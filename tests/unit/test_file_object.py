"""Unit tests for CoreFileObject upload and download tasks."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock

from nornir_infrahub.plugins.tasks.file_object import (
    download_file_object,
    upload_file_object,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_attr(value):
    """Create a mock attribute with a .value property."""
    attr = MagicMock()
    attr.value = value
    return attr


def _make_mock_node(
    node_id: str = "aaaa-bbbb-cccc-dddd",
    checksum: str = "abc123",
    file_name: str = "contract.pdf",
    file_type: str = "application/pdf",
    file_size: int = 1024,
):
    """Create a mock InfrahubNodeSync with CoreFileObject attributes."""
    node = MagicMock()
    node.id = node_id
    node.checksum = _make_attr(checksum)
    node.file_name = _make_attr(file_name)
    node.file_type = _make_attr(file_type)
    node.file_size = _make_attr(file_size)
    node._schema = MagicMock()
    node._schema.attribute_names = ["file_name", "file_type", "file_size", "checksum"]
    return node


def _make_mock_schema(inherit_from: list[str] | None = None):
    """Create a mock NodeSchemaAPI."""
    schema = MagicMock()
    schema.inherit_from = inherit_from if inherit_from is not None else ["CoreFileObject"]
    return schema


def _make_task():
    """Create a mock Nornir Task with an InfrahubNode in host data."""
    task = MagicMock()
    task.host = MagicMock()
    task.host.data = {"InfrahubNode": MagicMock()}
    return task


def _get_client_from_task(task):
    """Extract the mock client from a mock task."""
    return task.host.data["InfrahubNode"]._client


# ---------------------------------------------------------------------------
# US1: Upload tests
# ---------------------------------------------------------------------------


class TestUploadCreateNew:
    """T006: Upload creates a new node when no existing node is found."""

    def test_upload_creates_new_node(self, tmp_path: Path):
        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"pdf content here")

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()
        client.get.side_effect = Exception("not found")

        new_node = _make_mock_node()
        client.create.return_value = new_node

        result = upload_file_object(task=task, kind="NetworkContract", file_path=str(test_file))

        assert result.failed is False
        assert result.changed is True
        assert "created" in result.result
        client.create.assert_called_once()
        new_node.upload_from_path.assert_called_once_with(test_file)
        new_node.save.assert_called_once()


class TestUploadUpdateChanged:
    """T007: Upload updates an existing node when the checksum differs."""

    def test_upload_updates_when_checksum_differs(self, tmp_path: Path):
        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"updated content")

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        existing_node = _make_mock_node(checksum="old-checksum-does-not-match")
        client.get.return_value = existing_node

        result = upload_file_object(
            task=task,
            kind="NetworkContract",
            file_path=str(test_file),
            node_id="aaaa-bbbb-cccc-dddd",
        )

        assert result.failed is False
        assert result.changed is True
        assert "updated" in result.result
        existing_node.upload_from_path.assert_called_once_with(test_file)
        existing_node.save.assert_called_once()


class TestUploadSkipUnchanged:
    """T008: Upload skips when local checksum matches server checksum."""

    def test_upload_skips_when_checksums_match(self, tmp_path: Path):
        test_file = tmp_path / "contract.pdf"
        content = b"unchanged content"
        test_file.write_bytes(content)

        import hashlib

        expected_checksum = hashlib.sha1(content, usedforsecurity=False).hexdigest()

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        existing_node = _make_mock_node(checksum=expected_checksum)
        client.get.return_value = existing_node

        result = upload_file_object(
            task=task,
            kind="NetworkContract",
            file_path=str(test_file),
            node_id="aaaa-bbbb-cccc-dddd",
        )

        assert result.failed is False
        assert result.changed is False
        assert "up to date" in result.result
        existing_node.upload_from_path.assert_not_called()
        existing_node.save.assert_not_called()


class TestUploadInvalidKind:
    """T009: Upload fails when kind does not inherit from CoreFileObject."""

    def test_upload_fails_for_non_file_object_kind(self, tmp_path: Path):
        test_file = tmp_path / "data.txt"
        test_file.write_bytes(b"data")

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema(inherit_from=[])

        result = upload_file_object(task=task, kind="BuiltinTag", file_path=str(test_file))

        assert result.failed is True
        assert "CoreFileObject" in result.result


class TestUploadMissingFile:
    """T010: Upload fails when file_path does not exist."""

    def test_upload_fails_for_missing_file(self):
        task = _make_task()

        result = upload_file_object(task=task, kind="NetworkContract", file_path="/nonexistent/file.pdf")

        assert result.failed is True
        assert "does not exist" in result.result
        # Verify no API calls were made
        client = _get_client_from_task(task)
        client.schema.get.assert_not_called()


# ---------------------------------------------------------------------------
# US2: Download tests
# ---------------------------------------------------------------------------


class TestDownloadTextMime:
    """T013: Download returns binary + text for text MIME types."""

    def test_download_text_file(self):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        content = b'{"key": "value"}'
        node = _make_mock_node(file_type="application/json", file_name="data.json", file_size=len(content))
        node.download_file.return_value = content
        client.get.return_value = node

        result = download_file_object(task=task, kind="NetworkConfig", node_id="aaaa-bbbb-cccc-dddd")

        assert result.failed is False
        assert result.binary == base64.b64encode(content).decode("ascii")
        assert result.text == content.decode("utf-8")
        assert result.file_name == "data.json"
        assert result.file_type == "application/json"
        assert result.file_size == len(content)
        assert result.node_id == "aaaa-bbbb-cccc-dddd"


class TestDownloadBinaryMime:
    """T014: Download returns binary only (text=None) for binary MIME types."""

    def test_download_binary_file(self):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        content = b"\x89PNG\r\n\x1a\n"
        node = _make_mock_node(file_type="image/png", file_name="photo.png", file_size=len(content))
        node.download_file.return_value = content
        client.get.return_value = node

        result = download_file_object(task=task, kind="SitePhoto", node_id="aaaa-bbbb-cccc-dddd")

        assert result.failed is False
        assert result.binary == base64.b64encode(content).decode("ascii")
        assert result.text is None


class TestDownloadSaveToDest:
    """T015: Download saves file to dest path."""

    def test_download_saves_to_directory(self, tmp_path: Path):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        content = b"file content"
        node = _make_mock_node(file_name="report.txt", file_type="text/plain", file_size=len(content))
        node.download_file.return_value = content
        client.get.return_value = node

        dest_dir = str(tmp_path) + "/"
        result = download_file_object(task=task, kind="FileReport", node_id="aaaa-bbbb-cccc-dddd", dest=dest_dir)

        assert result.failed is False
        assert result.dest == str(tmp_path / "report.txt")
        assert Path(result.dest).read_bytes() == content

    def test_download_saves_to_explicit_path(self, tmp_path: Path):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        content = b"file content"
        node = _make_mock_node(file_name="report.txt", file_type="text/plain", file_size=len(content))
        node.download_file.return_value = content
        client.get.return_value = node

        dest_file = str(tmp_path / "custom_name.txt")
        result = download_file_object(task=task, kind="FileReport", node_id="aaaa-bbbb-cccc-dddd", dest=dest_file)

        assert result.failed is False
        assert result.dest == dest_file
        assert Path(dest_file).read_bytes() == content


class TestDownloadNodeNotFound:
    """T016: Download fails when node is not found."""

    def test_download_fails_for_missing_node(self):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()
        client.get.side_effect = Exception("Node not found")

        result = download_file_object(task=task, kind="NetworkContract", node_id="nonexistent-id")

        assert result.failed is True
        assert "Node not found" in result.result


class TestDownloadMissingIdentifier:
    """T017: Download fails when neither node_id nor hfid is provided."""

    def test_download_fails_without_identifier(self):
        task = _make_task()

        result = download_file_object(task=task, kind="NetworkContract")

        assert result.failed is True
        assert "node_id" in result.result or "hfid" in result.result

    def test_download_fails_with_both_identifiers(self):
        task = _make_task()

        result = download_file_object(task=task, kind="NetworkContract", node_id="some-id", hfid=["some-hfid"])

        assert result.failed is True
        assert "mutually exclusive" in result.result


class TestDownloadInvalidKind:
    """T018: Download fails when kind does not inherit from CoreFileObject."""

    def test_download_fails_for_non_file_object_kind(self):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema(inherit_from=[])

        result = download_file_object(task=task, kind="BuiltinTag", node_id="some-id")

        assert result.failed is True
        assert "CoreFileObject" in result.result
