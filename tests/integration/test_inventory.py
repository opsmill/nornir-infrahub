"""Integration tests for InfrahubInventory."""

import pytest
from nornir_infrahub.plugins.inventory.infrahub import InfrahubInventory

from .conftest import TEST_TOKEN, NornirInfrahubIntegration


@pytest.mark.integration
class TestInventoryBasic(NornirInfrahubIntegration):
    def test_all_devices_loaded(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice"},
            address=infrahub_address,
            token=TEST_TOKEN,
        ).load()

        assert len(inventory.hosts) == 3

    def test_host_names_match(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice"},
            address=infrahub_address,
            token=TEST_TOKEN,
        ).load()

        assert "router-1" in inventory.hosts
        assert "router-2" in inventory.hosts
        assert "switch-1" in inventory.hosts


@pytest.mark.integration
class TestSchemaMappings(NornirInfrahubIntegration):
    def test_ip_address_mapping(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice", "include": ["primary_address"]},
            address=infrahub_address,
            token=TEST_TOKEN,
            schema_mappings=[{"name": "hostname", "mapping": "primary_address.address"}],
        ).load()

        assert inventory.hosts["router-1"].hostname == "10.0.0.1"
        assert inventory.hosts["router-2"].hostname == "10.0.0.2"
        assert inventory.hosts["switch-1"].hostname == "10.0.0.3"

    def test_platform_mapping(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice", "include": ["platform"]},
            address=infrahub_address,
            token=TEST_TOKEN,
            schema_mappings=[{"name": "platform", "mapping": "platform.nornir_platform"}],
        ).load()

        assert inventory.hosts["router-1"].platform == "arista_eos"
        assert inventory.hosts["router-2"].platform == "juniper_junos"
        assert inventory.hosts["switch-1"].platform == "arista_eos"

    def test_multiple_mappings(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice", "include": ["primary_address", "platform"]},
            address=infrahub_address,
            token=TEST_TOKEN,
            schema_mappings=[
                {"name": "hostname", "mapping": "primary_address.address"},
                {"name": "platform", "mapping": "platform.nornir_platform"},
            ],
        ).load()

        assert inventory.hosts["router-1"].hostname == "10.0.0.1"
        assert inventory.hosts["router-1"].platform == "arista_eos"


@pytest.mark.integration
class TestGroupMappings(NornirInfrahubIntegration):
    def test_site_groups_created(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice", "include": ["site"]},
            address=infrahub_address,
            token=TEST_TOKEN,
            group_mappings=["site.name"],
        ).load()

        assert "site__chicago" in inventory.groups
        assert "site__nyc" in inventory.groups

    def test_hosts_in_correct_site_groups(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice", "include": ["site"]},
            address=infrahub_address,
            token=TEST_TOKEN,
            group_mappings=["site.name"],
        ).load()

        chicago_members = {
            name for name, host in inventory.hosts.items() if any(g.name == "site__chicago" for g in host.groups)
        }
        assert chicago_members == {"router-1", "router-2"}

        nyc_members = {
            name for name, host in inventory.hosts.items() if any(g.name == "site__nyc" for g in host.groups)
        }
        assert nyc_members == {"switch-1"}


@pytest.mark.integration
class TestGroupMembership(NornirInfrahubIntegration):
    def test_standard_group_appears(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice"},
            address=infrahub_address,
            token=TEST_TOKEN,
        ).load()

        assert "core-routers" in inventory.groups

    def test_router1_in_core_routers(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice"},
            address=infrahub_address,
            token=TEST_TOKEN,
        ).load()

        router1_groups = {g.name for g in inventory.hosts["router-1"].groups}
        assert "core-routers" in router1_groups

    def test_other_hosts_not_in_core_routers(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice"},
            address=infrahub_address,
            token=TEST_TOKEN,
        ).load()

        router2_groups = {g.name for g in inventory.hosts["router-2"].groups}
        switch1_groups = {g.name for g in inventory.hosts["switch-1"].groups}
        assert "core-routers" not in router2_groups
        assert "core-routers" not in switch1_groups


@pytest.mark.integration
class TestFilters(NornirInfrahubIntegration):
    def test_filter_by_site(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice", "filters": {"site__name__value": "chicago"}},
            address=infrahub_address,
            token=TEST_TOKEN,
        ).load()

        assert len(inventory.hosts) == 2
        assert "router-1" in inventory.hosts
        assert "router-2" in inventory.hosts
        assert "switch-1" not in inventory.hosts

    def test_filter_by_platform(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice", "filters": {"platform__name__value": "eos"}},
            address=infrahub_address,
            token=TEST_TOKEN,
        ).load()

        assert len(inventory.hosts) == 2
        assert "router-1" in inventory.hosts
        assert "switch-1" in inventory.hosts
        assert "router-2" not in inventory.hosts


@pytest.mark.integration
class TestBranch(NornirInfrahubIntegration):
    def test_main_branch_has_three_hosts(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice"},
            address=infrahub_address,
            token=TEST_TOKEN,
            branch="main",
        ).load()

        assert len(inventory.hosts) == 3
        assert "router-3" not in inventory.hosts

    def test_feature_branch_has_four_hosts(self, infrahub_address: str) -> None:
        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice"},
            address=infrahub_address,
            token=TEST_TOKEN,
            branch="test-branch",
        ).load()

        assert len(inventory.hosts) == 4
        assert "router-3" in inventory.hosts
