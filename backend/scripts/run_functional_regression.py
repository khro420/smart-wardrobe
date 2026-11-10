"""Run the explicit current functional scope without interception or result adapters.

Historical source guards remain executable separately on their original sources.
Missing J15 evidence still produces native failures; frozen skips stay unverified.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--junitxml', type=Path, default=Path('test-results/backend.xml'))
    parser.add_argument('--with-cv', action='store_true', help='Also collect geometry tests; requires teammate CV dependencies.')
    parser.add_argument('--baseline-oracle', type=Path,
                        help='Original approved B0 app.zip/manifest directory for immutable equivalence checks.')
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    scope = json.loads((backend / 'tests/fixtures/integrated_functional_scope.v1.json').read_text())
    modules = list(scope['modules'])
    if args.with_cv:
        modules.append('tests/test_segmentation_geometry.py')
    result = args.junitxml.resolve()
    result.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if args.baseline_oracle:
        env['B1_APPROVED_BASELINE_ORACLE'] = str(args.baseline_oracle.resolve())
    command = [sys.executable, '-B', '-m', 'pytest', *modules,
               *['--deselect=' + node for node in scope['historical_source_assignments']],
               '-k', 'not (' + ' or '.join(scope['dedicated_measurement_functions_excluded']) + ')',
               '-q', '--junitxml=' + str(result)]
    return subprocess.call(command, cwd=backend, env=env)


if __name__ == '__main__':
    raise SystemExit(main())
