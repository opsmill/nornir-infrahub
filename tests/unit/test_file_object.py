"""Unit tests for CoreFileObject upload and download tasks."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from unittest.mock import MagicMock

from nornir_infrahub.plugins.tasks.file_object import (
    download_file_object,
    upload_file_object,
)


def _make_attr(value):
    """Create a mock attribute with a .value property."""
    attr = MagicMock()
    attr.value = value
    return attr


def _make_mock_object(
    object_id: str = "aaaa-bbbb-cccc-dddd",
    checksum: str = "abc123",
    file_name: str = "contract.pdf",
    file_type: str = "application/pdf",
    file_size: int = 1024,
):
    """Create a mock InfrahubNodeSync with CoreFileObject attributes."""
    obj = MagicMock()
    obj.id = object_id
    obj.checksum = _make_attr(checksum)
    obj.file_name = _make_attr(file_name)
    obj.file_type = _make_attr(file_type)
    obj.file_size = _make_attr(file_size)
    obj._schema = MagicMock()
    obj._schema.attribute_names = ["file_name", "file_type", "file_size", "checksum"]
    return obj


def _make_mock_schema(inherit_from: list[str] | None = None):
    schema = MagicMock()
    schema.inherit_from = inherit_from if inherit_from is not None else ["CoreFileObject"]
    return schema


def _make_task():
    task = MagicMock()
    task.host = MagicMock()
    task.host.data = {"InfrahubNode": MagicMock()}
    return task


def _get_client_from_task(task):
    return task.host.data["InfrahubNode"]._client


class TestUploadCreateNew:
    def test_upload_creates_new_object(self, tmp_path: Path):
        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"pdf content here")

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()
        client.get.side_effect = Exception("not found")

        new_obj = _make_mock_object()
        client.create.return_value = new_obj

        result = upload_file_object(task=task, kind="NetworkContract", file_path=str(test_file))

        assert result.failed is False
        assert result.changed is True
        assert "created" in result.result
        client.create.assert_called_once()
        new_obj.upload_from_path.assert_called_once_with(test_file)
        new_obj.save.assert_called_once()

    def test_upload_accepts_path_object(self, tmp_path: Path):
        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"pdf content")

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()
        client.get.side_effect = Exception("not found")

        new_obj = _make_mock_object()
        client.create.return_value = new_obj

        result = upload_file_object(task=task, kind="NetworkContract", file_path=test_file)

        assert result.failed is False
        assert result.changed is True
        new_obj.upload_from_path.assert_called_once_with(test_file)


class TestUploadFromBytes:
    def test_upload_creates_object_from_bytes(self):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()
        client.get.side_effect = Exception("not found")

        new_obj = _make_mock_object()
        client.create.return_value = new_obj

        payload = b"inline bytes content"
        result = upload_file_object(
            task=task,
            kind="NetworkContract",
            content=payload,
            file_name="inline.txt",
        )

        assert result.failed is False
        assert result.changed is True
        new_obj.upload_from_bytes.assert_called_once_with(content=payload, name="inline.txt")
        new_obj.save.assert_called_once()

    def test_upload_bytes_requires_file_name(self):
        task = _make_task()

        result = upload_file_object(task=task, kind="NetworkContract", content=b"data")

        assert result.failed is True
        assert "file_name" in result.result

    def test_upload_rejects_both_file_path_and_content(self, tmp_path: Path):
        test_file = tmp_path / "f.txt"
        test_file.write_bytes(b"x")

        task = _make_task()
        result = upload_file_object(
            task=task,
            kind="NetworkContract",
            file_path=str(test_file),
            content=b"x",
            file_name="f.txt",
        )

        assert result.failed is True
        assert "Exactly one" in result.result

    def test_upload_rejects_neither_file_path_nor_content(self):
        task = _make_task()
        result = upload_file_object(task=task, kind="NetworkContract")

        assert result.failed is True
        assert "Exactly one" in result.result


class TestUploadUpdateChanged:
    def test_upload_updates_when_checksum_differs(self, tmp_path: Path):
        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"updated content")

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        existing_obj = _make_mock_object(checksum="old-checksum-does-not-match")
        client.get.return_value = existing_obj

        result = upload_file_object(
            task=task,
            kind="NetworkContract",
            file_path=str(test_file),
            object_id="aaaa-bbbb-cccc-dddd",
        )

        assert result.failed is False
        assert result.changed is True
        assert "updated" in result.result
        existing_obj.upload_from_path.assert_called_once_with(test_file)
        existing_obj.save.assert_called_once()


class TestUploadSkipUnchanged:
    def test_upload_skips_when_checksums_match(self, tmp_path: Path):
        test_file = tmp_path / "contract.pdf"
        content = b"unchanged content"
        test_file.write_bytes(content)

        expected_checksum = hashlib.sha1(content, usedforsecurity=False).hexdigest()

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        existing_obj = _make_mock_object(checksum=expected_checksum)
        client.get.return_value = existing_obj

        result = upload_file_object(
            task=task,
            kind="NetworkContract",
            file_path=str(test_file),
            object_id="aaaa-bbbb-cccc-dddd",
        )

        assert result.failed is False
        assert result.changed is False
        assert "up to date" in result.result
        existing_obj.upload_from_path.assert_not_called()
        existing_obj.save.assert_not_called()


class TestUploadInvalidKind:
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
    def test_upload_fails_for_missing_file(self):
        task = _make_task()

        result = upload_file_object(task=task, kind="NetworkContract", file_path="/nonexistent/file.pdf")

        assert result.failed is True
        assert "does not exist" in result.result
        client = _get_client_from_task(task)
        client.schema.get.assert_not_called()


class TestUploadKwargsPassthrough:
    def test_upload_forwards_kwargs_to_create(self, tmp_path: Path):
        test_file = tmp_path / "c.pdf"
        test_file.write_bytes(b"content")

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()
        client.get.side_effect = Exception("not found")
        client.create.return_value = _make_mock_object()

        expected_timeout = 30
        upload_file_object(
            task=task,
            kind="NetworkContract",
            file_path=str(test_file),
            allow_upsert=True,
            timeout=expected_timeout,
        )

        _, kwargs = client.create.call_args
        assert kwargs.get("allow_upsert") is True
        assert kwargs.get("timeout") == expected_timeout


class TestDownloadTextMime:
    def test_download_text_file(self):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        content = b'{"key": "value"}'
        obj = _make_mock_object(file_type="application/json", file_name="data.json", file_size=len(content))
        obj.download_file.return_value = content
        client.get.return_value = obj

        result = download_file_object(task=task, kind="NetworkConfig", object_id="aaaa-bbbb-cccc-dddd")

        assert result.failed is False
        assert result.changed is False
        assert result.binary == base64.b64encode(content).decode("ascii")
        assert result.text == content.decode("utf-8")
        assert result.file_name == "data.json"
        assert result.file_type == "application/json"
        assert result.file_size == len(content)
        assert result.object_id == "aaaa-bbbb-cccc-dddd"


class TestDownloadBinaryMime:
    def test_download_binary_file(self):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        content = b"\x89PNG\r\n\x1a\n"
        obj = _make_mock_object(file_type="image/png", file_name="photo.png", file_size=len(content))
        obj.download_file.return_value = content
        client.get.return_value = obj

        result = download_file_object(task=task, kind="SitePhoto", object_id="aaaa-bbbb-cccc-dddd")

        assert result.failed is False
        assert result.binary == base64.b64encode(content).decode("ascii")
        assert result.text is None


class TestDownloadSaveTo:
    def test_download_saves_to_directory(self, tmp_path: Path):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        content = b"file content"
        obj = _make_mock_object(file_name="report.txt", file_type="text/plain", file_size=len(content))
        obj.download_file.return_value = content
        client.get.return_value = obj

        result = download_file_object(
            task=task,
            kind="FileReport",
            object_id="aaaa-bbbb-cccc-dddd",
            save_to=str(tmp_path) + "/",
        )

        assert result.failed is False
        assert result.changed is True
        assert result.save_to == str(tmp_path / "report.txt")
        assert Path(result.save_to).read_bytes() == content

    def test_download_saves_to_explicit_path(self, tmp_path: Path):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        content = b"file content"
        obj = _make_mock_object(file_name="report.txt", file_type="text/plain", file_size=len(content))
        obj.download_file.return_value = content
        client.get.return_value = obj

        explicit = tmp_path / "custom_name.txt"
        result = download_file_object(
            task=task,
            kind="FileReport",
            object_id="aaaa-bbbb-cccc-dddd",
            save_to=explicit,
        )

        assert result.failed is False
        assert result.changed is True
        assert result.save_to == str(explicit)
        assert explicit.read_bytes() == content

    def test_download_skips_write_when_local_matches(self, tmp_path: Path):
        content = b"identical content"
        checksum = hashlib.sha1(content, usedforsecurity=False).hexdigest()

        existing_file = tmp_path / "report.txt"
        existing_file.write_bytes(content)

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        obj = _make_mock_object(
            file_name="report.txt",
            file_type="text/plain",
            file_size=len(content),
            checksum=checksum,
        )
        client.get.return_value = obj

        result = download_file_object(
            task=task,
            kind="FileReport",
            object_id="aaaa-bbbb-cccc-dddd",
            save_to=existing_file,
        )

        assert result.failed is False
        assert result.changed is False
        assert result.save_to == str(existing_file)
        obj.download_file.assert_not_called()

    def test_download_overwrites_when_local_differs(self, tmp_path: Path):
        server_content = b"new server content"
        server_checksum = hashlib.sha1(server_content, usedforsecurity=False).hexdigest()

        existing_file = tmp_path / "report.txt"
        existing_file.write_bytes(b"old local content")

        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()

        obj = _make_mock_object(
            file_name="report.txt",
            file_type="text/plain",
            file_size=len(server_content),
            checksum=server_checksum,
        )
        obj.download_file.return_value = server_content
        client.get.return_value = obj

        result = download_file_object(
            task=task,
            kind="FileReport",
            object_id="aaaa-bbbb-cccc-dddd",
            save_to=existing_file,
        )

        assert result.failed is False
        assert result.changed is True
        assert existing_file.read_bytes() == server_content


class TestDownloadNotFound:
    def test_download_fails_for_missing_object(self):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema()
        client.get.side_effect = Exception("Object not found")

        result = download_file_object(task=task, kind="NetworkContract", object_id="nonexistent-id")

        assert result.failed is True
        assert "Object not found" in result.result


class TestDownloadMissingIdentifier:
    def test_download_fails_without_identifier(self):
        task = _make_task()

        result = download_file_object(task=task, kind="NetworkContract")

        assert result.failed is True
        assert "object_id" in result.result or "hfid" in result.result

    def test_download_fails_with_both_identifiers(self):
        task = _make_task()

        result = download_file_object(
            task=task,
            kind="NetworkContract",
            object_id="some-id",
            hfid=["some-hfid"],
        )

        assert result.failed is True
        assert "mutually exclusive" in result.result


class TestDownloadInvalidKind:
    def test_download_fails_for_non_file_object_kind(self):
        task = _make_task()
        client = _get_client_from_task(task)
        client.schema.get.return_value = _make_mock_schema(inherit_from=[])

        result = download_file_object(task=task, kind="BuiltinTag", object_id="some-id")

        assert result.failed is True
        assert "CoreFileObject" in result.result
