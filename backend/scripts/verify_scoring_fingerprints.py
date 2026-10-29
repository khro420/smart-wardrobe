"""Exhaustive 200-garment transcripts against independent completed 2A.

Instrumentation run, NOT latency evidence. Retains the historical 2A hashes.
"""
import argparse
import json
import hashlib
from pathlib import Path
import subprocess
import sys

BACKEND = Path(__file__).resolve().parents[1]
ANCHORS = (
    "7338a94fddf5c8c66cfafb3f9732e00114e90e062a75e1f1098b9d61f61a14c5",
    "302fa15c0bd06c36445a5d8bf07fb2ea0b1a43db56905a863adf0ba4cfacb574",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--reference",type=Path,default=BACKEND/"tests/fixtures/performance_reference_2a")
    parser.add_argument("--progress-digest",action="store_true")
    parser.add_argument("--candidate-reference",type=Path,help="Archived trial arm; combined label remains distinct from reference")
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    results = []
    for populated,anchor in enumerate(ANCHORS):
        reference = None
        for variant in ("original","combined"):
            print(f"Complete transcript: preferences={populated}, {variant}",flush=True)
            output = args.output/f"prefs-{populated}-{variant}.json"
            arm_reference=args.candidate_reference if variant=="combined" and args.candidate_reference else args.reference
            arm_variant="original" if variant=="combined" and args.candidate_reference else variant
            if args.candidate_reference and args.candidate_reference.resolve()==args.reference.resolve():
                raise ValueError("Reference and experimental trial must be independent")
            if args.candidate_reference and hashlib.sha256((args.candidate_reference/'app.zip').read_bytes()).digest()==hashlib.sha256((args.reference/'app.zip').read_bytes()).digest():
                raise ValueError("Reference and experimental trial archives must differ")
            subprocess.run([sys.executable,"-B",str(BACKEND/"tests/performance_worker.py"),
                "--reference",str(arm_reference),
                "--variant",arm_variant,"--fixtures",str(args.fixtures_dir/f"size-200-prefs-{populated}-input.json"),
                "--output",str(output),"--digest",*(["--progress-digest"] if args.progress_digest else [])],check=True)
            value = json.loads(output.read_text())[0]
            comparable = {k:v for k,v in value.items() if k != "timings"}
            if value["scored_count"] != 134820 or value["transcript"] != {"sha256":anchor,"events":404460}:
                raise RuntimeError("Complete stream differs from preserved 2A fingerprint")
            if reference is None:
                reference = comparable
            elif comparable != reference:
                raise RuntimeError("Complete outcome or persisted metadata differs")
            results.append({"populated":bool(populated),"variant":variant,"transcript":value["transcript"],
                "scored_count":value["scored_count"],"winner":value["winner"],"score_metadata":value["score_metadata"]})
            if args.progress_digest: results[-1]["progress"] = value["progress"]
            (args.output/"results.json").write_text(json.dumps(results,indent=2)+"\n")
    print("All four full streams match the independent reference and preserved hashes.",flush=True)


if __name__ == "__main__":
    main()
