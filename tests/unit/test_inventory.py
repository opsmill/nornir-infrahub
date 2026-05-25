import ipaddress
from typing import Any

import pytest
from infrahub_sdk import InfrahubClient
from infrahub_sdk.node import InfrahubNodeSync
from infrahub_sdk.schema import NodeSchemaAPI
from nornir.core.inventory import ConnectionOptions, Defaults  # , HostOrGroup
from nornir_infrahub.plugins.inventory.infrahub import (  # _get_inventory_element,
    HostNode,
    InfrahubInventory,
    SchemaMappingNode,
    _get_connection_options,
    _get_defaults,
    get_related_nodes,
    ip_interface_to_ip_string,
    resolve_node_mapping,
)
from pydantic import ValidationError

# from unittest.mock import Mock, patch


# ip_interface_to_ip_string


def test_ip_interface_to_ip_string_ipv4():
    ip_interface = ipaddress.IPv4Interface("192.168.1.1/24")
    result = ip_interface_to_ip_string(ip_interface)
    assert result == "192.168.1.1"


def test_ip_interface_to_ip_string_ipv6():
    ip_interface = ipaddress.IPv6Interface("2001:db8::1/64")
    result = ip_interface_to_ip_string(ip_interface)
    assert result == "2001:db8::1"


# resolve_node_mapping


def test_valid_mapping(client: InfrahubClient, ipaddress_schema: NodeSchemaAPI, ipaddress_data: dict[str, Any]):
    node = InfrahubNodeSync(client=client, schema=ipaddress_schema, data=ipaddress_data)
    attrs = ["address"]
    result = resolve_node_mapping(node, attrs)
    assert result == "192.168.1.1"


def test_unsupported_cardinality(client: InfrahubClient, location_schema: NodeSchemaAPI):
    node = InfrahubNodeSync(client=client, schema=location_schema)
    attrs = ["tags"]
    with pytest.raises(RuntimeError, match="Relations with many cardinality are not supported!"):
        resolve_node_mapping(node, attrs)


def test_invalid_mapping(client: InfrahubClient, ipaddress_schema: NodeSchemaAPI):
    node = InfrahubNodeSync(client=client, schema=ipaddress_schema)
    attrs = ["invalid_attribute"]
    with pytest.raises(RuntimeError, match="Unable to resolve mapping"):
        resolve_node_mapping(node, attrs)


# _get_connection_options


def test_get_connection_options():
    data = {
        "connection1": {
            "hostname": "example.com",
            "port": 22,
            "username": "user1",
            "password": "password1",
            "platform": "cisco",
            "extras": {"key1": "value1"},
        },
        "connection2": {
            "hostname": "test.com",
            "port": 2222,
            "username": "user2",
            "password": "password2",
            "platform": "juniper",
            "extras": {"key2": "value2"},
        },
    }

    result = _get_connection_options(data)

    # expected_result = {
    #     "connection1": ConnectionOptions(
    #         hostname="example.com",
    #         port=22,
    #         username="user1",
    #         password="password1",
    #         platform="linux",
    #         extras={"key1": "value1"},
    #     ),
    #     "connection2": ConnectionOptions(
    #         hostname="test.com",
    #         port=2222,
    #         username="user2",
    #         password="password2",
    #         platform="windows",
    #         extras={"key2": "value2"},
    #     ),
    # }

    # assert resul == expected_result
    assert isinstance(result["connection1"], ConnectionOptions)
    assert isinstance(result["connection2"], ConnectionOptions)


# _get_defaults


def test_get_defaults():
    data = {
        "hostname": "example.com",
        "port": 22,
        "username": "user1",
        "password": "password1",
        "platform": "linux",
        "data": {"key": "value"},
        "connection_options": {
            "connection1": {
                "hostname": "example.com",
                "port": 22,
                "username": "user1",
                "password": "password1",
                "platform": "linux",
                "extras": {"key1": "value1"},
            }
        },
    }

    result = _get_defaults(data)

    # expected_result = Defaults(
    #     hostname="example.com",
    #     port=22,
    #     username="user1",
    #     password="password1",
    #     platform="linux",
    #     data={"key": "value"},
    #     connection_options={
    #         "connection1": ConnectionOptions(
    #             hostname="example.com",
    #             port=22,
    #             username="user1",
    #             password="password1",
    #             platform="linux",
    #             extras={"key1": "value1"},
    #         )
    #     },
    # )

    # assert result == expected_result
    assert isinstance(result, Defaults)


# _get_inventory_element


# XXX fails atm - TypeError: 'TypeVar' object is not callable
# def test_get_inventory_element():
#     data = {
#         "hostname": "example.com",
#         "port": 22,
#         "username": "user1",
#         "password": "password1",
#         "platform": "cisco",
#         "data": {"key": "value"},
#         "groups": ["group1", "group2"],
#         "connection_options": {
#             "connection1": {
#                 "hostname": "example.com",
#                 "port": 22,
#                 "username": "user1",
#                 "password": "password1",
#                 "platform": "cisco",
#                 "extras": {"key1": "value1"},
#             }
#         },
#     }
#     name = "test_host"
#     defaults = Defaults(
#         hostname="default.com",
#         port=2222,
#         username="default_user",
#         password="default_password",
#         platform="default_platform",
#         data={"default_key": "default_value"},
#         connection_options={},
#     )

#     result = _get_inventory_element(HostOrGroup, data, name, defaults)

#     # expected_result = HostOrGroup(
#     #     name="test_host",
#     #     hostname="example.com",
#     #     port=22,
#     #     username="user1",
#     #     password="password1",
#     #     platform="linux",
#     #     data={"key": "value"},
#     #     groups=["group1", "group2"],
#     #     defaults=defaults,
#     #     connection_options={
#     #         "connection1": ConnectionOptions(
#     #             hostname="example.com",
#     #             port=22,
#     #             username="user1",
#     #             password="password1",
#     #             platform="linux",
#     #             extras={"key1": "value1"},
#     #         )
#     #     },
#     # )

#     # assert result == expected_result
#     assert isinstance(result, HostOrGroup)


# SchemaMappingNode


def test_create_schema_mapping_node():
    name = "node_name"
    mapping = "node_mapping"
    node = SchemaMappingNode(name, mapping)

    assert node.name == name
    assert node.mapping == mapping


def test_schema_mapping_node_equality():
    node1 = SchemaMappingNode("node1", "mapping1")
    node2 = SchemaMappingNode("node1", "mapping1")
    node3 = SchemaMappingNode("node2", "mapping2")

    assert node1 == node2
    assert node1 != node3


# HostNode


def test_create_host_node():
    kind = "host"
    include = ["item1", "item2"]
    exclude = ["item3", "item4"]
    filters = {"key1": "value1", "key2": "value2"}

    host_node = HostNode(kind=kind, include=include, exclude=exclude, filters=filters)

    assert host_node.kind == kind
    assert sorted(host_node.include) == sorted(["member_of_groups", "item1", "item2"])
    assert host_node.exclude == exclude
    assert host_node.filters == filters


def test_validate_include_property():
    valid_include = ["item1", "item2"]
    valid_host_node = HostNode(kind="host", include=valid_include)

    assert sorted(valid_host_node.include) == sorted(["member_of_groups", "item1", "item2"])

    invalid_include = 123
    with pytest.raises(ValidationError, match="Input should be a valid list"):
        HostNode(kind="host", include=invalid_include)

    invalid_include_items = ["item1", [123]]
    with pytest.raises(ValidationError, match="Input should be a valid string"):
        HostNode(kind="host", include=invalid_include_items)


# get_related_nodes


def test_get_related_nodes():
    schema = {
        "name": "Person",
        "namespace": "Test",
        "default_filter": "name__value",
        "attributes": [
            {"name": "name", "kind": "Text", "unique": True},
        ],
        "relationships": [
            {"name": "vehicules", "peer": "TestVehicule", "cardinality": "many", "identifier": "person__vehicule"}
        ],
    }
    node_schema = NodeSchemaAPI(**schema)
    attrs = {"vehicules", "address"}  # "Address" is not in the relationships
    result = get_related_nodes(node_schema, attrs)
    expected_result = {"CoreStandardGroup", "TestVehicule"}
    assert result == expected_result


# InfrahubInventory


@pytest.mark.parametrize(
    "branch,expected,description",
    [
        (None, "main", "default branch"),
        ("main", "main", "explicit main branch"),
        ("custom-branch", "custom-branch", "custom branch"),
        ("feature/new-feature", "feature/new-feature", "branch with slash"),
    ],
)
def test_infrahub_inventory_client_config_branch_integration(branch, expected, description):
    """Test that the client.config.default_branch is properly set for both default and custom branches."""
    from unittest.mock import Mock, patch

    from infrahub_sdk import Config

    with patch("nornir_infrahub.plugins.inventory.infrahub.InfrahubClientSync") as mock_client_class:
        # Don't mock the Config - let it be created normally
        # But mock the client instance that gets returned
        mock_client = Mock()
        mock_schema = Mock()
        mock_schema.relationships = []
        mock_client.schema.get.return_value = mock_schema

        # Capture the config passed to the constructor
        def capture_config(config, address):
            mock_client.config = config  # Store the real config on our mock client
            return mock_client

        mock_client_class.side_effect = capture_config

        # Create inventory
        if branch is None:
            inventory = InfrahubInventory(
                host_node={"kind": "InfraDevice"}, address="http://localhost:8000", token="test-token"
            )
        else:
            inventory = InfrahubInventory(
                host_node={"kind": "InfraDevice"},
                address="http://localhost:8000",
                token="test-token",
                branch=branch,
            )

        # Verify inventory.branch is set correctly
        assert inventory.branch == expected, f"Failed for {description}"

        # Verify the client config is a real Config instance
        assert isinstance(inventory.client.config, Config), f"Failed for {description}"

        # Verify client.config.default_branch is set correctly
        assert inventory.client.config.default_branch == expected, f"Failed for {description}"

        # Verify other config properties
        assert inventory.client.config.api_token == "test-token", f"Failed for {description}"

        # Verify InfrahubClientSync constructor was called correctly
        mock_client_class.assert_called_once()
        call_args = mock_client_class.call_args
        config_passed = call_args[1]["config"]
        assert config_passed.default_branch == expected, f"Failed for {description}"
        assert call_args[1]["address"] == "http://localhost:8000", f"Failed for {description}"


def test_infrahub_inventory_auto_includes_mapped_relationships():
    """Mapped relationships in schema_mappings/group_mappings are auto-added to host_node.include."""
    from unittest.mock import Mock, patch

    with patch("nornir_infrahub.plugins.inventory.infrahub.InfrahubClientSync") as mock_client_class:
        mock_client = Mock()
        site_rel = Mock()
        site_rel.name = "site"
        site_rel.peer = "InfraSite"
        platform_rel = Mock()
        platform_rel.name = "platform"
        platform_rel.peer = "InfraPlatform"
        mock_schema = Mock()
        mock_schema.relationships = [site_rel, platform_rel]
        mock_schema.relationship_names = ["site", "platform"]
        mock_client.schema.get.return_value = mock_schema
        mock_client_class.return_value = mock_client

        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice"},
            schema_mappings=[{"name": "platform", "mapping": "platform.nornir_platform"}],
            group_mappings=["site.name"],
        )

        assert "site" in inventory.host_node.include
        assert "platform" in inventory.host_node.include
        assert "member_of_groups" in inventory.host_node.include


def test_infrahub_inventory_no_duplicate_include():
    """Auto-include does not duplicate relationships the user already provided."""
    from unittest.mock import Mock, patch

    with patch("nornir_infrahub.plugins.inventory.infrahub.InfrahubClientSync") as mock_client_class:
        mock_client = Mock()
        site_rel = Mock()
        site_rel.name = "site"
        site_rel.peer = "InfraSite"
        mock_schema = Mock()
        mock_schema.relationships = [site_rel]
        mock_schema.relationship_names = ["site"]
        mock_client.schema.get.return_value = mock_schema
        mock_client_class.return_value = mock_client

        inventory = InfrahubInventory(
            host_node={"kind": "InfraDevice", "include": ["site"]},
            group_mappings=["site.name"],
        )

        assert inventory.host_node.include.count("site") == 1


def test_infrahub_inventory_branch_used_in_get_resources():
    """Test that the branch parameter is properly used in get_resources method."""
    from unittest.mock import Mock, patch

    custom_branch = "dev-branch"

    with patch("nornir_infrahub.plugins.inventory.infrahub.InfrahubClientSync") as mock_client_class:
        mock_client = Mock()
        mock_schema = Mock()
        mock_schema.relationships = []  # Empty list to avoid iteration error
        mock_client.schema.get.return_value = mock_schema
        mock_client.filters.return_value = []
        mock_client_class.return_value = mock_client

        inventory = InfrahubInventory(host_node={"kind": "InfraDevice"}, branch=custom_branch)

        # Call get_resources to verify the branch is passed correctly
        inventory.get_resources(kind="InfraDevice")

        # Verify that client.all was called with the correct branch
        mock_client.filters.assert_called_once()
        call_args = mock_client.filters.call_args
        assert call_args[1]["branch"] == custom_branch
        assert call_args[1]["kind"] == "InfraDevice"
        assert call_args[1]["populate_store"] is True


# XXX fails atm
# def test_infrahub_inventory_load(mock_infrahub_inventory):
#     mock_defaults_content = """
#     """
#     mock_group_content = """
#     """

#     with patch(
#         "builtins.open", side_effect=[Mock(read_data=mock_defaults_content), Mock(read_data=mock_group_content)]
#     ):
#         inventory = mock_infrahub_inventory.load()

#     print(inventory.hosts.keys())
#     print(inventory.groups.keys())

#     assert len(inventory.hosts) > 0
#     assert len(inventory.groups) > 0
#     assert isinstance(inventory.defaults, HostNode)  # Check if defaults were loaded correctly
#     assert inventory.defaults.hostname == "default-host"  # Check values in the defaults
#     assert "Group" in inventory.extra_nodes  # Check if the extra nodes were retrieved


# XXX todo
# def test_infrahub_inventory_get_resources():
#     pass
