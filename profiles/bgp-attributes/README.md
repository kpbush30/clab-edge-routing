# BGP Attributes Profile: Provider Preference Manipulation

**Difficulty**: Intermediate

## Learning Objectives

- Understand the BGP best-path selection algorithm order: weight > local-preference > AS-path length > MED
- Apply route-maps to manipulate BGP attributes inbound and outbound
- Observe how local-preference changes ISP preference for an overlapping prefix
- Compare different BGP attributes and when to use each

## Prerequisites

Complete the [base profile](../base/README.md) first to understand the default topology.

## What This Profile Adds

Four route-maps are pre-configured on both edge routers:

| Route-Map | Action | Applied To | Purpose |
|-----------|--------|------------|---------|
| `RM-ISP1-LOCALPREF-IN` | Sets local-preference 200 | ISP1 inbound (active) | Makes ISP1 the preferred path |
| `RM-ISP1-PREPEND-IN` | Prepends AS 64501 3x | Available for exercise | Lengthens ISP1 AS-path |
| `RM-ISP2-MED-OUT` | Sets MED 100 | Available for exercise | Influences ISP2 return traffic |
| `RM-ISP1-WEIGHT` | Sets weight 200 | Available for exercise | Local-only ISP1 preference |

By default, `RM-ISP1-LOCALPREF-IN` is applied to the ISP1 peer group inbound, making ISP1 the preferred provider for all overlapping prefixes.

## Deploy

```bash
make deploy PROFILE=bgp-attributes
```

## Verification Commands

### Verify route-maps are applied

```bash
# On edge-router-1:
show route-map
```

### Check local-preference on ISP1 routes

```bash
# On edge-router-1:
show ip bgp 100.64.0.0/24
```

**Expected**: ISP1 path shows local-preference 200; ISP2 path shows default (100). ISP1 path is selected as best.

### Verify core sees ISP1-preferred path

```bash
# On core-router-1:
show ip route 100.64.0.0/24
```

**Expected**: Best path is via the edge router's ISP1 uplink.

## Exercises

### Exercise 1: Switch from local-preference to AS-path prepending

```bash
# On edge-router-1, replace the ISP1 inbound route-map:
configure
router bgp 65000
  address-family ipv4
    neighbor ISP1 route-map RM-ISP1-PREPEND-IN in
    no neighbor ISP1 route-map RM-ISP1-LOCALPREF-IN in
  !
end
clear ip bgp ISP1 soft in

# Now check the BGP table:
show ip bgp 100.64.0.0/24
```

**Expected**: ISP1 path now has a longer AS-path (64501 64501 64501 64501). ISP2 becomes preferred because its AS-path is shorter.

### Exercise 2: Apply weight (local-only preference)

```bash
# On edge-router-1:
configure
router bgp 65000
  address-family ipv4
    neighbor ISP1 route-map RM-ISP1-WEIGHT in
    no neighbor ISP1 route-map RM-ISP1-PREPEND-IN in
  !
end
clear ip bgp ISP1 soft in

show ip bgp 100.64.0.0/24
```

**Expected**: ISP1 path shows weight 200. Weight is evaluated before local-preference — ISP1 is preferred again, but only on this router (weight is not propagated via iBGP).

## Validate

```bash
make validate PROFILE=bgp-attributes
```

## Teardown

```bash
make destroy
```

## Key Takeaways

- BGP path selection order: weight (local only) > local-preference (iBGP-propagated) > AS-path length > origin > MED (same neighbor AS) > eBGP over iBGP > lowest router-id
- Local-preference is the most common tool for ISP preference because it propagates via iBGP to all routers in the AS
- Weight is per-router only — useful when you want different routers to prefer different ISPs
- AS-path prepending makes a path look longer to influence inbound traffic decisions by remote ASes
- MED (Multi-Exit Discriminator) influences how a neighboring AS chooses between multiple entry points into your network
