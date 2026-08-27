# Base Profile: Dual-Homed BGP Topology

**Difficulty**: Beginner

## Learning Objectives

- Understand a dual-homed internet edge topology with two ISP uplinks
- Observe default BGP best-path selection behavior
- Verify iBGP between edge routers with next-hop-self
- See how overlapping prefixes from multiple ISPs are resolved

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
              └────────┬──┘  └──┬────────┘
                  Eth2 │        │ Eth2
                       │        │
                  Eth1 │        │ Eth1
                    ┌──┴────────┴──┐
                    │ isp-router-2 │
                    │  AS 64502    │
                    └──────────────┘

              ┌────────────┐  ┌────────────┐
              │edge-rtr-1  ├──┤edge-rtr-2  │
              └──────┬─────┘  └──────┬─────┘
                Eth4 │               │ Eth4
                     │               │
                Eth1 │          Eth2 │
                  ┌──┴───────────┴──┐
                  │  core-router-1  │
                  │    AS 65001     │
                  └─────────────────┘
```

## Deploy

```bash
make deploy PROFILE=base
```

## Verification Commands

### Check BGP neighbor status on all devices

```bash
# On any device (via SSH or console):
show ip bgp summary
```

**Expected**: All neighbors show state `Established` with non-zero prefixes received.

### Check routes received at the core

```bash
# On core-router-1:
show ip route bgp
```

**Expected**: Three BGP-learned prefixes:
- `203.0.113.0/24` — from ISP1 only
- `198.51.100.0/24` — from ISP2 only
- `100.64.0.0/24` — from both ISPs (BGP selects best path)

### Examine BGP best-path for the overlapping prefix

```bash
# On core-router-1:
show ip bgp 100.64.0.0/24
```

**Expected**: Two paths visible (one via each edge router). BGP selects the best path based on default attributes (lowest router-id as tiebreaker when all else is equal).

### Verify iBGP next-hop-self

```bash
# On edge-router-1:
show ip bgp neighbors 10.0.3.2 routes
```

**Expected**: Routes learned via iBGP show edge-router-1 (10.0.3.1) as the next-hop, not the original ISP next-hop — confirming next-hop-self is working.

## Validate

```bash
make validate PROFILE=base
```

## Teardown

```bash
make destroy
```

## Key Takeaways

- A dual-homed edge with two ISPs provides redundancy — if one ISP fails, routes are still available via the other
- Without policy manipulation, BGP uses its default best-path algorithm: shortest AS-path, then lowest origin type, then lowest MED (if from same AS), then eBGP over iBGP, then lowest router-id
- iBGP between edge routers is essential for sharing routes learned from ISPs with the peer edge router
- `next-hop-self` on iBGP ensures the peer edge router can reach ISP-learned routes without needing routes to ISP-facing subnets
- The overlapping prefix (100.64.0.0/24) demonstrates that BGP deterministically selects one best path, even when the same prefix is received from multiple sources
