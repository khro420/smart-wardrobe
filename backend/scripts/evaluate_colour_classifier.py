"""Import datasets, assess explicit threshold experiments, or evaluate locked data.

No implicit threshold search, split randomisation, CV rerun, or release activation.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.application.recommendation.colour_dataset import load_dataset, evaluate_dataset
from app.application.recommendation.prototype_colour_classifier import PrototypeColourClassifier, DEFAULT_PROTOTYPES, content_hash


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("import", "calibrate", "evaluate"))
    parser.add_argument("--dataset",type=Path,required=True)
    parser.add_argument("--prototypes",type=Path,default=DEFAULT_PROTOTYPES)
    parser.add_argument("--thresholds",type=Path)
    parser.add_argument("--partition",choices=("development","calibration","validation"))
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--confirm-locked-validation",action="store_true")
    args = parser.parse_args(argv)
    try:
        dataset = load_dataset(args.dataset)
        if args.operation == "import":
            if args.thresholds or args.partition or args.confirm_locked_validation:
                raise ValueError("Import does not evaluate samples.")
            payload = dataset
        else:
            if not args.partition:
                raise ValueError("An explicit partition is required.")
            if args.operation == "calibrate" and (args.partition == "validation" or not args.thresholds or args.confirm_locked_validation):
                raise ValueError("Calibration requires supplied thresholds and development/calibration data only.")
            if args.partition == "validation" and not args.confirm_locked_validation:
                raise ValueError("Locked validation access must be explicitly acknowledged; do not tune from its results.")
            if args.confirm_locked_validation and args.partition != "validation":
                raise ValueError("Validation acknowledgement is only for validation.")
            thresholds = json.loads(args.thresholds.read_text(encoding="utf-8")) if args.thresholds else None
            classifier = PrototypeColourClassifier(args.prototypes,thresholds)
            payload = evaluate_dataset(dataset,classifier,args.partition)
            payload["operation"] = args.operation
        if args.output.resolve() in {args.dataset.resolve(), args.prototypes.resolve()} or (args.thresholds and args.output.resolve() == args.thresholds.resolve()):
            raise ValueError("Output must not overwrite input artifacts.")
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        print(json.dumps({"operation":args.operation,"output":str(args.output),"dataset_hash":content_hash(dataset),"mandatory_evidence_enabled":False}))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
