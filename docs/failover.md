# Failover mechanics and how to trigger them

This lab shows two independent failure-detection mechanisms working
together, and it's worth understanding both before you start pulling links:

- **BFD** catches *hard* failures — a link or a BGP peer actually goes down.
  Detection is sub-second, well ahead of BGP's own hold-timer.
- **Connectivity monitor + event-handler** catches *soft* failures — the
  local link and BGP session are completely healthy, but the ISP's own
  upstream has gone dark. BFD and BGP have nothing to trigger on in this
  case, since nothing adjacent to the router actually failed.

Only `edge-router1` (the ISP1/primary side) runs the connectivity-monitor
automation. `edge-router2` (ISP2/backup) is a static, always-available
fallback path with no automation of its own.

## How the automated failover works

Two route-maps on `edge-router1` control both directions of traffic:

- **`ISP-IN`** (applied inbound from ISP1) sets **local-preference**, which
  decides which ISP `edge-router1`/`edge-router2` send *outbound* traffic
  through. Healthy: `200` (beats edge-router2's static `50`). Down: `40`
  (drops below edge-router2's `50`, so both edge routers start using ISP2
  instead).
- **`ISP-OUT`** (applied outbound to ISP1) sets **AS-path prepend** on the
  `11.11.11.0/24` internal prefix, which influences which path *the internet*
  uses to send traffic *back in*. Healthy: no prepend (shortest AS-path,
  preferred). Down: prepended 4x (longer than edge-router2's permanent 3x
  prepend, so ISP2 becomes preferred inbound too).

`edge-router1` runs `monitor connectivity` probes to real hosts beyond ISP1
(`100.64.0.1`, `1.1.1.1`, `199.7.83.42`) out Ethernet1. When those probes
fail, EOS logs a `CONNECTIVITYMON-5-HOST_UNREACHABLE` event; the
`ISP1-DOWN` event-handler reacts to that log message by flipping both
route-maps and issuing `clear bgp peer-group ISP1 soft in` to re-apply them
— failing over both directions of traffic at once, from a single trigger,
with no external automation involved. `ISP1-UP` reverses it ~5 seconds after
`CONNECTIVITYMON-5-HOST_REACHABLE` is logged (a short delay to avoid
flapping).

## Watching it happen

Every edge router and `isp-router3` have a built-in alias, **`wroutes`**,
that watches the relevant route flip in real time:

- On `edge-router1` / `edge-router2`: `wroutes` = `watch 1 diff sh ip route
  1.1.1.1 detail` — watch which ISP the edge routers are using *outbound*.
- On `isp-router3`: `wroutes` = `watch 1 diff sh ip route 11.11.11.11
  detail` — watch which edge router the internet is using to reach the
  internal LAN *inbound*.

Open a terminal on `edge-router1` and one on `isp-router3` and run `wroutes`
in each before triggering a failure — you'll see both flip together.

## Scenario A — Hard failure (BFD): kill the ISP1 link

```bash
docker exec -it isp-router1 Cli
isp-router1> enable
isp-router1# configure
isp-router1(config)# interface Ethernet1
isp-router1(config-if-Et1)# shutdown
```

Watch on `edge-router1`:

```
show bfd peers          # ISP1 session drops almost immediately
show ip bgp summary     # ISP1 neighbor goes to Idle in well under a second
show ip route 1.1.1.1   # now via edge-router2 / ISP2
```

This is the fast path: BFD detects the down link/session directly, so the
route is gone and re-selected almost instantly. The connectivity-monitor /
event-handler logic never gets involved — there's nothing to detect, the
neighbor is just gone.

Restore it:

```
isp-router1(config-if-Et1)# no shutdown
```

## Scenario B — Soft failure (connectivity monitor): fail ISP1 without touching the link

This is the scenario the lab is really built to demonstrate. Instead of
taking down a link or BGP session, black-hole *only* the monitored
destination (`100.64.0.1`, ISP-router3's simulated internet address) at
`isp-router1` with a `Null0` static route. The `edge-router1` ↔ `isp-router1`
link and BGP/BFD session stay completely healthy the entire time — this is
what makes it a "soft" failure that only an active reachability probe can
catch.

```bash
docker exec -it isp-router1 Cli
isp-router1> enable
isp-router1# configure
isp-router1(config)# ip route 100.64.0.1/32 Null0
```

Watch on `edge-router1` (give it a few probe intervals):

```
show monitor connectivity host                  # INTERNET/Cloudflare_DNS/Root_Server -> unreachable
show logging | grep CONNECTIVITYMON              # CONNECTIVITYMON-5-HOST_UNREACHABLE ... INTERNET ... Ethernet1
show ip bgp summary                              # ISP1 neighbor stays Established the whole time
show route-map ISP-IN                            # local-preference now 40
show route-map ISP-OUT                           # as-path prepend re-applied
show ip route 1.1.1.1                            # flips to ISP2, even though the ISP1 session is still up
```

And on `isp-router3`:

```
show ip bgp 11.11.11.0/24    # AS-path via edge-router1 is now longer than via edge-router2
```

That's the point of the lab: the BGP session and the physical link to ISP1
never went down, so BFD had nothing to detect — only an active
reachability probe past the immediate neighbor caught the failure.

Restore it:

```
isp-router1(config)# no ip route 100.64.0.1/32 Null0
```

`isp-router1`'s running-config also has a `pull route on` / `pull route
off` CLI alias that wraps this same static route as a shortcut. It isn't
saved to the tracked startup-config yet, so it won't be there after a fresh
`make deploy`/`make recreate` — the explicit `ip route` commands above will
always work.
