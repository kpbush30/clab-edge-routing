# Edge Routing Resiliency Lab

A containerlab-based lab using Arista cEOS to teach edge routing resiliency concepts. Deploy a dual-homed internet edge topology and explore how BGP attributes, connectivity monitoring, and interface tracking provide different strategies for ISP failover.

## Topology

```
                    ┌──────────────┐
                    │ isp-router-1 │
                    │  AS 64501    │
                    └──┬────────┬──┘
                  Eth1 │        │ Eth2
                       │        │
                  Eth1 │        │ Eth1
              ┌────────┴──┐  ┌──┴────────┐
              │edge-rtr-1 │──│edge-rtr-2 │  (iBGP: Eth3 ↔ Eth3)
              │  AS 65000 │  │  AS 65000 │
              └────┬───┬──┘  └──┬───┬────┘
              Eth2 │   │ Eth4   │   │ Eth4
                   │   │        │   │
              Eth1 │   │   Eth1 │   │
                ┌──┴───┴────┴──┐│   │
                │ isp-router-2 ││   │
                │  AS 64502    │└───┘
                └──────────────┘Eth2 │
                                    │
                Eth1 ┌──────────────┴──┐ Eth2
                     │  core-router-1  │
                     │    AS 65001     │
                     └─────────────────┘
```

Five devices: 2 ISP routers originating prefixes, 2 edge routers (iBGP pair), and 1 core router receiving routes via eBGP.

## Prerequisites

- [containerlab](https://containerlab.dev/) installed
- Arista cEOS image imported (`ceos:latest`)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
git clone <repo-url>
cd clab-edge-routing
uv sync  # or: pip install -e .
```

## Quick Start

```bash
make lab PROFILE=base
```

This deploys all 5 nodes and runs validation tests to confirm BGP is fully operational.

## Learning Path

Work through the profiles in order. Each builds on the previous one.

| # | Profile | Difficulty | Description |
|---|---------|------------|-------------|
| 1 | [base](profiles/base/README.md) | Beginner | Deploy a dual-homed BGP topology, observe default path selection |
| 2 | [bgp-attributes](profiles/bgp-attributes/README.md) | Intermediate | Manipulate local-preference, AS-path, MED, and weight |
| 3a | [monitor-connectivity](profiles/monitor-connectivity/README.md) | Intermediate | Automated failover via event-handler + FastCli |
| 3b | [pingcheck](profiles/pingcheck/README.md) | Intermediate | Automated failover via PingCheck EOS SDK extension |
| 4 | [interface-tracking](profiles/interface-tracking/README.md) | Intermediate | Conditional routing via track objects |

Profiles 3a and 3b are alternatives — they demonstrate two different approaches to the same failover problem.

## Usage

```bash
# Deploy a profile
make deploy PROFILE=base

# Switch to a different profile (without restarting containers)
make switch PROFILE=bgp-attributes

# Run validation tests
make validate PROFILE=bgp-attributes

# Full lifecycle (deploy + validate)
make lab PROFILE=base

# Tear down the lab
make destroy

# Clean generated artifacts
make clean
```

## Project Structure

```
├── profiles/                    # Configuration profiles
│   ├── base/                    # Base BGP topology
│   ├── bgp-attributes/          # Route-map attribute manipulation
│   ├── monitor-connectivity/    # Event-handler failover
│   ├── pingcheck/               # PingCheck extension failover
│   └── interface-tracking/      # Track object conditional routing
├── inventory/                   # Ansible inventory (shared across profiles)
├── scripts/                     # Build, deploy, and validate tooling
├── tests/                       # pytest validation suites per profile
├── PingCheck/                   # PingCheck EOS SDK extension (vendored)
├── avd/                         # Arista AVD (local clone for config generation)
└── Makefile                     # User-facing CLI targets
```

## How It Works

1. **Build**: AVD `eos_cli_config_gen` renders EOS CLI configs from structured YAML (`profiles/<name>/host_vars/`)
2. **Topology**: A script generates a containerlab topology file from the AVD structured config
3. **Deploy**: containerlab creates cEOS containers with the generated configs
4. **Switch**: pyeapi pushes new configs via eAPI without restarting containers
5. **Validate**: pytest tests verify BGP state, route tables, and failover behavior via eAPI
