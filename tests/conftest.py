"""Pytest fixtures for edge routing lab validation."""

from __future__ import annotations

from typing import Any

import pyeapi
import pytest

DEVICE_MGMT_IPS: dict[str, str] = {
    "isp-router-1": "172.100.100.2",
    "isp-router-2": "172.100.100.3",
    "edge-router-1": "172.100.100.4",
    "edge-router-2": "172.100.100.5",
    "core-router-1": "172.100.100.6",
}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--profile",
        action="store",
        default="base",
        help="Active lab profile name",
    )


@pytest.fixture
def profile(request: pytest.FixtureRequest) -> str:
    value: str = request.config.getoption("--profile")
    return value


@pytest.fixture
def topology_devices() -> list[str]:
    return list(DEVICE_MGMT_IPS.keys())


@pytest.fixture
def eapi_connection() -> Any:
    """Factory fixture returning a pyeapi Node for a given device name."""
    connections: dict[str, Any] = {}

    def _connect(device_name: str) -> Any:
        if device_name not in connections:
            mgmt_ip = DEVICE_MGMT_IPS[device_name]
            connections[device_name] = pyeapi.connect(
                transport="https",
                host=mgmt_ip,
                username="admin",
                password="admin",
                return_node=True,
            )
        return connections[device_name]

    return _connect
