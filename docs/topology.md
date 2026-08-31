# Topology

```
                              ┌─────────────────────┐
                              │    isp-router3      │   AS 64503 ("the Internet")
                              │  originates:        │
                              │   0.0.0.0/0         │
                              │   1.1.1.1/32        │
                              │   100.64.0.0/24     │
                              │   199.7.83.42/32    │
                              │   203.0.113.0/24    │
                              │   198.51.100.0/24.  │
                              └────┬───────────┬────┘
                              Et1  │           │  Et2
                                   │           │
                              Et2  │           │  Et2
                         ┌─────────┴───┐   ┌───┴─────────┐
                         │ isp-router1 │   │ isp-router2 │
                         │  AS 64501   │   │  AS 64502   │
                         └──────┬──────┘   └───────┬─────┘
                            Et1 │                  │ Et1
                                │                  │
                            Et1 │                  │ Et1
                    ┌───────────┴───┐          ┌───┴─────────────┐
                    │ edge-router1  │───Et3────│  edge-router2   │  AS 65000
                    │  (IS  primary)│  Po1000  │ (ISP2 = backup) │  iBGP + MLAG
                    └───┬───────────┘          └───────────┬─────┘
                    Et2 │                                  │ Et2
                        │           ┌──────────────┐       │
                        └───────────┤ core-router1 ├───────┘
                                    │   AS 65001   │
                                    └──────────────┘
```

| Node | AS | Role |
|------|----|------|
| `isp-router3` | 64503 | Simulates "the internet": originates the default route + a handful of public prefixes, dual-homed to both ISPs |
| `isp-router1` | 64501 | ISP1 — the **primary** transit path |
| `isp-router2` | 64502 | ISP2 — the **backup** transit path |
| `edge-router1` | 65000 | Edge router facing ISP1, MLAG + iBGP peer of edge-router2 |
| `edge-router2` | 65000 | Edge router facing ISP2, MLAG + iBGP peer of edge-router1 |
| `core-router1` | 65001 | Internal core, dual-homed to both edge routers, hosts the "protected" internal LAN (`11.11.11.0/24` on Vlan111, edge-router1/2) |

`isp-router3` stands in for the wider internet: it originates a default
route plus a few public prefixes (a simulated DNS resolver at `1.1.1.1`, a
root-server address, and a couple of RFC 5737/6598 test blocks) and peers
with both ISPs so it has two independent, equally valid paths back to each
of them.
