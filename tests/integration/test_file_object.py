"""Integration tests for CoreFileObject upload/download tasks."""

import base64

import pytest
from infrahub_sdk import Config, InfrahubClientSync
from nornir_infrahub.plugins.tasks.file_object import (
    download_file_object,
    upload_file_object,
)

from .conftest import TEST_TOKEN, NornirInfrahubIntegration

FILE_OBJECT_SCHEMA = {
    "version": "1.0",
    "nodes": [
        {
            "name": "TestFile",
            "namespace": "Testing",
            "inherit_from": ["CoreFileObject"],
            "attributes": [
                {"name": "label", "kind": "Text", "optional": True},
            ],
        },
    ],
}


class _NodeWrapper:
    def __init__(self, client: InfrahubClientSync) -> None:
        self._client = client


class _FakeHost:
    def __init__(self, client: InfrahubClientSync) -> None:
        self.data = {"InfrahubNode": _NodeWrapper(client)}


class _FakeTask:
    """Minimal Task stand-in: file_object tasks only read ``task.host.data['InfrahubNode']._client``."""

    def __init__(self, client: InfrahubClientSync) -> None:
        self.host = _FakeHost(client)


@pytest.mark.integration
class TestFileObjectTasks(NornirInfrahubIntegration):
    @pytest.fixture(scope="class", autouse=True)
    def file_object_schema(self, infrahub_address: str, bootstrap: None) -> None:  # noqa: ARG002
        # Layer the CoreFileObject-inheriting kind onto the conftest's base bootstrap.
        client = InfrahubClientSync(
            config=Config(api_token=TEST_TOKEN),
            address=infrahub_address,
        )
        client.schema.load(schemas=[FILE_OBJECT_SCHEMA], wait_until_converged=True)

    @pytest.fixture(scope="class")
    def client(self, infrahub_address: str) -> InfrahubClientSync:
        return InfrahubClientSync(
            config=Config(api_token=TEST_TOKEN),
            address=infrahub_address,
        )

    @pytest.fixture
    def task(self, client: InfrahubClientSync) -> _FakeTask:
        return _FakeTask(client)

    def test_upload_lifecycle(self, task: _FakeTask, tmp_path) -> None:
        file_path = tmp_path / "lifecycle.txt"
        file_path.write_bytes(b"v1 content")

        # Create
        r1 = upload_file_object(task=task, kind="TestingTestFile", file_path=str(file_path))
        assert r1.failed is False, r1.result
        assert r1.changed is True
        assert "created" in r1.result
        object_id = r1.object_id

        # Idempotent skip (same content, same object)
        r2 = upload_file_object(
            task=task,
            kind="TestingTestFile",
            file_path=str(file_path),
            object_id=object_id,
        )
        assert r2.failed is False, r2.result
        assert r2.changed is False
        assert "up to date" in r2.result

        # Update with changed content
        file_path.write_bytes(b"v2 content - different")
        r3 = upload_file_object(
            task=task,
            kind="TestingTestFile",
            file_path=str(file_path),
            object_id=object_id,
        )
        assert r3.failed is False, r3.result
        assert r3.changed is True
        assert "updated" in r3.result

    def test_download_returns_content(self, task: _FakeTask, tmp_path) -> None:
        src = tmp_path / "download_src.txt"
        content = b"hello download world"
        src.write_bytes(content)

        up = upload_file_object(task=task, kind="TestingTestFile", file_path=str(src))
        assert up.failed is False, up.result

        dn = download_file_object(task=task, kind="TestingTestFile", object_id=up.object_id)
        assert dn.failed is False, dn.result
        assert dn.file_name == "download_src.txt"
        assert base64.b64decode(dn.binary) == content

    def test_download_skip_when_local_matches(self, task: _FakeTask, tmp_path) -> None:
        src = tmp_path / "skip_src.txt"
        content = b"identical bytes for skip"
        src.write_bytes(content)
        up = upload_file_object(task=task, kind="TestingTestFile", file_path=str(src))
        assert up.failed is False, up.result

        target = tmp_path / "dl" / "skip_src.txt"
        d1 = download_file_object(
            task=task,
            kind="TestingTestFile",
            object_id=up.object_id,
            save_to=str(target),
        )
        assert d1.failed is False, d1.result
        assert d1.changed is True
        assert target.read_bytes() == content

        # Second download — local already matches server checksum → no rewrite
        d2 = download_file_object(
            task=task,
            kind="TestingTestFile",
            object_id=up.object_id,
            save_to=str(target),
        )
        assert d2.failed is False, d2.result
        assert d2.changed is False

    def test_data_attr_persists_on_skip(self, task: _FakeTask, client: InfrahubClientSync, tmp_path) -> None:
        f = tmp_path / "attr.txt"
        f.write_bytes(b"unchanged content")

        # Create (no label yet)
        up = upload_file_object(task=task, kind="TestingTestFile", file_path=str(f))
        assert up.failed is False, up.result
        object_id = up.object_id

        # Re-upload identical content + a label — file is unchanged, but the label
        # should be persisted (review #2 behaviour).
        r = upload_file_object(
            task=task,
            kind="TestingTestFile",
            file_path=str(f),
            object_id=object_id,
            data={"label": "after-update"},
        )
        assert r.failed is False, r.result
        assert r.changed is True
        assert "attributes updated" in r.result

        # Verify the label was actually persisted on the server.
        obj = client.get(kind="TestingTestFile", id=object_id)
        assert obj.label.value == "after-update"

    def test_explicit_object_id_not_found_fails(self, task: _FakeTask, tmp_path) -> None:
        f = tmp_path / "miss.txt"
        f.write_bytes(b"x")
        result = upload_file_object(
            task=task,
            kind="TestingTestFile",
            file_path=str(f),
            object_id="00000000-0000-0000-0000-000000000000",
        )
        assert result.failed is True
        assert "not found" in result.result

    def test_unknown_key_in_data_fails_on_update(self, task: _FakeTask, tmp_path) -> None:
        f = tmp_path / "unknown_key.txt"
        f.write_bytes(b"data")

        first = upload_file_object(task=task, kind="TestingTestFile", file_path=str(f))
        assert first.failed is False, first.result

        result = upload_file_object(
            task=task,
            kind="TestingTestFile",
            file_path=str(f),
            object_id=first.object_id,
            data={"totally_bogus_key": "x"},
        )
        assert result.failed is True
        assert "Unknown key 'totally_bogus_key'" in result.result
