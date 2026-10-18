"""CoreFileObject management tasks"""

from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from infrahub_sdk.exceptions import NodeNotFoundError
from nornir.core.task import Result, Task
from nornir_infrahub.utils import get_async_client, get_client

if TYPE_CHECKING:
    from infrahub_sdk import InfrahubClient, InfrahubClientSync
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


def _check_file_object_schema(schema: Any, kind: str) -> NodeSchemaAPI:
    if "CoreFileObject" not in getattr(schema, "inherit_from", []):
        raise ValueError(f"Kind '{kind}' does not inherit from CoreFileObject")
    return schema


def _validate_file_object_kind(client: InfrahubClientSync, kind: str, branch: str | None = None) -> NodeSchemaAPI:
    return _check_file_object_schema(client.schema.get(kind=kind, branch=branch), kind)


async def _avalidate_file_object_kind(client: InfrahubClient, kind: str, branch: str | None = None) -> NodeSchemaAPI:
    return _check_file_object_schema(await client.schema.get(kind=kind, branch=branch), kind)


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


def _lookup_kwargs(
    kind: str, object_id: str | None, hfid: list[str] | None, fallback_file_name: str, branch: str | None
) -> dict[str, Any]:
    if object_id:
        return {"kind": kind, "id": object_id, "branch": branch}
    if hfid:
        return {"kind": kind, "hfid": hfid, "branch": branch}
    return {"kind": kind, "branch": branch, "file_name__value": fallback_file_name}


def _multiple_objects_error(kind: str, fallback_file_name: str) -> ValueError:
    return ValueError(
        f"Multiple {kind} objects share file_name='{fallback_file_name}'; specify object_id or hfid to disambiguate."
    )


def _lookup_existing_object(
    client: InfrahubClientSync,
    kind: str,
    object_id: str | None,
    hfid: list[str] | None,
    fallback_file_name: str,
    branch: str | None,
) -> Any:
    try:
        return client.get(**_lookup_kwargs(kind, object_id, hfid, fallback_file_name, branch))
    except NodeNotFoundError:
        if object_id is not None:
            raise
        return None
    except IndexError as exc:
        raise _multiple_objects_error(kind, fallback_file_name) from exc


async def _alookup_existing_object(
    client: InfrahubClient,
    kind: str,
    object_id: str | None,
    hfid: list[str] | None,
    fallback_file_name: str,
    branch: str | None,
) -> Any:
    try:
        return await client.get(**_lookup_kwargs(kind, object_id, hfid, fallback_file_name, branch))
    except NodeNotFoundError:
        if object_id is not None:
            raise
        return None
    except IndexError as exc:
        raise _multiple_objects_error(kind, fallback_file_name) from exc


def _apply_update_data(existing_obj: Any, kind: str, data: dict[str, Any]) -> bool:
    """Set the attributes in ``data`` on an existing object and return whether one changed.

    Raises:
        ValueError: A key of ``data`` is a relationship or not part of the schema.
    """
    attrs_changed = False
    for key, value in data.items():
        if key in existing_obj._schema.attribute_names:
            current_attr = getattr(existing_obj, key)
            if getattr(current_attr, "value", current_attr) != value:
                setattr(existing_obj, key, value)
                attrs_changed = True
        elif key in existing_obj._schema.relationship_names:
            raise ValueError(
                f"Cannot update relationship '{key}' on existing {kind} via `data`; "
                "the `data` parameter only updates attributes on existing objects. "
                "Use the infrahub-sdk directly to change relationships."
            )
        else:
            raise ValueError(f"Unknown key '{key}' in `data` for {kind}; not an attribute or relationship.")
    return attrs_changed


def _create_data(data: dict[str, Any], upload_name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    create_data = dict(data)
    if not create_data and not kwargs:
        # client.create requires at least one field or keyword. Seed file_name
        # from the source so a bare upload (no data, no kwargs) succeeds;
        # upload_if_changed() refreshes file_name from the actual content
        # before the node is saved.
        create_data["file_name"] = {"value": upload_name}
    return create_data


def _update_result(task: Task, existing_obj: Any, kind: str, upload_name: str, uploaded: bool, saved: bool) -> Result:
    if uploaded:
        message = f"{kind} '{upload_name}' updated (checksum changed)"
    elif saved:
        message = f"{kind} '{upload_name}' attributes updated (file unchanged)"
    else:
        message = f"{kind} '{upload_name}' already up to date (checksum match)"
    return Result(
        host=task.host,
        failed=False,
        changed=uploaded or saved,
        object_id=str(existing_obj.id),
        result=message,
    )


def _create_result(task: Task, new_obj: Any, kind: str, upload_name: str) -> Result:
    return Result(
        host=task.host,
        failed=False,
        changed=True,
        object_id=str(new_obj.id),
        result=f"{kind} '{upload_name}' created",
    )


def _check_download_args(object_id: str | None, hfid: list[str] | None) -> str | None:
    if not object_id and not hfid:
        return "One of 'object_id' or 'hfid' is required"
    if object_id and hfid:
        return "'object_id' and 'hfid' are mutually exclusive"
    return None


def _resolve_save_to(save_to: str | Path | None, file_name: str) -> Path | None:
    if save_to is None:
        return None
    save_to_path = Path(save_to)
    if str(save_to).endswith(("/", os.sep)) or save_to_path.is_dir():
        return save_to_path / file_name
    return save_to_path


def _is_local_file_candidate(resolved_save_to: Path | None, server_checksum: str | None) -> bool:
    return bool(
        resolved_save_to is not None and resolved_save_to.exists() and resolved_save_to.is_file() and server_checksum
    )


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _download_result(task: Task, obj: Any, content: bytes, changed: bool, resolved_save_to: Path | None) -> Result:
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
        checksum=obj.checksum.value,
        object_id=str(obj.id),
        save_to=str(resolved_save_to) if resolved_save_to is not None else None,
    )


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
        data (dict, optional): Additional object fields. On create, this is forwarded to
            ``client.create`` (attributes and relationships). On update, only attribute
            keys are applied; passing a relationship or unknown key fails the task.
        object_id (str, optional): UUID of an existing object to update.
        hfid (list[str], optional): HFID components identifying an existing object.
        branch (str, optional): Target Infrahub branch. Defaults to the client's default branch.
        **kwargs (Any, optional): Extra keyword arguments forwarded to ``client.create``
            (e.g. ``allow_upsert``, ``timeout``). Applies only on the create path;
            the update path does not call ``client.create``, so these are not used
            when updating an existing object.

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
    try:
        existing_obj = _lookup_existing_object(client, kind, object_id, hfid, upload_name, branch)
    except NodeNotFoundError as exc:
        return Result(
            host=task.host,
            failed=True,
            result=f"{kind} with id={object_id!r} not found: {exc}",
        )
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    if existing_obj:
        try:
            attrs_changed = _apply_update_data(existing_obj, kind, data)
        except ValueError as exc:
            return Result(host=task.host, failed=True, result=str(exc))

        try:
            upload_result = existing_obj.upload_if_changed(source, upload_name)
        except Exception as exc:  # noqa: BLE001
            return Result(host=task.host, failed=True, result=str(exc))

        saved = False
        if not upload_result.was_uploaded and attrs_changed:
            existing_obj.save()
            saved = True
        return _update_result(task, existing_obj, kind, upload_name, upload_result.was_uploaded, saved)

    try:
        new_obj = client.create(kind=kind, branch=branch, data=_create_data(data, upload_name, kwargs), **kwargs)
        new_obj.upload_if_changed(source, upload_name)
    except Exception as exc:  # noqa: BLE001
        return Result(host=task.host, failed=True, result=str(exc))

    return _create_result(task, new_obj, kind, upload_name)


async def aupload_file_object(
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
    Uploads a file to an Infrahub CoreFileObject object, without blocking the event loop.

    Asynchronous variant of `upload_file_object`, for an inventory loaded with
    `AInitNornir` and run with `Nornir.arun`. It takes the same arguments and returns
    the same `Result`.

    Args:
        task (Task): The Nornir task instance containing host-related data.
        kind (str): The schema kind that inherits from CoreFileObject.
        file_path (str | Path, optional): Filesystem path to the file to upload.
        content (bytes, optional): Raw file content to upload. Requires ``file_name``.
        file_name (str, optional): File name to associate with ``content``. Ignored when ``file_path`` is used.
        data (dict, optional): Additional object fields. On create, this is forwarded to
            ``client.create`` (attributes and relationships). On update, only attribute
            keys are applied; passing a relationship or unknown key fails the task.
        object_id (str, optional): UUID of an existing object to update.
        hfid (list[str], optional): HFID components identifying an existing object.
        branch (str, optional): Target Infrahub branch. Defaults to the client's default branch.
        **kwargs (Any, optional): Extra keyword arguments forwarded to ``client.create``
            on the create path only.

    Returns:
        Result: A Nornir Result with ``changed`` indicating whether the object was
            created or updated, ``object_id`` with the UUID, and a descriptive
            ``result`` message.

    Example:
        Upload a contract PDF to a CoreFileObject object from a running event loop

        ```python
        from nornir_infrahub.plugins.tasks import aupload_file_object

        result = await nr.arun(
            task=aupload_file_object,
            kind="NetworkCircuitContract",
            file_path="/path/to/contract.pdf",
        )
        ```
    """
    try:
        source, upload_name = _resolve_upload_source(file_path, content, file_name)
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    client = get_async_client(task)

    try:
        await _avalidate_file_object_kind(client, kind, branch)
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    data = data or {}
    try:
        existing_obj = await _alookup_existing_object(client, kind, object_id, hfid, upload_name, branch)
    except NodeNotFoundError as exc:
        return Result(
            host=task.host,
            failed=True,
            result=f"{kind} with id={object_id!r} not found: {exc}",
        )
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    if existing_obj:
        try:
            attrs_changed = _apply_update_data(existing_obj, kind, data)
        except ValueError as exc:
            return Result(host=task.host, failed=True, result=str(exc))

        try:
            upload_result = await existing_obj.upload_if_changed(source, upload_name)
        except Exception as exc:  # noqa: BLE001
            return Result(host=task.host, failed=True, result=str(exc))

        saved = False
        if not upload_result.was_uploaded and attrs_changed:
            await existing_obj.save()
            saved = True
        return _update_result(task, existing_obj, kind, upload_name, upload_result.was_uploaded, saved)

    try:
        new_obj = await client.create(kind=kind, branch=branch, data=_create_data(data, upload_name, kwargs), **kwargs)
        await new_obj.upload_if_changed(source, upload_name)
    except Exception as exc:  # noqa: BLE001
        return Result(host=task.host, failed=True, result=str(exc))

    return _create_result(task, new_obj, kind, upload_name)


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

    Note: The downloaded content is held in memory and embedded as base64 in the
    Nornir ``Result``. Nornir aggregates results across hosts, so downloading
    large files across many hosts can be heavy. For large payloads, prefer
    ``save_to`` and ignore the ``binary``/``text`` fields, or call the
    infrahub-sdk download API directly.

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
    args_error = _check_download_args(object_id, hfid)
    if args_error:
        return Result(host=task.host, failed=True, result=args_error)

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

    resolved_save_to = _resolve_save_to(save_to, obj.file_name.value)

    changed = False
    if _is_local_file_candidate(resolved_save_to, obj.checksum.value) and obj.matches_local_checksum(resolved_save_to):
        content: bytes = resolved_save_to.read_bytes()  # type: ignore[union-attr]  # checked above
    else:
        content = obj.download_file()  # type: ignore[assignment]  # dest=None always returns bytes
        if resolved_save_to is not None:
            _write_file(resolved_save_to, content)
            changed = True

    return _download_result(task, obj, content, changed, resolved_save_to)


async def adownload_file_object(
    task: Task,
    kind: str,
    object_id: str | None = None,
    hfid: list[str] | None = None,
    save_to: str | Path | None = None,
    branch: str | None = None,
) -> Result:
    """
    Downloads file content from an Infrahub CoreFileObject object, without blocking the event loop.

    Asynchronous variant of `download_file_object`, for an inventory loaded with
    `AInitNornir` and run with `Nornir.arun`. It takes the same arguments and returns
    the same `Result`. Local file reads and writes run in a worker thread.

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

    Example:
        Download a file from a CoreFileObject object from a running event loop

        ```python
        from nornir_infrahub.plugins.tasks import adownload_file_object

        result = await nr.arun(
            task=adownload_file_object,
            kind="NetworkCircuitContract",
            hfid=["contract-2026"],
        )
        ```
    """
    args_error = _check_download_args(object_id, hfid)
    if args_error:
        return Result(host=task.host, failed=True, result=args_error)

    client = get_async_client(task)

    try:
        await _avalidate_file_object_kind(client, kind, branch)
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    try:
        if object_id:
            obj = await client.get(kind=kind, id=object_id, branch=branch)
        else:
            obj = await client.get(kind=kind, hfid=hfid, branch=branch)
    except Exception as exc:  # noqa: BLE001
        return Result(host=task.host, failed=True, result=f"Object not found: {exc}")

    resolved_save_to = await asyncio.to_thread(_resolve_save_to, save_to, obj.file_name.value)

    changed = False
    local_candidate = await asyncio.to_thread(_is_local_file_candidate, resolved_save_to, obj.checksum.value)
    if local_candidate and await obj.matches_local_checksum(resolved_save_to):
        content: bytes = await asyncio.to_thread(resolved_save_to.read_bytes)  # type: ignore[union-attr]
    else:
        content = await obj.download_file()  # type: ignore[assignment]  # dest=None always returns bytes
        if resolved_save_to is not None:
            await asyncio.to_thread(_write_file, resolved_save_to, content)
            changed = True

    return _download_result(task, obj, content, changed, resolved_save_to)
