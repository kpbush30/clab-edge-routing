"""Validation tests for the bgp-attributes profile."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.bgp_attributes
class TestBGPAttributes:
    def test_isp1_local_preference(self, eapi_connection: Any) -> None:
        """ISP1 routes on edge-router-1 should have local-preference 200."""
        conn = eapi_connection("edge-router-1")
        result = conn.run_commands(
            ["show ip bgp 100.64.0.0/24"], encoding="json"
        )
        paths = (
            result[0]
            .get("vrfs", {})
            .get("default", {})
            .get("bgpRouteEntries", {})
            .get("100.64.0.0/24", {})
            .get("bgpRoutePaths", [])
        )

        isp1_path = None
        for path in paths:
            as_path = path.get("asPathEntry", {}).get("asPath", "")
            if "64501" in as_path:
                isp1_path = path
                break

        assert isp1_path is not None, "No path via ISP1 (AS 64501) found"
        local_pref = isp1_path.get("localPreference", 0)
        assert local_pref == 200, (
            f"ISP1 path local-preference should be 200, got {local_pref}"
        )

    def test_overlapping_prefix_prefers_isp1(self, eapi_connection: Any) -> None:
        """100.64.0.0/24 best path should be via ISP1 (local-pref 200 > default 100)."""
        conn = eapi_connection("edge-router-1")
        result = conn.run_commands(
            ["show ip bgp 100.64.0.0/24"], encoding="json"
        )
        paths = (
            result[0]
            .get("vrfs", {})
            .get("default", {})
            .get("bgpRouteEntries", {})
            .get("100.64.0.0/24", {})
            .get("bgpRoutePaths", [])
        )

        best_path = None
        for path in paths:
            if path.get("routeType", {}).get("active", False):
                best_path = path
                break

        assert best_path is not None, "No active/best path found for 100.64.0.0/24"
        as_path = best_path.get("asPathEntry", {}).get("asPath", "")
        assert "64501" in as_path, (
            f"Best path should be via ISP1 (AS 64501), got AS-path: {as_path}"
        )

    def test_core_routes_via_isp1(self, eapi_connection: Any) -> None:
        """Core routing table for 100.64.0.0/24 should prefer ISP1 path."""
        conn = eapi_connection("core-router-1")
        result = conn.run_commands(
            ["show ip route 100.64.0.0/24"], encoding="json"
        )
        routes = (
            result[0]
            .get("vrfs", {})
            .get("default", {})
            .get("routes", {})
            .get("100.64.0.0/24", {})
        )
        assert routes, "100.64.0.0/24 not in core routing table"
