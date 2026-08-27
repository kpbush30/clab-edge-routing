"""Validation tests for the interface-tracking profile."""

from __future__ import annotations

import time
from typing import Any

import pytest


@pytest.mark.interface_tracking
class TestInterfaceTracking:
    def test_tracker_up(self, eapi_connection: Any) -> None:
        """Track objects should show Up when interfaces are up."""
        conn = eapi_connection("edge-router-1")
        result = conn.run_commands(["show track"], encoding="text")
        output = result[0].get("output", "")
        assert "TRACK-ISP1-UPLINK" in output, "TRACK-ISP1-UPLINK not configured"
        assert "TRACK-ISP2-UPLINK" in output, "TRACK-ISP2-UPLINK not configured"

    def test_static_route_present(self, eapi_connection: Any) -> None:
        """Static route to 203.0.113.0/24 should be in routing table when tracker is Up."""
        conn = eapi_connection("edge-router-1")
        result = conn.run_commands(
            ["show ip route 203.0.113.0/24"], encoding="json"
        )
        routes = (
            result[0]
            .get("vrfs", {})
            .get("default", {})
            .get("routes", {})
        )
        assert "203.0.113.0/24" in routes, (
            "Static route 203.0.113.0/24 not in routing table"
        )

    def test_tracker_down_on_shutdown(self, eapi_connection: Any) -> None:
        """After shutting Ethernet1, tracker should transition to Down within 5s."""
        conn = eapi_connection("edge-router-1")

        conn.run_commands(
            ["enable", "configure", "interface Ethernet1", "shutdown"],
            encoding="text",
        )

        try:
            time.sleep(5)
            result = conn.run_commands(["show track"], encoding="text")
            output = result[0].get("output", "")
            lines = output.split("\n")
            for i, line in enumerate(lines):
                if "TRACK-ISP1-UPLINK" in line:
                    tracker_section = "\n".join(lines[i : i + 5])
                    assert "Down" in tracker_section, (
                        f"TRACK-ISP1-UPLINK should be Down, got: {tracker_section}"
                    )
                    break
        finally:
            conn.run_commands(
                ["enable", "configure", "interface Ethernet1", "no shutdown"],
                encoding="text",
            )

    def test_static_route_withdrawn(self, eapi_connection: Any) -> None:
        """Static route should be withdrawn when tracker is Down."""
        conn = eapi_connection("edge-router-1")

        conn.run_commands(
            ["enable", "configure", "interface Ethernet1", "shutdown"],
            encoding="text",
        )

        try:
            time.sleep(5)
            result = conn.run_commands(
                ["show ip route static"], encoding="json"
            )
            routes = (
                result[0]
                .get("vrfs", {})
                .get("default", {})
                .get("routes", {})
            )
            tracked_route = routes.get("203.0.113.0/24")
            assert tracked_route is None or not tracked_route, (
                "Tracked static route 203.0.113.0/24 should be withdrawn when tracker is Down"
            )
        finally:
            conn.run_commands(
                ["enable", "configure", "interface Ethernet1", "no shutdown"],
                encoding="text",
            )

    def test_tracker_restores(self, eapi_connection: Any) -> None:
        """After restoring Ethernet1, tracker and static route should recover."""
        conn = eapi_connection("edge-router-1")
        time.sleep(5)

        result = conn.run_commands(["show track"], encoding="text")
        output = result[0].get("output", "")
        lines = output.split("\n")
        for i, line in enumerate(lines):
            if "TRACK-ISP1-UPLINK" in line:
                tracker_section = "\n".join(lines[i : i + 5])
                assert "Up" in tracker_section, (
                    f"TRACK-ISP1-UPLINK should be Up after restore, got: {tracker_section}"
                )
                break

        result = conn.run_commands(
            ["show ip route 203.0.113.0/24"], encoding="json"
        )
        routes = (
            result[0]
            .get("vrfs", {})
            .get("default", {})
            .get("routes", {})
        )
        assert "203.0.113.0/24" in routes, (
            "Static route 203.0.113.0/24 should be reinstalled after tracker restores"
        )
