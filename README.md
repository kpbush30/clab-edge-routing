# Edge Routing Resiliency Lab

A containerlab topology built with Arista cEOS that demonstrates a dual-homed
internet edge: two ISPs, an MLAG-paired edge router pair speaking iBGP, and a
core router behind them. It shows two different failover mechanisms working
together — BFD for fast hard-failure detection, and EOS connectivity monitor
+ event-handlers for detecting "soft" failures that BGP and BFD alone can't
see. See [docs/failover.md](docs/failover.md) for the full mechanics and
step-by-step scenarios.

> **Status:** This lab is not yet driven by Arista AVD. Everything ships as
> static, hand-written EOS startup-configs (`clab/configs/*.cfg`) that boot
> the devices straight into a fully working state — **no config push step is
> required**. AVD-based config generation (see `avd/`) is planned but not
> wired up yet; ignore that directory for now.

Six nodes: `isp-router3` (simulated internet), two ISPs (`isp-router1`
primary, `isp-router2` backup), an MLAG/iBGP edge router pair
(`edge-router1`/`edge-router2`), and `core-router1` behind them. Full diagram
and per-node details: [docs/topology.md](docs/topology.md).

## Prerequisites

- [containerlab](https://containerlab.dev/) installed
- Docker
- An Arista cEOS-lab image — **you need to supply your own**, downloaded from
  [arista.com](https://www.arista.com/en/support/software-download) (requires
  a free Arista account). This lab does not, and cannot, ship the image.
- (Optional) A CloudVision onboarding token, if you want the lab to stream
  telemetry to CloudVision.

## Setup

**1. Import your cEOS image into Docker and point the topology at it.**

```bash
docker import cEOS-lab-<version>.tar.xz ceos:<version>
```

Then edit `clab/topology.clab.yml` and update the image tag under
`topology.kinds.arista_ceos.image` to match what you just imported.

**2. Provide (or skip) a CloudVision onboarding token.**

The topology binds `clab/cv-onboarding-token` into every node for the
`TerminAttr` daemon. The file must exist for the bind mount to work, even if
you don't plan to use CloudVision:

```bash
# To stream to CloudVision: paste your real onboarding token in this file
# To skip CloudVision entirely: just create an empty file
touch clab/cv-onboarding-token
```

If you do want CloudVision streaming to work, the containerlab management
network needs a route to your CVaaS/on-prem cluster — that's on you to set
up (routing, NAT, or a management-network uplink); it's outside the scope of
this lab.

## Deploy the lab

```bash
make deploy
```

Because every node boots from a complete startup-config already
(`enforce-startup-config: true`), **the lab is fully operational the moment
the containers come up** — BGP, BFD, MLAG, and connectivity monitor are all
already configured and running. There is nothing to push.

```bash
make status                       # confirm all nodes are running
docker exec -it edge-router1 Cli   # log in (containers are named after the node — the topology sets prefix: "")
```

> NOTE: All devices can be accessed using arista/arista

Baseline sanity check from `edge-router1`: `show ip bgp summary`, `show bfd
peers`, and `show monitor connectivity host` should all be healthy, with
`show ip route 1.1.1.1` preferred via ISP1 (Ethernet1).

## Trigger a failover

- **Hard failure (BFD):** shut down the ISP1 link and watch BFD/BGP react in
  under a second.
- **Soft failure (connectivity monitor):** black-hole just the monitored
  destination on `isp-router1` and watch the event-handler fail over while
  the ISP1 link and BGP session stay fully up.

Both scenarios, exact commands, and where to watch the route change:
[docs/failover.md](docs/failover.md).

## Destroy or recreate the lab

```bash
make destroy    # tear down, keep generated lab files (TLS certs, etc.)
make clean      # tear down and remove all generated lab files
make recreate   # destroy + deploy in one step, fresh boot
```

If your containerlab/Docker setup requires elevated privileges, prefix any
of these with `sudo`, e.g. `sudo make deploy`.

## Project structure

```
├── clab/
│   ├── topology.clab.yml   # containerlab topology (nodes, links, image)
│   ├── configs/            # EOS startup-configs, one per node — the source of truth
│   ├── sn/                 # per-node serial number / system MAC files (cEOS identity)
│   └── cv-onboarding-token # CloudVision onboarding token (gitignored; create your own)
├── docs/                   # topology diagram and failover walkthroughs
├── avd/                    # Arista AVD structured config — not wired up yet
├── Makefile                # deploy / status / recreate / destroy / clean
└── README.md
```
