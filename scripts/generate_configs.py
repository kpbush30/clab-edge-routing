#!/usr/bin/env python3
"""Generate EOS CLI configs from AVD structured config with profile merging."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

VALID_PROFILES = [
    "base", "bgp-attributes", "monitor-connectivity", "pingcheck", "interface-tracking",
]


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning a new dict."""
    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_group_vars(group_vars_dir: Path) -> dict:
    """Load all group_vars YAML files and merge them."""
    merged: dict = {}
    if not group_vars_dir.exists():
        return merged
    for f in sorted(group_vars_dir.glob("*.yml")):
        merged = deep_merge(merged, load_yaml(f))
    return merged


def build_structured_configs(profile: str) -> dict[str, dict]:
    """Build merged structured configs for all devices in a profile."""
    base_dir = Path("profiles/base/host_vars")
    profile_dir = Path(f"profiles/{profile}/host_vars")
    group_vars_dir = Path("inventory/group_vars")

    if not base_dir.exists():
        print(f"Error: base host_vars not found: {base_dir}", file=sys.stderr)
        sys.exit(1)

    if profile != "base" and not profile_dir.exists():
        print(f"Error: profile host_vars not found: {profile_dir}", file=sys.stderr)
        sys.exit(1)

    group_vars = load_group_vars(group_vars_dir)
    devices: dict[str, dict] = {}

    for f in sorted(base_dir.glob("*.yml")):
        device_name = f.stem
        device_config = deep_merge(group_vars, load_yaml(f))
        devices[device_name] = device_config

    if profile != "base":
        for f in sorted(profile_dir.glob("*.yml")):
            device_name = f.stem
            if device_name in devices:
                devices[device_name] = deep_merge(devices[device_name], load_yaml(f))

    return devices


def strip_topology_keys(config: dict) -> dict:
    """Remove custom topology annotation keys before AVD validation."""
    import copy

    config = copy.deepcopy(config)
    for intf in config.get("ethernet_interfaces", []):
        intf.pop("peer", None)
        intf.pop("peer_interface", None)
    return config


def generate_eos_configs(devices: dict[str, dict], output_dir: Path) -> None:
    """Validate structured configs and render EOS CLI configs using pyavd."""
    from pyavd import get_device_config, validate_structured_config

    output_dir.mkdir(parents=True, exist_ok=True)

    for device_name, structured_config in devices.items():
        structured_config.setdefault("hostname", device_name)

        clean_config = strip_topology_keys(structured_config)
        result = validate_structured_config(clean_config)
        if result.validation_result.violations:
            print(f"Error: validation failed for {device_name}:", file=sys.stderr)
            for violation in result.validation_result.violations:
                print(f"  {violation.path}: {violation.message}", file=sys.stderr)
            sys.exit(1)

        config = get_device_config(result.validated_data)
        config_path = output_dir / f"{device_name}.cfg"
        config_path.write_text(config)
        print(f"Generated {config_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate EOS configs from AVD structured config")
    parser.add_argument("--profile", required=True, help="Configuration profile name")
    parser.add_argument(
        "--output-dir", default="intended/configs", help="Output directory for configs",
    )
    args = parser.parse_args()

    if args.profile not in VALID_PROFILES:
        print(
            f"Error: invalid profile '{args.profile}'. Valid: {', '.join(VALID_PROFILES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    devices = build_structured_configs(args.profile)
    generate_eos_configs(devices, Path(args.output_dir))
    print(f"Generated configs for {len(devices)} devices (profile: {args.profile})")


if __name__ == "__main__":
    main()
