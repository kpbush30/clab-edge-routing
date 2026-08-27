"""Validation tests for the base profile."""

from __future__ import annotations

from typing import Any

import pytest

EXPECTED_DEVICES = [
    "isp-router-1",
    "isp-router-2",
    "edge-router-1",
    "edge-router-2",
    "core-router-1",
]

EXPECTED_BGP_NEIGHBORS = {
    "isp-router-1": 2,
    "isp-router-2": 2,
    "edge-router-1": 4,
    "edge-router-2": 4,
    "core-router-1": 2,
}

CORE_EXPECTED_PREFIXES = [
    "203.0.113.0/24",
    "198.51.100.0/24",
    "100.64.0.0/24",
]


@pytest.mark.base
class TestBaseTopology:
    def test_all_devices_reachable(self, eapi_connection: Any, topology_devices: list[str]) -> None:
        for device in EXPECTED_DEVICES:
            conn = eapi_connection(device)
            result = conn.run_commands(["show version"], encoding="json")
            assert result[0].get("modelName"), f"{device} not reachable via eAPI"

    def test_bgp_neighbors_established(self, eapi_connection: Any) -> None:
        for device, expected_count in EXPECTED_BGP_NEIGHBORS.items():
            conn = eapi_connection(device)
            result = conn.run_commands(["show ip bgp summary"], encoding="json")
            peers = result[0].get("vrfs", {}).get("default", {}).get("peers", {})

            established = [
                peer_ip
                for peer_ip, info in peers.items()
                if info.get("peerState") == "Established"
            ]
            assert len(established) == expected_count, (
                f"{device}: expected {expected_count} Established peers, "
                f"got {len(established)} ({established})"
            )

    def test_core_has_all_bgp_prefixes(self, eapi_connection: Any) -> None:
        conn = eapi_connection("core-router-1")
        result = conn.run_commands(["show ip route bgp"], encoding="json")
        routes = result[0].get("vrfs", {}).get("default", {}).get("routes", {})

        for prefix in CORE_EXPECTED_PREFIXES:
            assert prefix in routes, (
                f"core-router-1 missing BGP prefix {prefix}. "
                f"Present routes: {list(routes.keys())}"
            )

    def test_ibgp_next_hop_self(self, eapi_connection: Any) -> None:
        for edge in ["edge-router-1", "edge-router-2"]:
            conn = eapi_connection(edge)
            result = conn.run_commands(
                ["show ip bgp 100.64.0.0/24"], encoding="json"
            )
            bgp_entries = (
                result[0]
                .get("vrfs", {})
                .get("default", {})
                .get("bgpRouteEntries", {})
                .get("100.64.0.0/24", {})
                .get("bgpRoutePaths", [])
            )

            ibgp_paths = [
                path
                for path in bgp_entries
                if path.get("routeType", {}).get("origin", "") == "IGP"
                and "i" in str(path.get("routeType", {}).get("valid", ""))
            ]
            if ibgp_paths:
                for path in ibgp_paths:
                    next_hop = path.get("nextHop", "")
                    assert next_hop.startswith("10.0.3."), (
                        f"{edge}: iBGP path next-hop should be peer edge router "
                        f"(10.0.3.x), got {next_hop}"
                    )
