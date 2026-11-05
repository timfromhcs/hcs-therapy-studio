"""Summarise an A/B register-anchoring run.

Runs the measurement script and prints only the mismatches, so the failure modes
are visible instead of being buried in JSON.

    .\\.venv\\Scripts\\python.exe scripts\\bench\\summarise_register_ab.py --repeat 3
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("register_anchoring.py")


def main() -> int:
    # The Windows console defaults to a legacy code page that cannot encode every
    # character a model emits. Failing here would hide the very result the script
    # exists to show, so stdout is forced to UTF-8 with replacement.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ab", "--repeat", str(args.repeat)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if not result.stdout.strip():
        print(result.stderr, file=sys.stderr)
        return 1

    data = json.loads(result.stdout)
    for arm in ("anchored", "unanchored"):
        stats = data[arm]["stats"]
        print(f"\n{arm}: n={stats['requests']}  mixed={stats['mixed']}  "
              f"wrong_register={stats['wrong_register']}")
        for row in data[arm]["rows"]:
            if row["matches_expected"]:
                continue
            print(
                f"   expected={row['expected']:4} detected={str(row['detected']):7} "
                f"du={row['du']} sie={row['sie']}  {row['sample'][:80]}"
            )
    print("\n" + result.stderr.strip().splitlines()[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
