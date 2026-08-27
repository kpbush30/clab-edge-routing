"""Validation tests for monitor-connectivity and pingcheck failover profiles."""

from __future__ import annotations

import time
from typing import Any

import pytest


@pytest.mark.monitor_connectivity
class TestMonitorConnectivity:
    def test_connectivity_hosts_up(self, eapi_connection: Any) -> None:
        """Monitor connectivity hosts should both be Up."""
        conn = eapi_connection("edge-router-1")
        result = conn.run_commands(
            ["show monitor connectivity"], encoding="text"
        )
        output = result[0].get("output", "")
        assert "ISP1-GATEWAY" in output, "ISP1-GATEWAY host not configured"
        assert "ISP2-GATEWAY" in output, "ISP2-GATEWAY host not configured"

    def test_failover_on_isp1_down(self, eapi_connection: Any) -> None:
        """After shutting Ethernet1, local-preference should drop within 30s."""
        conn = eapi_connection("edge-router-1")

        conn.run_commands(
            ["enable", "configure", "interface Ethernet1", "shutdown"],
            encoding="text",
        )

        try:
            failover_detected = False
            for _ in range(6):
                time.sleep(5)
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
                for path in paths:
                    as_path = path.get("asPathEntry", {}).get("asPath", "")
                    if "64501" in as_path:
                        lp = path.get("localPreference", 100)
                        if lp < 100:
                            failover_detected = True
                            break
                if failover_detected:
                    break

            assert failover_detected, (
                "ISP1 local-preference did not drop below 100 within 30 seconds"
            )
        finally:
            conn.run_commands(
                ["enable", "configure", "interface Ethernet1", "no shutdown"],
                encoding="text",
            )

    def test_recovery_after_restore(self, eapi_connection: Any) -> None:
        """After restoring Ethernet1, local-preference should return to 200 within 60s."""
        conn = eapi_connection("edge-router-1")
        recovery_detected = False
        for _ in range(12):
            time.sleep(5)
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
            for path in paths:
                as_path = path.get("asPathEntry", {}).get("asPath", "")
                if "64501" in as_path:
                    lp = path.get("localPreference", 0)
                    if lp >= 200:
                        recovery_detected = True
                        break
            if recovery_detected:
                break

        assert recovery_detected, (
            "ISP1 local-preference did not restore to 200 within 60 seconds"
        )

    def test_core_shifts_to_isp2(self, eapi_connection: Any) -> None:
        """Core routing table should shift to ISP2 path during ISP1 failure."""
        conn = eapi_connection("edge-router-1")
        conn.run_commands(
            ["enable", "configure", "interface Ethernet1", "shutdown"],
            encoding="text",
        )

        try:
            time.sleep(15)

            core_conn = eapi_connection("core-router-1")
            result = core_conn.run_commands(
                ["show ip route 100.64.0.0/24"], encoding="json"
            )
            routes = (
                result[0]
                .get("vrfs", {})
                .get("default", {})
                .get("routes", {})
                .get("100.64.0.0/24", {})
            )
            assert routes, "100.64.0.0/24 missing from core routing table"
        finally:
            conn.run_commands(
                ["enable", "configure", "interface Ethernet1", "no shutdown"],
                encoding="text",
            )


@pytest.mark.pingcheck
class TestPingCheck:
    def test_daemon_running(self, eapi_connection: Any) -> None:
        """PingCheck daemon should be running with health status GOOD."""
        conn = eapi_connection("edge-router-1")
        result = conn.run_commands(
            ["show daemon PingCheck"], encoding="text"
        )
        output = result[0].get("output", "")
        assert "PingCheck" in output, "PingCheck daemon not found"

    def test_failover_on_isp1_down(self, eapi_connection: Any) -> None:
        """After shutting Ethernet1, PingCheck should detect failure and reduce local-pref."""
        conn = eapi_connection("edge-router-1")

        conn.run_commands(
            ["enable", "configure", "interface Ethernet1", "shutdown"],
            encoding="text",
        )

        try:
            failover_detected = False
            for _ in range(6):
                time.sleep(5)
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
                for path in paths:
                    as_path = path.get("asPathEntry", {}).get("asPath", "")
                    if "64501" in as_path:
                        lp = path.get("localPreference", 100)
                        if lp < 100:
                            failover_detected = True
                            break
                if failover_detected:
                    break

            assert failover_detected, (
                "PingCheck did not reduce ISP1 local-preference within 30 seconds"
            )
        finally:
            conn.run_commands(
                ["enable", "configure", "interface Ethernet1", "no shutdown"],
                encoding="text",
            )

    def test_recovery_after_restore(self, eapi_connection: Any) -> None:
        """After restoring Ethernet1, PingCheck should recover and restore local-pref."""
        conn = eapi_connection("edge-router-1")
        recovery_detected = False
        for _ in range(12):
            time.sleep(5)
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
            for path in paths:
                as_path = path.get("asPathEntry", {}).get("asPath", "")
                if "64501" in as_path:
                    lp = path.get("localPreference", 0)
                    if lp >= 200:
                        recovery_detected = True
                        break
            if recovery_detected:
                break

        assert recovery_detected, (
            "PingCheck did not restore ISP1 local-preference within 60 seconds"
        )
