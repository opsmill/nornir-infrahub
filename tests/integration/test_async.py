"""Integration tests for loading the inventory with AInitNornir and running the asynchronous tasks."""

import base64
from typing import Any

import pytest
from infrahub_sdk import Config, InfrahubClientSync
from infrahub_sdk.node import InfrahubNode
from nornir import AInitNornir
from nornir.core import Nornir
from nornir_infrahub.plugins.tasks import adownload_file_object, aupload_file_object

from .conftest import TEST_TOKEN, NornirInfrahubIntegration
from .test_file_object import FILE_OBJECT_SCHEMA


async def _ainit(infrahub_address: str, **options: Any) -> Nornir:
    return await AInitNornir(
        runner={"plugin": "asyncio", "options": {"num_workers": 5}},
        inventory={
            "plugin": "InfrahubInventory",
            "options": {"address": infrahub_address, "token": TEST_TOKEN, **options},
        },
        logging={"enabled": False},
    )


@pytest.mark.integration
class TestAsyncInventory(NornirInfrahubIntegration):
    @pytest.fixture(scope="class", autouse=True)
    def file_object_schema(self, infrahub_address: str, bootstrap: None) -> None:  # noqa: ARG002
        client = InfrahubClientSync(config=Config(api_token=TEST_TOKEN), address=infrahub_address)
        client.schema.load(schemas=[FILE_OBJECT_SCHEMA], wait_until_converged=True)

    async def test_mappings_and_groups(self, infrahub_address: str) -> None:
        nr = await _ainit(
            infrahub_address,
            host_node={"kind": "InfraDevice"},
            schema_mappings=[
                {"name": "hostname", "mapping": "primary_address.address"},
                {"name": "platform", "mapping": "platform.nornir_platform"},
            ],
            group_mappings=["site.name"],
        )

        hosts = nr.inventory.hosts
        assert set(hosts) == {"router-1", "router-2", "switch-1"}
        assert hosts["router-1"].hostname == "10.0.0.1"
        assert hosts["router-2"].platform == "juniper_junos"
        assert {g.name for g in hosts["router-1"].groups} == {"core-routers", "site__chicago"}
        assert {g.name for g in hosts["switch-1"].groups} == {"site__nyc"}
        assert all(isinstance(host.data["InfrahubNode"], InfrahubNode) for host in hosts.values())

    async def test_branch(self, infrahub_address: str) -> None:
        nr = await _ainit(infrahub_address, host_node={"kind": "InfraDevice"}, branch="test-branch")

        assert "router-3" in nr.inventory.hosts

    async def test_upload_and_download_file_object(self, infrahub_address: str, tmp_path) -> None:
        nr = await _ainit(infrahub_address, host_node={"kind": "InfraDevice"})
        router1 = nr.filter(name="router-1")
        source = tmp_path / "async.txt"
        source.write_bytes(b"async content")

        created = (await router1.arun(task=aupload_file_object, kind="TestingTestFile", file_path=source))["router-1"]
        assert created.failed is False, created.result
        assert created.changed is True

        unchanged = (
            await router1.arun(
                task=aupload_file_object, kind="TestingTestFile", file_path=source, object_id=created.object_id
            )
        )["router-1"]
        assert unchanged.changed is False, unchanged.result

        downloaded = (
            await router1.arun(
                task=adownload_file_object,
                kind="TestingTestFile",
                object_id=created.object_id,
                save_to=f"{tmp_path}/out/",
            )
        )["router-1"]
        assert downloaded.failed is False, downloaded.result
        assert base64.b64decode(downloaded.binary) == b"async content"
        assert (tmp_path / "out" / "async.txt").read_bytes() == b"async content"
