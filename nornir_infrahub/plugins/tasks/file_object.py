"""CoreFileObject management tasks"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nornir.core.task import Result, Task

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


def _get_client(task: Task) -> InfrahubClientSync:
    # Extract the InfrahubClientSync from the Nornir task's host data.
    node = task.host.data["InfrahubNode"]
    return node._client


def _validate_file_object_kind(client: InfrahubClientSync, kind: str, branch: str | None = None) -> NodeSchemaAPI:  # type: ignore[return-type]  # SDK returns union of schema types
    # Fetch schema and verify it inherits from CoreFileObject. Raises ValueError if not.
    schema = client.schema.get(kind=kind, branch=branch)
    if "CoreFileObject" not in getattr(schema, "inherit_from", []):
        raise ValueError(f"Kind '{kind}' does not inherit from CoreFileObject")
    return schema


def upload_file_object(
    task: Task,
    kind: str,
    file_path: str,
    data: dict[str, Any] | None = None,
    node_id: str | None = None,
    hfid: list[str] | None = None,
    branch: str | None = None,
) -> Result:
    """
    Uploads a local file to an Infrahub CoreFileObject node.

    Creates the node if it does not exist, or updates it if the file content
    has changed (SHA-1 checksum comparison).  When the local file is identical
    to the one stored on the server the upload is skipped (idempotent).

    Args:
        task (Task): The Nornir task instance containing host-related data.
        kind (str): The schema kind that inherits from CoreFileObject.
        file_path (str): Local filesystem path to the file to upload.
        data (dict, optional): Additional node attributes to set on create or update.
        node_id (str, optional): UUID of an existing node to update.
        hfid (list[str], optional): HFID components identifying an existing node.
        branch (str, optional): Target Infrahub branch. Defaults to the client's default branch.

    Returns:
        Result: A Nornir Result with ``changed`` indicating whether the node was
            created or updated, ``node_id`` with the UUID, and a descriptive
            ``result`` message.

    Raises:
        ValueError: If *kind* does not inherit from CoreFileObject.

    Example:
        Upload a contract PDF to a CoreFileObject node

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
    path = Path(file_path)
    if not path.exists():
        return Result(host=task.host, failed=True, result=f"file_path '{file_path}' does not exist")

    client = _get_client(task)

    try:
        _validate_file_object_kind(client, kind, branch)
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    data = data or {}

    # Look up existing node
    existing_node = None
    try:
        if node_id:
            existing_node = client.get(kind=kind, id=node_id, branch=branch)
        elif hfid:
            existing_node = client.get(kind=kind, hfid=hfid, branch=branch)
        else:
            # Fall back to file_name filter
            file_name = path.name
            existing_node = client.get(kind=kind, branch=branch, file_name__value=file_name)
    except Exception:  # noqa: BLE001
        existing_node = None

    if existing_node:
        # Compare checksums
        local_checksum = hashlib.sha1(path.read_bytes(), usedforsecurity=False).hexdigest()
        server_checksum = existing_node.checksum.value

        if local_checksum == server_checksum:
            return Result(
                host=task.host,
                failed=False,
                changed=False,
                node_id=str(existing_node.id),
                result=f"{kind} '{path.name}' already up to date (checksum match)",
            )

        # Update: re-upload changed file
        for attr_name, attr_value in data.items():
            if attr_name in existing_node._schema.attribute_names:
                setattr(existing_node, attr_name, attr_value)

        existing_node.upload_from_path(path)
        existing_node.save()

        return Result(
            host=task.host,
            failed=False,
            changed=True,
            node_id=str(existing_node.id),
            result=f"{kind} '{path.name}' updated (checksum changed)",
        )

    # Create new node
    try:
        new_node = client.create(kind=kind, branch=branch, data=data)
        new_node.upload_from_path(path)
        new_node.save()
    except Exception as exc:  # noqa: BLE001
        return Result(host=task.host, failed=True, result=str(exc))

    return Result(
        host=task.host,
        failed=False,
        changed=True,
        node_id=str(new_node.id),
        result=f"{kind} '{path.name}' created",
    )


def download_file_object(
    task: Task,
    kind: str,
    node_id: str | None = None,
    hfid: list[str] | None = None,
    dest: str | None = None,
    branch: str | None = None,
) -> Result:
    """
    Downloads file content from an Infrahub CoreFileObject node.

    Returns the file content as base64-encoded binary data, with a UTF-8
    text representation for text MIME types.  Optionally saves the file
    to a local destination path.

    Args:
        task (Task): The Nornir task instance containing host-related data.
        kind (str): The schema kind that inherits from CoreFileObject.
        node_id (str, optional): UUID of the node to download from.
        hfid (list[str], optional): HFID components identifying the node.
        dest (str, optional): Local path to save the downloaded file. Directories get the original file name appended.
        branch (str, optional): Target Infrahub branch. Defaults to the client's default branch.

    Returns:
        Result: A Nornir Result containing ``binary`` (base64 string),
            ``text`` (UTF-8 string or None), ``file_name``, ``file_type``,
            ``file_size``, ``checksum``, ``node_id``, and ``dest``.

    Raises:
        ValueError: If *kind* does not inherit from CoreFileObject.

    Example:
        Download a file from a CoreFileObject node

        ```python
        from nornir_infrahub.plugins.tasks import download_file_object

        result = nr.run(
            task=download_file_object,
            kind="NetworkCircuitContract",
            hfid=["contract-2026"],
        )
        ```
    """
    if not node_id and not hfid:
        return Result(host=task.host, failed=True, result="One of 'node_id' or 'hfid' is required")

    if node_id and hfid:
        return Result(host=task.host, failed=True, result="'node_id' and 'hfid' are mutually exclusive")

    client = _get_client(task)

    try:
        _validate_file_object_kind(client, kind, branch)
    except ValueError as exc:
        return Result(host=task.host, failed=True, result=str(exc))

    try:
        if node_id:
            node = client.get(kind=kind, id=node_id, branch=branch)
        else:
            node = client.get(kind=kind, hfid=hfid, branch=branch)
    except Exception as exc:  # noqa: BLE001
        return Result(host=task.host, failed=True, result=f"Node not found: {exc}")

    content: bytes = node.download_file()  # type: ignore[assignment]  # dest=None always returns bytes

    # Write to dest if requested
    resolved_dest: str | None = None
    if dest is not None:
        dest_path = Path(dest)
        if dest.endswith("/") or dest_path.is_dir():
            resolved_dest = str(dest_path / node.file_name.value)
        else:
            resolved_dest = str(dest_path)
        Path(resolved_dest).parent.mkdir(parents=True, exist_ok=True)
        Path(resolved_dest).write_bytes(content)

    file_type = node.file_type.value
    is_text = file_type in TEXT_MIME_TYPES

    return Result(
        host=task.host,
        failed=False,
        binary=base64.b64encode(content).decode("ascii"),
        text=content.decode("utf-8", errors="replace") if is_text else None,
        file_name=node.file_name.value,
        file_type=file_type,
        file_size=node.file_size.value,
        checksum=node.checksum.value,
        node_id=str(node.id),
        dest=resolved_dest,
    )
