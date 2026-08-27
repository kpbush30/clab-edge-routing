#!/usr/bin/env python3
"""Run validation tests for a specific profile against the running topology."""

from __future__ import annotations

import argparse
import subprocess
import sys

VALID_PROFILES = [
    "base", "bgp-attributes", "monitor-connectivity", "pingcheck", "interface-tracking",
]

PROFILE_MARKERS: dict[str, str] = {
    "base": "base",
    "bgp-attributes": "bgp_attributes",
    "monitor-connectivity": "monitor_connectivity",
    "pingcheck": "pingcheck",
    "interface-tracking": "interface_tracking",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run validation tests for a profile")
    parser.add_argument("--profile", required=True, help="Configuration profile name")
    args = parser.parse_args()

    if args.profile not in VALID_PROFILES:
        print(
            f"Error: invalid profile '{args.profile}'. Valid: {', '.join(VALID_PROFILES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    marker = PROFILE_MARKERS[args.profile]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            marker,
            "--profile",
            args.profile,
            "-v",
        ],
        check=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
