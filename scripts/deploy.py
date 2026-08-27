#!/usr/bin/env python3
"""Deploy or switch lab profile configs to containerlab topology."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pyeapi

VALID_PROFILES = [
    "base", "bgp-attributes", "monitor-connectivity", "pingcheck", "interface-tracking",
]
TOPO_FILE = "topology.yml"

DEVICE_MGMT_IPS: dict[str, str] = {
    "isp-router-1": "172.100.100.2",
    "isp-router-2": "172.100.100.3",
    "edge-router-1": "172.100.100.4",
    "edge-router-2": "172.100.100.5",
    "core-router-1": "172.100.100.6",
}


def is_topology_running() -> bool:
    """Check if the containerlab topology is already deployed."""
    try:
        result = subprocess.run(
            ["containerlab", "inspect", "--name", "edge-routing", "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        return bool(data.get("containers"))
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def run_generate_configs(profile: str) -> None:
    """Run the config generation script."""
    result = subprocess.run(
        [sys.executable, "scripts/generate_configs.py", "--profile", profile],
        check=False,
    )
    if result.returncode != 0:
        print("Error: config generation failed", file=sys.stderr)
        sys.exit(1)


def run_generate_topology(profile: str) -> None:
    """Run the topology generation script."""
    result = subprocess.run(
        [sys.executable, "scripts/generate_topology.py", "--profile", profile],
        check=False,
    )
    if result.returncode != 0:
        print("Error: topology generation failed", file=sys.stderr)
        sys.exit(1)


def deploy_topology() -> None:
    """Deploy the containerlab topology."""
    result = subprocess.run(
        ["containerlab", "deploy", "--topo", TOPO_FILE],
        check=False,
    )
    if result.returncode != 0:
        print("Error: containerlab deploy failed", file=sys.stderr)
        sys.exit(1)


def push_configs_via_eapi(configs_dir: Path) -> None:
    """Push generated configs to running devices via eAPI configure replace."""
    for device_name, mgmt_ip in DEVICE_MGMT_IPS.items():
        config_file = configs_dir / f"{device_name}.cfg"
        if not config_file.exists():
            print(f"Warning: no config file for {device_name}, skipping", file=sys.stderr)
            continue

        config_text = config_file.read_text()
        try:
            connection = pyeapi.connect(
                transport="https",
                host=mgmt_ip,
                username="admin",
                password="admin",
                return_node=True,
            )
            connection.run_commands(
                [
                    "enable",
                    {"cmd": "configure replace", "input": config_text},
                ],
                encoding="text",
            )
            print(f"Pushed config to {device_name} ({mgmt_ip})")
        except Exception as e:
            print(f"Error pushing config to {device_name}: {e}", file=sys.stderr)
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy or switch lab profile")
    parser.add_argument("--profile", required=True, help="Configuration profile name")
    parser.add_argument(
        "--switch-only",
        action="store_true",
        help="Only switch config (topology must be running)",
    )
    args = parser.parse_args()

    if args.profile not in VALID_PROFILES:
        print(
            f"Error: invalid profile '{args.profile}'. Valid: {', '.join(VALID_PROFILES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    running = is_topology_running()

    if args.switch_only and not running:
        print("Error: topology is not running. Deploy first with 'make deploy'.", file=sys.stderr)
        sys.exit(1)

    run_generate_configs(args.profile)

    if running:
        print(f"Topology already running — pushing {args.profile} configs via eAPI")
        push_configs_via_eapi(Path("intended/configs"))
    else:
        run_generate_topology(args.profile)
        deploy_topology()

    print(f"Profile '{args.profile}' deployed successfully")


if __name__ == "__main__":
    main()
