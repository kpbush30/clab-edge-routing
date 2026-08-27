#!/usr/bin/env python3
"""Generate containerlab topology YAML from AVD structured config host_vars."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

CLAB_PREFIX = "edge-routing"
CEOS_IMAGE = "ceos:latest"
MGMT_NETWORK = "172.100.100.0/24"
MGMT_GATEWAY = "172.100.100.1"

MGMT_IPS: dict[str, str] = {
    "isp-router-1": "172.100.100.2/24",
    "isp-router-2": "172.100.100.3/24",
    "edge-router-1": "172.100.100.4/24",
    "edge-router-2": "172.100.100.5/24",
    "core-router-1": "172.100.100.6/24",
}


def load_host_vars(profile_dir: Path, base_dir: Path | None = None) -> dict[str, dict]:
    """Load and merge host_vars from base and profile directories."""
    devices: dict[str, dict] = {}

    if base_dir and base_dir.exists():
        for f in sorted(base_dir.glob("*.yml")):
            with open(f) as fh:
                devices[f.stem] = yaml.safe_load(fh) or {}

    if profile_dir.exists():
        for f in sorted(profile_dir.glob("*.yml")):
            name = f.stem
            with open(f) as fh:
                override = yaml.safe_load(fh) or {}
            if name in devices:
                devices[name] = deep_merge(devices[name], override)
            else:
                devices[name] = override

    return devices


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning a new dict."""
    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def extract_links(devices: dict[str, dict]) -> list[dict]:
    """Extract unique links from ethernet_interfaces peer annotations."""
    seen: set[tuple[tuple[str, str], ...]] = set()
    links: list[dict] = []

    for device_name, config in devices.items():
        for intf in config.get("ethernet_interfaces", []):
            peer = intf.get("peer")
            peer_intf = intf.get("peer_interface")
            intf_name = intf.get("name", "")

            if not peer or not peer_intf:
                continue

            link_key = tuple(sorted([(device_name, intf_name), (peer, peer_intf)]))
            if link_key in seen:
                continue
            seen.add(link_key)

            links.append({
                "endpoints": [
                    f"{device_name}:{intf_name}",
                    f"{peer}:{peer_intf}",
                ],
            })

    return links


def build_topology(
    devices: dict[str, dict],
    binds: dict[str, list[str]] | None = None,
) -> dict:
    """Build containerlab topology dict."""
    nodes: dict[str, dict] = {}
    for name in devices:
        node: dict = {
            "kind": "ceos",
            "image": CEOS_IMAGE,
        }
        if name in MGMT_IPS:
            node["mgmt-ipv4"] = MGMT_IPS[name]

        startup_cfg = Path("intended/configs") / f"{name}.cfg"
        node_binds = [f"{startup_cfg}:/mnt/flash/startup-config"]
        if binds and name in binds:
            node_binds.extend(binds[name])
        node["binds"] = node_binds

        nodes[name] = node

    links = extract_links(devices)

    return {
        "name": CLAB_PREFIX,
        "mgmt": {
            "network": "clab-mgmt",
            "ipv4-subnet": MGMT_NETWORK,
            "ipv4-gw": MGMT_GATEWAY,
        },
        "topology": {
            "kinds": {
                "ceos": {
                    "image": CEOS_IMAGE,
                },
            },
            "nodes": nodes,
            "links": links,
        },
    }


def get_profile_binds(profile: str) -> dict[str, list[str]]:
    """Return extra bind mounts needed for a specific profile."""
    if profile == "pingcheck":
        pingcheck_binds = [
            "PingCheck/PingCheck.py:/mnt/flash/PingCheck.py",
            "profiles/pingcheck/files/isp1-failed.conf:/mnt/flash/isp1-failed.conf",
            "profiles/pingcheck/files/isp1-recover.conf:/mnt/flash/isp1-recover.conf",
        ]
        return {
            "edge-router-1": pingcheck_binds,
            "edge-router-2": pingcheck_binds,
        }
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate containerlab topology")
    parser.add_argument("--profile", default="base", help="Configuration profile name")
    parser.add_argument("--output", default="topology.yml", help="Output file path")
    args = parser.parse_args()

    base_dir = Path("profiles/base/host_vars")
    profile_dir = Path(f"profiles/{args.profile}/host_vars")

    if not base_dir.exists():
        print(f"Error: base host_vars directory not found: {base_dir}", file=sys.stderr)
        sys.exit(1)

    if args.profile != "base" and not profile_dir.exists():
        print(f"Error: profile host_vars directory not found: {profile_dir}", file=sys.stderr)
        sys.exit(1)

    if args.profile == "base":
        devices = load_host_vars(base_dir)
    else:
        devices = load_host_vars(profile_dir, base_dir)

    binds = get_profile_binds(args.profile)
    topology = build_topology(devices, binds)

    with open(args.output, "w") as f:
        yaml.dump(topology, f, default_flow_style=False, sort_keys=False)

    print(f"Generated {args.output} with {len(devices)} nodes")


if __name__ == "__main__":
    main()
