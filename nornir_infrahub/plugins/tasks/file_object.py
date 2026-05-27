"""CoreFileObject management tasks"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nornir.core.task import Result, Task
from nornir_infrahub.utils import get_client

if TYPE_CHECKING:
    from infrahub_sdk import InfrahubClientSync
    from infrahub_sdk.schema import NodeSchemaAPI

TEXT_MIME_TYPES: frozenset[str] = frozenset(
    {
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
        "application/yaml",
        "application/x-yaml",
        "application/hcl",
        "application/graphql",
        "application/xml",
    }
)


def _validate_file_object_kind(client: InfrahubClientSync, kind: str, branch: str | None = None) -> NodeSchemaAPI:  # type: ignore[return-type]  # SDK returns union of schema types
    schema = client.schema.get(kind=kind, branch=branch)
    if "CoreFileObject" not in getattr(schema, "inherit_from", []):
        raise ValueError(f"Kind '{kind}' does not inherit from CoreFileObject")
    return schema


def _sha1(data: bytes) -> str:
    return hashlib.sha1(data, usedforsecurity=False).hexdigest()


def _resolve_upload_source(
    file_path: str | Path | None,
    content: bytes | None,
    file_name: str | None,
) -> tuple[bytes | Path, str]:
    # Returns (source, upload_name); raises ValueError on bad args.
    # source is a Path (streamed by the SDK) or raw bytes.
    if (file_path is None) == (content is None):
        raise ValueError("Exactly one of 'file_path' or 'content' must be provided")

    if file_path is not None:
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"file_path '{file_path}' does not exist")
        return path, path.name

    if not file_name:
        raise ValueError("'file_name' is required when using 'content'")
    return content, file_name  # type: ignore[return-value]


def _lookup_existing_object(
    client: InfrahubClientSync,
    kind: str,
    object_id: str | None,
    hfid: list[str] | None,
    fallback_file_name: str,
    branch: str | None,
) -> Any:
    try:
        if object_id:
            return client.get(kind=kind, id=object_id, branch=branch)
        if hfid:
            return client.get(kind=kind, hfid=hfid, branch=branch)
        return client.get(kind=kind, branch=branch, file_name__value=fallback_file_name)
    except Exception:  # noqa: BLE001
        return None


def upload_file_object(
    task: Task,
    kind: str,
    file_path: str | Path | None = None,
    content: bytes | None = None,
    file_name: str | None = None,
    data: dict[str, Any] | None = None,
    object_id: str | None = None,
    hfid: list[str] | None = None,
    branch: str | None = None,
    **kwargs: Any,
) -> Result:
    """
    Uploads a file to an Infrahub CoreFileObject object.

    Creates the object if it does not exist, or updates it if the file content
    has changed (SHA-1 checksum comparison).  When the local content is identical
    to the one stored on the server the upload is skipped (idempotent).

    Provide either ``file_path`` (to upload a file from disk) or ``content`` with
    ``file_name`` (to upload raw bytes).

    Args:
        task (Task): The Nornir task instance containing host-related data.
        kind (str): The schema kind that inherits from CoreFileObject.
        file_path (str | Path, optional): Filesystem path to the file to upload.
        content (bytes, optional): Raw file content to upload. Requires ``file_name``.
        file_name (str, optional): File name to associate with ``content``. Ignored when ``file_path`` is used.
        data (dict, optional): Additional object attributes to set on create or update.
        object_id (str, optional): UUID of an existing object to update.
        hfid (list[str], optional): HFID components identifying an existing object.
        branch (str, optional): Target Infrahub branch. Defaults to the client's default branch.
        **kwargs: Extra keyword arguments forwarded to ``client.create`` (e.g. ``allow_upsert``, ``timeout``).

    Returns:
        Result: A Nornir Result with ``changed`` indicating whether the object was
            created or updated, ``object_id`` with the UUID, and a descriptive
            ``result`` message.

    Raises:
        ValueError: If *kind* does not inherit from CoreFileObject or arguments are inconsistent.

    Example:
        Upload a contract PDF to a CoreFileObject object

        ```python
        from nornir_infrahub.plugins.tasks import upload_file_object

        result = nr.run(
            task=upload_file_object,
            kind="NetworkCircuitContract",
            file_path="/path/to/contract.pdf",
            data={"contract_start": "2026-01-01"},
        )
        ```
    """
    try:
        source, upload_name = _resolve_upload_source(file_path, content, file_name)
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    client = get_client(task)

    try:
        _validate_file_object_kind(client, kind, branch)
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    data = data or {}
    existing_obj = _lookup_existing_object(client, kind, object_id, hfid, upload_name, branch)

    if existing_obj:
        for attr_name, attr_value in data.items():
            if attr_name in existing_obj._schema.attribute_names:
                setattr(existing_obj, attr_name, attr_value)

        try:
            upload_result = existing_obj.upload_if_changed(source, upload_name)
        except Exception as exc:  # noqa: BLE001
            return Result(host=task.host, failed=True, result=str(exc))

        if not upload_result.was_uploaded:
            return Result(
                host=task.host,
                failed=False,
                changed=False,
                object_id=str(existing_obj.id),
                result=f"{kind} '{upload_name}' already up to date (checksum match)",
            )

        return Result(
            host=task.host,
            failed=False,
            changed=True,
            object_id=str(existing_obj.id),
            result=f"{kind} '{upload_name}' updated (checksum changed)",
        )

    try:
        new_obj = client.create(kind=kind, branch=branch, data=data, **kwargs)
        new_obj.upload_if_changed(source, upload_name)
    except Exception as exc:  # noqa: BLE001
        return Result(host=task.host, failed=True, result=str(exc))

    return Result(
        host=task.host,
        failed=False,
        changed=True,
        object_id=str(new_obj.id),
        result=f"{kind} '{upload_name}' created",
    )


def download_file_object(
    task: Task,
    kind: str,
    object_id: str | None = None,
    hfid: list[str] | None = None,
    save_to: str | Path | None = None,
    branch: str | None = None,
) -> Result:
    """
    Downloads file content from an Infrahub CoreFileObject object.

    Returns the file content as base64-encoded binary data, with a UTF-8
    text representation for text MIME types.  Optionally saves the file
    to a local path.

    When ``save_to`` points to an existing file whose SHA-1 matches the
    server-side checksum, the download is skipped and ``changed`` is ``False``
    (idempotent, similar to ``nornir_utils.plugins.tasks.files.write_file``).

    Args:
        task (Task): The Nornir task instance containing host-related data.
        kind (str): The schema kind that inherits from CoreFileObject.
        object_id (str, optional): UUID of the object to download from.
        hfid (list[str], optional): HFID components identifying the object.
        save_to (str | Path, optional): Local path where the downloaded file should be written.
            A directory receives the original file name; an explicit path is used as-is.
        branch (str, optional): Target Infrahub branch. Defaults to the client's default branch.

    Returns:
        Result: A Nornir Result containing ``binary`` (base64 string),
            ``text`` (UTF-8 string or None), ``file_name``, ``file_type``,
            ``file_size``, ``checksum``, ``object_id``, ``save_to``, and
            ``changed`` (True only when a local file was created or overwritten).

    Raises:
        ValueError: If *kind* does not inherit from CoreFileObject.

    Example:
        Download a file from a CoreFileObject object

        ```python
        from nornir_infrahub.plugins.tasks import download_file_object

        result = nr.run(
            task=download_file_object,
            kind="NetworkCircuitContract",
            hfid=["contract-2026"],
        )
        ```
    """
    if not object_id and not hfid:
        return Result(host=task.host, failed=True, result="One of 'object_id' or 'hfid' is required")

    if object_id and hfid:
        return Result(host=task.host, failed=True, result="'object_id' and 'hfid' are mutually exclusive")

    client = get_client(task)

    try:
        _validate_file_object_kind(client, kind, branch)
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    try:
        if object_id:
            obj = client.get(kind=kind, id=object_id, branch=branch)
        else:
            obj = client.get(kind=kind, hfid=hfid, branch=branch)
    except Exception as exc:  # noqa: BLE001
        return Result(host=task.host, failed=True, result=f"Object not found: {exc}")

    server_checksum = obj.checksum.value

    resolved_save_to: Path | None = None
    if save_to is not None:
        save_to_path = Path(save_to)
        if str(save_to).endswith("/") or save_to_path.is_dir():
            resolved_save_to = save_to_path / obj.file_name.value
        else:
            resolved_save_to = save_to_path

    changed = False
    if resolved_save_to is not None and resolved_save_to.exists() and resolved_save_to.is_file():
        local_checksum = _sha1(resolved_save_to.read_bytes())
        if local_checksum == server_checksum:
            content: bytes = resolved_save_to.read_bytes()
        else:
            content = obj.download_file()  # type: ignore[assignment]  # dest=None always returns bytes
            resolved_save_to.parent.mkdir(parents=True, exist_ok=True)
            resolved_save_to.write_bytes(content)
            changed = True
    else:
        content = obj.download_file()  # type: ignore[assignment]  # dest=None always returns bytes
        if resolved_save_to is not None:
            resolved_save_to.parent.mkdir(parents=True, exist_ok=True)
            resolved_save_to.write_bytes(content)
            changed = True

    file_type = obj.file_type.value
    is_text = file_type in TEXT_MIME_TYPES

    return Result(
        host=task.host,
        failed=False,
        changed=changed,
        binary=base64.b64encode(content).decode("ascii"),
        text=content.decode("utf-8", errors="replace") if is_text else None,
        file_name=obj.file_name.value,
        file_type=file_type,
        file_size=obj.file_size.value,
        checksum=server_checksum,
        object_id=str(obj.id),
        save_to=str(resolved_save_to) if resolved_save_to is not None else None,
    )
