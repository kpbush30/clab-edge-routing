# Interface Tracking Profile: Conditional Routing via Track Objects

**Difficulty**: Intermediate

## Learning Objectives

- Understand EOS `track` objects and how they monitor interface line-protocol state
- Configure static routes with track associations for conditional routing
- Observe route withdrawal and reinstallation based on interface state
- Compare coarse-grained (interface state) vs fine-grained (probe-based) failure detection

## Prerequisites

Complete the [base profile](../base/README.md) first.

## What This Profile Adds

### Track Objects

| Tracker Name | Interface | Tracked Property |
|-------------|-----------|------------------|
| TRACK-ISP1-UPLINK | Ethernet1 | line-protocol |
| TRACK-ISP2-UPLINK | Ethernet2 | line-protocol |

### Tracked Static Route

A floating static route to `203.0.113.0/24` (ISP1-only prefix) via the ISP1 next-hop, associated with TRACK-ISP1-UPLINK. When Ethernet1 goes down, the tracker transitions to Down and the static route is withdrawn from the routing table.

## Deploy

```bash
make deploy PROFILE=interface-tracking
```

## Verification Commands

### Check track object status

```bash
# On edge-router-1:
show track
```

**Expected**: TRACK-ISP1-UPLINK and TRACK-ISP2-UPLINK both show `Up`.

### Check tracked static route

```bash
show ip route static
show ip route 203.0.113.0/24
```

**Expected**: Static route to 203.0.113.0/24 via ISP1 next-hop is present.

## Failover Exercise

### Step 1: Verify baseline

```bash
show track
show ip route 203.0.113.0/24
```

### Step 2: Simulate ISP1 uplink failure

```bash
configure
interface Ethernet1
  shutdown
end
```

### Step 3: Observe tracker transition

```bash
show track
```

**Expected**: TRACK-ISP1-UPLINK transitions to `Down` immediately (line-protocol change is detected within seconds).

### Step 4: Verify route withdrawal

```bash
show ip route 203.0.113.0/24
```

**Expected**: The tracked static route is no longer in the routing table. Traffic to 203.0.113.0/24 now follows the BGP-learned route (if available via ISP2 or iBGP).

### Step 5: Restore ISP1

```bash
configure
interface Ethernet1
  no shutdown
end
```

### Step 6: Verify recovery

```bash
show track
show ip route 203.0.113.0/24
```

**Expected**: TRACK-ISP1-UPLINK returns to `Up`. Static route is reinstalled.

## Validate

```bash
make validate PROFILE=interface-tracking
```

## Teardown

```bash
make destroy
```

## Comparison with Probe-Based Approaches

| Aspect | Interface Tracking | Monitor Connectivity / PingCheck |
|--------|-------------------|----------------------------------|
| Detection granularity | Interface state (up/down) | End-to-end reachability (ICMP) |
| Detection speed | Immediate (sub-second) | Seconds (probe interval + dampening) |
| Failure types caught | Physical link failures only | Link failures + L3 routing issues |
| False positives | Low | Possible (transient packet loss) |
| Configuration complexity | Simple (2-3 lines) | Moderate (probes + handlers) |
| Use case | Known single-homed uplinks | Complex or multi-hop paths |

## Key Takeaways

- Track objects on cEOS only support `interface line-protocol` — there is no probe-based tracking available
- Interface tracking provides the fastest detection (sub-second) but only catches physical link failures
- A link can be "up" at L1/L2 while the remote device is unreachable at L3 — track objects would not detect this
- For scenarios where L3 reachability matters (ISP router failure, upstream routing issue), use probe-based approaches like `monitor connectivity` or PingCheck
- Track objects are best suited for known single-homed uplinks where interface state directly correlates with path availability
