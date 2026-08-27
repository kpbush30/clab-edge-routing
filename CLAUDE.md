# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

clab-edge-routing is an educational containerlab repository using Arista cEOS to demonstrate edge routing resiliency concepts. It uses Arista AVD (`eos_cli_config_gen`) to generate EOS device configurations from structured YAML, and containerlab to deploy the topology.

The topology simulates a dual-homed edge: two ISP routers originate routes via eBGP to a pair of edge routers, which feed a small core/internal network. Scenarios demonstrate BGP path selection, monitor connectivity-based failover, and interface tracking.

## Development Environment

- **Python**: 3.11 (pinned in `.python-version`)
- **Package manager**: uv (uses `pyproject.toml`, no `requirements.txt`)
- **Virtual environment**: `.venv/` (created by uv)

### Setup

```bash
uv sync
```

### Build & Deploy

```bash
make deploy PROFILE=base           # Build configs + deploy containerlab topology
make switch PROFILE=bgp-attributes # Switch running topology to a different profile
make validate PROFILE=base         # Run pytest validation suite
make lab PROFILE=base              # Deploy + validate in one step
make destroy                       # Tear down containerlab topology
make clean                         # Remove generated artifacts
```

### Profiles

| Profile | Extends | What it adds |
|---------|---------|-------------|
| `base` | — | Working dual-homed BGP topology |
| `bgp-attributes` | `base` | Route-maps for local-pref, AS-path, MED, weight |
| `monitor-connectivity` | `bgp-attributes` | Monitor connectivity + event-handler failover |
| `pingcheck` | `bgp-attributes` | PingCheck EOS SDK daemon failover |
| `interface-tracking` | `base` | Track objects + conditional static routes |

### Scripts

- `scripts/generate_configs.py --profile <name>` — Merge base + profile host_vars, validate with pyavd, render EOS CLI configs
- `scripts/generate_topology.py --profile <name>` — Generate containerlab topology YAML from AVD structured config
- `scripts/deploy.py --profile <name>` — Deploy or switch profiles (detects running topology)
- `scripts/validate.py --profile <name>` — Run pytest with profile-specific markers

### Tests

```bash
pytest tests/ -m base -v --profile base  # Run base profile tests directly
```

Tests use pyeapi to connect to running cEOS containers and verify BGP state, routing tables, and failover behavior.

## AVD Reference

A local clone of the AVD repository is at `avd/`. Key paths for schema lookups:

- `avd/python-avd/pyavd/_eos_cli_config_gen/schema/eos_cli_config_gen.schema.yml` — full eos_cli_config_gen schema
- `avd/python-avd/pyavd/_eos_designs/schema/eos_designs.schema.yml` — full eos_designs schema
- `avd/python-avd/pyavd/_eos_cli_config_gen/schema/schema_fragments/` — per-feature schema fragments
- `avd/ansible_collections/arista/avd/roles/eos_cli_config_gen/docs/tables/*.md` — input variable docs

This project uses `eos_cli_config_gen` directly (not `eos_designs`) because the edge routing topology does not fit AVD's data center fabric abstractions.

## EOS Platform Notes

- EOS has no `ip sla` command. The equivalent is `monitor connectivity` (ICMP/HTTP probes).
- Dynamic BGP policy changes based on probe results require `event-handler on-logging` reacting to connectivity monitor syslog messages, using `FastCli` to update route-maps.
- `track` objects on cEOS only support `interface line-protocol` (follows veth admin/oper state).
- PingCheck (EOS SDK extension at `PingCheck/PingCheck.py`) provides daemon-based failover with HOLDUP/HOLDDOWN dampening. AVD's `daemons` schema doesn't support daemon options — use `eos_cli` for PingCheck config.
- AVD's `static_routes` schema doesn't support `track` associations — use `eos_cli` for tracked static routes.

## SpecKit Integration

This project uses SpecKit for feature specification workflows. Configuration lives in `.specify/`. Use the `/speckit-*` skills (specify, plan, tasks, implement, etc.) to drive the feature development lifecycle.
