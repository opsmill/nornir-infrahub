"""Unit tests for loading the inventory with AInitNornir and for the asynchronous tasks."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from infrahub_sdk import InfrahubClient, InfrahubClientSync
from infrahub_sdk.exceptions import NodeNotFoundError
from infrahub_sdk.node import InfrahubNode, InfrahubNodeSync
from infrahub_sdk.schema import NodeSchemaAPI
from nornir import AInitNornir, InitNornir
from nornir_infrahub.plugins.inventory.infrahub import InfrahubInventory
from nornir_infrahub.plugins.tasks import (
    adownload_file_object,
    agenerate_artifacts,
    aget_artifact,
    aregenerate_host_artifact,
    aupload_file_object,
    get_artifact,
)

if TYPE_CHECKING:
    from pathlib import Path

    from nornir.core.task import Task

INVENTORY_MODULE = "nornir_infrahub.plugins.inventory.infrahub"


@pytest.fixture
def host_schema() -> NodeSchemaAPI:
    return NodeSchemaAPI(
        name="Device",
        namespace="Infra",
        attributes=[
            {"name": "name", "kind": "String"},
            {"name": "description", "kind": "String", "optional": True},
        ],
        relationships=[
            {"name": "member_of_groups", "peer": "CoreGroup", "optional": True, "cardinality": "many", "kind": "Group"}
        ],
    )


def _node_data(name: str) -> dict[str, Any]:
    return {
        "id": f"id-{name}",
        "name": {"value": name},
        "description": {"value": f"{name}.example.net"},
        "member_of_groups": {"edges": []},
    }


def _inventory_options(tmp_path: Path) -> dict[str, Any]:
    return {
        "address": "http://mock",
        "branch": "test-branch",
        "host_node": {"kind": "InfraDevice"},
        "schema_mappings": [{"name": "hostname", "mapping": "description"}],
        "defaults_file": str(tmp_path / "defaults.yaml"),
        "group_file": str(tmp_path / "groups.yaml"),
    }


def _sync_client(schema: NodeSchemaAPI, names: list[str]) -> Mock:
    client = Mock()
    client.schema.get.return_value = schema
    client.filters.return_value = [
        InfrahubNodeSync(client=InfrahubClientSync(address="http://mock"), schema=schema, data=_node_data(name))
        for name in names
    ]
    return client


def _async_client(schema: NodeSchemaAPI, names: list[str]) -> Mock:
    client = Mock()
    client.schema.get = AsyncMock(return_value=schema)
    client.filters = AsyncMock(
        return_value=[
            InfrahubNode(client=InfrahubClient(address="http://mock"), schema=schema, data=_node_data(name))
            for name in names
        ]
    )
    return client


# Inventory plugin


def test_inventory_declares_sync_and_asyncio_capabilities(tmp_path: Path):
    inventory = InfrahubInventory(**_inventory_options(tmp_path))
    assert inventory.get_capabilities() == frozenset({"sync", "asyncio"})


def test_inventory_constructor_does_not_fetch_the_schema(tmp_path: Path):
    with (
        patch(f"{INVENTORY_MODULE}.InfrahubClientSync") as sync_class,
        patch(f"{INVENTORY_MODULE}.InfrahubClient") as async_class,
    ):
        InfrahubInventory(**_inventory_options(tmp_path))

    sync_class.return_value.schema.get.assert_not_called()
    async_class.return_value.schema.get.assert_not_called()


def test_inventory_clients_share_the_branch_and_token(tmp_path: Path):
    inventory = InfrahubInventory(token="test-token", **_inventory_options(tmp_path))

    assert inventory.async_client.config.default_branch == "test-branch"
    assert inventory.async_client.config.api_token == "test-token"
    assert inventory.client.config is inventory.async_client.config


async def test_aload_builds_the_same_hosts_as_load(tmp_path: Path, host_schema: NodeSchemaAPI):
    names = ["edge1", "edge2"]
    with (
        patch(f"{INVENTORY_MODULE}.InfrahubClientSync", return_value=_sync_client(host_schema, names)),
        patch(f"{INVENTORY_MODULE}.InfrahubClient", return_value=_async_client(host_schema, names)),
    ):
        inventory = InfrahubInventory(**_inventory_options(tmp_path))
    sync_inventory = inventory.load()
    async_inventory = await inventory.aload()

    assert list(async_inventory.hosts) == list(sync_inventory.hosts) == names
    for name in names:
        assert async_inventory.hosts[name].hostname == sync_inventory.hosts[name].hostname == f"{name}.example.net"
        assert isinstance(sync_inventory.hosts[name].data["InfrahubNode"], InfrahubNodeSync)
        assert isinstance(async_inventory.hosts[name].data["InfrahubNode"], InfrahubNode)


async def test_aload_reads_defaults_and_groups_files(tmp_path: Path, host_schema: NodeSchemaAPI):
    (tmp_path / "defaults.yaml").write_text("username: admin\n", encoding="utf-8")
    (tmp_path / "groups.yaml").write_text("core:\n  platform: eos\n", encoding="utf-8")
    with patch(f"{INVENTORY_MODULE}.InfrahubClient", return_value=_async_client(host_schema, ["edge1"])):
        inventory = InfrahubInventory(**_inventory_options(tmp_path))
    result = await inventory.aload()

    assert result.defaults.username == "admin"
    assert result.groups["core"].platform == "eos"


async def test_aget_resources_passes_branch_filters_and_store(tmp_path: Path, host_schema: NodeSchemaAPI):
    client = _async_client(host_schema, [])
    with patch(f"{INVENTORY_MODULE}.InfrahubClient", return_value=client):
        inventory = InfrahubInventory(**_inventory_options(tmp_path))
    await inventory.aget_resources(kind="InfraDevice", include=["platform"], filters={"role__value": "edge"})

    client.filters.assert_awaited_once_with(
        kind="InfraDevice", branch="test-branch", populate_store=True, include=["platform"], role__value="edge"
    )


# Nornir entry points


async def test_ainitnornir_loads_with_aload_and_runs_async_tasks(tmp_path: Path, host_schema: NodeSchemaAPI):
    with patch(f"{INVENTORY_MODULE}.InfrahubClient", return_value=_async_client(host_schema, ["edge1"])):
        nr = await AInitNornir(
            runner={"plugin": "asyncio"},
            inventory={"plugin": "InfrahubInventory", "options": _inventory_options(tmp_path)},
            logging={"enabled": False},
        )

    async def node_type(task: Task) -> str:
        return type(task.host.data["InfrahubNode"]).__name__

    result = await nr.arun(task=node_type)
    assert result["edge1"].result == "InfrahubNode"


def test_initnornir_loads_with_load(tmp_path: Path, host_schema: NodeSchemaAPI):
    with patch(f"{INVENTORY_MODULE}.InfrahubClientSync", return_value=_sync_client(host_schema, ["edge1"])):
        nr = InitNornir(
            inventory={"plugin": "InfrahubInventory", "options": _inventory_options(tmp_path)},
            logging={"enabled": False},
        )

    assert isinstance(nr.inventory.hosts["edge1"].data["InfrahubNode"], InfrahubNodeSync)


# Artifact tasks


def _async_task(node: Any) -> MagicMock:
    task = MagicMock()
    task.host.name = "edge1"
    task.host.data = {"InfrahubNode": node}
    return task


def _async_node() -> MagicMock:
    node = MagicMock()
    node.id = "node-id"
    node.artifact_generate = AsyncMock()
    node._client.get = AsyncMock()
    node._client.create = AsyncMock()
    node._client.schema.get = AsyncMock()
    node._client.object_store.get = AsyncMock()
    return node


async def test_aregenerate_host_artifact_awaits_the_sdk():
    node = _async_node()
    result = await aregenerate_host_artifact(_async_task(node), artifact="startup-config")

    assert result.failed is False
    node.artifact_generate.assert_awaited_once_with(name="startup-config")


async def test_agenerate_artifacts_generates_the_definition():
    node = _async_node()
    definition = MagicMock(generate=AsyncMock())
    node._client.get.return_value = definition

    result = await agenerate_artifacts(_async_task(node), artifact="startup-config")

    assert result.failed is False
    node._client.get.assert_awaited_once_with(kind="CoreArtifactDefinition", artifact_name__value="startup-config")
    definition.generate.assert_awaited_once_with()


@pytest.mark.parametrize(
    ("content_type", "content", "expected"),
    [
        ("application/json", '{"hostname": "edge1"}', {"hostname": "edge1"}),
        ("text/plain", "hostname edge1", "hostname edge1"),
    ],
)
async def test_aget_artifact_reads_the_object_store(content_type: str, content: str, expected: Any):
    node = _async_node()
    node._client.get.return_value = MagicMock(
        storage_id=MagicMock(value="storage-id"), content_type=MagicMock(value=content_type)
    )
    node._client.object_store.get.return_value = content

    result = await aget_artifact(_async_task(node), artifact="startup-config")

    assert result.result == expected
    assert result.content_type == content_type
    node._client.get.assert_awaited_once_with(
        kind="CoreArtifact", name__value="startup-config", object__ids=["node-id"]
    )
    node._client.object_store.get.assert_awaited_once_with(identifier="storage-id")


async def test_aget_artifact_requires_exactly_one_identifier():
    with pytest.raises(RuntimeError, match="aget_artifact"):
        await aget_artifact(_async_task(_async_node()), artifact="a", artifact_id="b")


async def test_async_task_rejects_a_host_loaded_with_initnornir(host_schema: NodeSchemaAPI):
    node = InfrahubNodeSync(client=InfrahubClientSync(address="http://mock"), schema=host_schema, data=_node_data("r"))
    with pytest.raises(TypeError, match="loaded with InitNornir"):
        await aregenerate_host_artifact(_async_task(node), artifact="startup-config")


def test_sync_task_rejects_a_host_loaded_with_ainitnornir(host_schema: NodeSchemaAPI):
    node = InfrahubNode(client=InfrahubClient(address="http://mock"), schema=host_schema, data=_node_data("r"))
    with pytest.raises(TypeError, match="loaded with AInitNornir"):
        get_artifact(_async_task(node), artifact="startup-config")


# File object tasks


def _file_object(checksum: str = "abc123", file_type: str = "text/plain") -> MagicMock:
    obj = MagicMock()
    obj.id = "file-id"
    obj.checksum.value = checksum
    obj.file_name.value = "contract.txt"
    obj.file_type.value = file_type
    obj.file_size.value = 7
    obj._schema.attribute_names = ["file_name", "description"]
    obj._schema.relationship_names = ["owner"]
    obj.upload_if_changed = AsyncMock(return_value=MagicMock(was_uploaded=True))
    obj.save = AsyncMock()
    obj.download_file = AsyncMock(return_value=b"content")
    obj.matches_local_checksum = AsyncMock(return_value=True)
    return obj


def _file_object_node() -> MagicMock:
    node = _async_node()
    node._client.schema.get.return_value = MagicMock(inherit_from=["CoreFileObject"])
    return node


async def test_aupload_file_object_creates_a_new_object(tmp_path: Path):
    source = tmp_path / "contract.txt"
    source.write_bytes(b"content")
    node = _file_object_node()
    node._client.get.side_effect = NodeNotFoundError(identifier={})
    new_obj = _file_object()
    node._client.create.return_value = new_obj

    result = await aupload_file_object(_async_task(node), kind="NetworkContract", file_path=source)

    assert (result.failed, result.changed, result.object_id) == (False, True, "file-id")
    node._client.create.assert_awaited_once_with(
        kind="NetworkContract", branch=None, data={"file_name": {"value": "contract.txt"}}
    )
    new_obj.upload_if_changed.assert_awaited_once_with(source, "contract.txt")


async def test_aupload_file_object_saves_changed_attributes_when_file_is_unchanged():
    node = _file_object_node()
    existing = _file_object()
    existing.upload_if_changed.return_value = MagicMock(was_uploaded=False)
    node._client.get.return_value = existing

    result = await aupload_file_object(
        _async_task(node),
        kind="NetworkContract",
        content=b"content",
        file_name="contract.txt",
        data={"description": "x"},
    )

    assert result.changed is True
    assert "attributes updated" in result.result
    existing.save.assert_awaited_once_with()


async def test_aupload_file_object_rejects_relationship_updates():
    node = _file_object_node()
    node._client.get.return_value = _file_object()

    result = await aupload_file_object(
        _async_task(node), kind="NetworkContract", content=b"x", file_name="contract.txt", data={"owner": "y"}
    )

    assert result.failed is True
    assert "Cannot update relationship 'owner'" in result.result


async def test_aupload_file_object_rejects_a_kind_without_core_file_object():
    node = _file_object_node()
    node._client.schema.get.return_value = MagicMock(inherit_from=[])

    result = await aupload_file_object(_async_task(node), kind="InfraDevice", content=b"x", file_name="a.txt")

    assert result.failed is True
    assert "does not inherit from CoreFileObject" in result.result


async def test_adownload_file_object_writes_the_file(tmp_path: Path):
    node = _file_object_node()
    node._client.get.return_value = _file_object()

    result = await adownload_file_object(
        _async_task(node), kind="NetworkContract", object_id="file-id", save_to=tmp_path
    )

    assert result.changed is True
    assert result.text == "content"
    assert base64.b64decode(result.binary) == b"content"
    assert (tmp_path / "contract.txt").read_bytes() == b"content"


async def test_adownload_file_object_skips_a_local_file_with_matching_checksum(tmp_path: Path):
    (tmp_path / "contract.txt").write_bytes(b"local")
    node = _file_object_node()
    obj = _file_object()
    node._client.get.return_value = obj

    result = await adownload_file_object(_async_task(node), kind="NetworkContract", hfid=["c"], save_to=tmp_path)

    assert result.changed is False
    assert result.text == "local"
    obj.download_file.assert_not_awaited()


async def test_adownload_file_object_requires_one_identifier():
    result = await adownload_file_object(_async_task(_file_object_node()), kind="NetworkContract")

    assert result.failed is True
    assert "required" in result.result
