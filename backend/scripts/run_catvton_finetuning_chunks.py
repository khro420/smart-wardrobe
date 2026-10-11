"""Run short CatVTON experiment chunks with a conservative GPU cooldown gate."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time


BACKEND = Path(__file__).resolve().parents[1]


def temperature() -> int:
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], text=True
    )
    return int(output.strip().splitlines()[0])


def main() -> None:
    parser = ArgumentParser(description="Resume CatVTON attention fine-tuning in thermally bounded chunks.")
    parser.add_argument("--start-checkpoint", type=Path, required=True)
    parser.add_argument("--start-step", type=int, required=True)
    parser.add_argument("--target-step", type=int, default=1000)
    parser.add_argument("--chunk-steps", type=int, default=100)
    parser.add_argument("--max-start-temperature", type=int, default=65)
    parser.add_argument("--max-cooldown-seconds", type=int, default=600)
    args = parser.parse_args()
    if args.target_step <= args.start_step or args.chunk_steps < 1:
        raise SystemExit("target-step must exceed start-step and chunk-steps must be positive.")
    checkpoint = args.start_checkpoint.resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    report = {"kind": "Thermally bounded CatVTON fine-tuning runner", "started_at": datetime.now(timezone.utc).isoformat(), "chunks": [], "status": "running"}
    report_path = BACKEND / "runs" / "catvton_dresscode_attention" / "chunk_runner_results.json"
    step = args.start_step
    while step < args.target_step:
        deadline = time.monotonic() + args.max_cooldown_seconds
        while temperature() > args.max_start_temperature:
            if time.monotonic() >= deadline:
                report["status"] = "cooldown_timeout"
                report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                raise RuntimeError("GPU did not cool to the configured start temperature.")
            time.sleep(20)
        next_step = min(step + args.chunk_steps, args.target_step)
        output_dir = BACKEND / "runs" / "catvton_dresscode_attention" / f"step{next_step}"
        command = [sys.executable, "scripts/train_catvton_attention_dresscode.py", "--max-steps", str(next_step - step), "--checkpoint-every", "25", "--resume-from", str(checkpoint), "--output-dir", str(output_dir)]
        started = time.perf_counter()
        subprocess.run(command, cwd=BACKEND, check=True)
        checkpoint = output_dir / "attention_experiment.pt"
        if not checkpoint.is_file():
            raise RuntimeError(f"Expected checkpoint was not written: {checkpoint}")
        report["chunks"].append({"from_step": step, "to_step": next_step, "checkpoint": str(checkpoint), "seconds": round(time.perf_counter() - started, 3), "temperature_after_c": temperature()})
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        step = next_step
    report["status"] = "complete"
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
