"""Base class and bootstrap fixtures for integration tests."""

import pytest
from infrahub_sdk import Config, InfrahubClientSync
from infrahub_testcontainers.helpers import PROJECT_ENV_VARIABLES, TestInfrahubDocker

TEST_TOKEN = PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]

SCHEMA = {
    "version": "1.0",
    "nodes": [
        {
            "name": "Platform",
            "namespace": "Infra",
            "default_filter": "name__value",
            "attributes": [
                {"name": "name", "kind": "Text", "unique": True},
                {"name": "nornir_platform", "kind": "Text"},
            ],
        },
        {
            "name": "Site",
            "namespace": "Infra",
            "default_filter": "name__value",
            "attributes": [
                {"name": "name", "kind": "Text", "unique": True},
            ],
        },
        {
            "name": "IPAddress",
            "namespace": "Infra",
            "default_filter": "address__value",
            "attributes": [
                {"name": "address", "kind": "IPHost"},
            ],
        },
        {
            "name": "Device",
            "namespace": "Infra",
            "default_filter": "name__value",
            "attributes": [
                {"name": "name", "kind": "Text", "unique": True},
            ],
            "relationships": [
                {"name": "platform", "peer": "InfraPlatform", "cardinality": "one", "optional": True},
                {"name": "site", "peer": "InfraSite", "cardinality": "one", "optional": True},
                {"name": "primary_address", "peer": "InfraIPAddress", "cardinality": "one", "optional": True},
            ],
        },
    ],
}


class NornirInfrahubIntegration(TestInfrahubDocker):
    @pytest.fixture(scope="class")
    def infrahub_address(self, infrahub_port: int) -> str:
        return f"http://localhost:{infrahub_port}"

    @pytest.fixture(scope="class", autouse=True)
    def bootstrap(self, infrahub_address: str) -> None:
        client = InfrahubClientSync(
            config=Config(api_token=TEST_TOKEN),
            address=infrahub_address,
        )

        # Load schema
        client.schema.load(schemas=[SCHEMA], wait_until_converged=True)

        # Create platforms
        eos = client.create(
            kind="InfraPlatform",
            data={"name": {"value": "eos"}, "nornir_platform": {"value": "arista_eos"}},
        )
        eos.save()

        junos = client.create(
            kind="InfraPlatform",
            data={"name": {"value": "junos"}, "nornir_platform": {"value": "juniper_junos"}},
        )
        junos.save()

        # Create sites
        chicago = client.create(kind="InfraSite", data={"name": {"value": "chicago"}})
        chicago.save()

        nyc = client.create(kind="InfraSite", data={"name": {"value": "nyc"}})
        nyc.save()

        # Create IP addresses
        ip1 = client.create(kind="InfraIPAddress", data={"address": {"value": "10.0.0.1/32"}})
        ip1.save()
        ip2 = client.create(kind="InfraIPAddress", data={"address": {"value": "10.0.0.2/32"}})
        ip2.save()
        ip3 = client.create(kind="InfraIPAddress", data={"address": {"value": "10.0.0.3/32"}})
        ip3.save()

        # Create devices
        router1 = client.create(
            kind="InfraDevice",
            data={
                "name": {"value": "router-1"},
                "site": {"id": chicago.id},
                "platform": {"id": eos.id},
                "primary_address": {"id": ip1.id},
            },
        )
        router1.save()

        router2 = client.create(
            kind="InfraDevice",
            data={
                "name": {"value": "router-2"},
                "site": {"id": chicago.id},
                "platform": {"id": junos.id},
                "primary_address": {"id": ip2.id},
            },
        )
        router2.save()

        switch1 = client.create(
            kind="InfraDevice",
            data={
                "name": {"value": "switch-1"},
                "site": {"id": nyc.id},
                "platform": {"id": eos.id},
                "primary_address": {"id": ip3.id},
            },
        )
        switch1.save()

        # Create CoreStandardGroup and add router-1 as member
        group = client.create(
            kind="CoreStandardGroup",
            data={"name": {"value": "core-routers"}, "label": {"value": "Core Routers"}},
        )
        group.save()

        router1.member_of_groups.fetch()
        router1.member_of_groups.add(group.id)
        router1.save()

        # Create test-branch and add router-3 to it
        client.branch.create("test-branch", wait_until_completion=True)

        ip4 = client.create(
            kind="InfraIPAddress",
            branch="test-branch",
            data={"address": {"value": "10.0.0.4/32"}},
        )
        ip4.save()

        router3 = client.create(
            kind="InfraDevice",
            branch="test-branch",
            data={
                "name": {"value": "router-3"},
                "site": {"id": nyc.id},
                "platform": {"id": eos.id},
                "primary_address": {"id": ip4.id},
            },
        )
        router3.save()
