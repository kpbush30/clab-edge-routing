# Monitor Connectivity Profile: Event-Handler Reactive Failover

**Difficulty**: Intermediate

## Learning Objectives

- Understand how `monitor connectivity` probes track ISP gateway reachability
- See how `event-handler on-logging` reacts to syslog messages from connectivity monitor
- Observe automated ISP failover by dynamically changing local-preference
- Understand the trade-offs of syslog-regex-based automation (fragility, lack of built-in dampening)

## Prerequisites

Complete the [bgp-attributes profile](../bgp-attributes/README.md) first — this profile extends it.

## What This Profile Adds

### Monitor Connectivity Hosts

| Host Name | Target IP | Source Interface | Purpose |
|-----------|-----------|------------------|---------|
| ISP1-GATEWAY | 10.0.1.1 (edge-router-1) / 10.0.1.5 (edge-router-2) | Ethernet1 | Monitors ISP1 reachability |
| ISP2-GATEWAY | 10.0.2.1 (edge-router-1) / 10.0.2.5 (edge-router-2) | Ethernet2 | Monitors ISP2 reachability |

### Event Handlers

| Handler | Trigger | Action | Delay |
|---------|---------|--------|-------|
| ISP1-DOWN | Syslog: ISP1-GATEWAY is now down | Set local-preference to 50 via FastCli | 5 seconds |
| ISP1-UP | Syslog: ISP1-GATEWAY is now up | Restore local-preference to 200 via FastCli | 5 seconds |

## Deploy

```bash
make deploy PROFILE=monitor-connectivity
```

## Verification Commands

### Check monitor connectivity status

```bash
# On edge-router-1:
show monitor connectivity
```

**Expected**: Both ISP1-GATEWAY and ISP2-GATEWAY show status `Up`.

### Check event-handler configuration

```bash
show event-handler
```

**Expected**: ISP1-DOWN and ISP1-UP event handlers configured with on-logging triggers.

## Failover Exercise

### Step 1: Verify baseline

```bash
show ip bgp 100.64.0.0/24
```

ISP1 path should show local-preference 200 (preferred).

### Step 2: Simulate ISP1 failure

```bash
configure
interface Ethernet1
  shutdown
end
```

### Step 3: Observe failover

```bash
# Watch syslog for connectivity monitor event:
show logging last 20

# After ~10 seconds, check BGP table:
show ip bgp 100.64.0.0/24
```

**Expected**: ISP1 path local-preference drops to 50. ISP2 becomes the best path.

### Step 4: Restore ISP1

```bash
configure
interface Ethernet1
  no shutdown
end
```

### Step 5: Verify recovery

```bash
# After ~10 seconds:
show ip bgp 100.64.0.0/24
```

**Expected**: ISP1 path local-preference returns to 200. ISP1 becomes preferred again.

## Validate

```bash
make validate PROFILE=monitor-connectivity
```

## Teardown

```bash
make destroy
```

## Key Takeaways

- `monitor connectivity` provides ICMP probe-based reachability tracking, similar to Cisco IP SLA
- EOS has no native consumer that links connectivity monitor state to BGP policy — you must bridge the gap with `event-handler`
- Event handlers use syslog regex matching, which is fragile — changes to log message format can break the trigger
- The `delay` field provides basic dampening but no HOLDUP/HOLDDOWN logic like PingCheck offers
- For production use, consider [PingCheck](../pingcheck/README.md) which provides built-in dampening and cleaner integration
