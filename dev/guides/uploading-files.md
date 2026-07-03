# Uploading and Downloading Files

This guide shows how to use the file-object task plugins shipped in `nornir-infrahub` to move file content between your machine and Infrahub's object store. For writing your own task, see [Developing a Task Plugin](developing-a-task-plugin.md); for the artifact tasks, see [Managing Artifacts](managing-artifacts.md). This guide covers calling the existing tasks defined in `nornir_infrahub/plugins/tasks/file_object.py`.

These tasks operate on Infrahub nodes whose kind inherits from `CoreFileObject` (for example a `NetworkCircuitContract` that stores a PDF). The `kind` you pass is validated up front: if it does not inherit from `CoreFileObject`, the task fails.

## Prerequisites

Like the artifact tasks, both file-object tasks reach the Infrahub client through `task.host.data["InfrahubNode"]`. That entry is populated by `InfrahubInventory` when the inventory loads, so your Nornir instance must use the Infrahub inventory plugin (see [Using the Inventory Plugin](using-the-inventory-plugin.md)). Running these tasks against hosts from any other inventory will raise a `KeyError`.

Import the tasks from the package's task module:

```python
from nornir_infrahub.plugins.tasks import (
    upload_file_object,
    download_file_object,
)
```

## Upload a file (`upload_file_object`)

```python
upload_file_object(
    task,
    kind,
    file_path=None,
    content=None,
    file_name=None,
    data=None,
    object_id=None,
    hfid=None,
    branch=None,
    **kwargs,
)
```

Upload either a file from disk (`file_path`) **or** raw bytes (`content` plus a `file_name`) — pass exactly one of the two, or the task fails. The task locates the target object (by `object_id`, by `hfid`, or by matching `file_name`), creating it when it does not exist. Extra fields go in `data`; on create, `data` and any `**kwargs` (such as `allow_upsert`) are forwarded to `client.create`, while on update only attribute keys are applied.

```python
run_once = nr.filter(name="jfk1-edge1")
result = run_once.run(
    task=upload_file_object,
    kind="NetworkCircuitContract",
    file_path="/path/to/contract.pdf",
    data={"contract_start": "2026-01-01"},
)
```

The upload is idempotent and checksum-driven. The local content is compared against the server-side SHA-1: if it differs the file is uploaded and `changed=True`; if it matches the upload is skipped and `changed=False`. When the file is unchanged but `data` attributes differ, the attributes are saved and `changed=True`.

## Download a file (`download_file_object`)

```python
download_file_object(
    task,
    kind,
    object_id=None,
    hfid=None,
    save_to=None,
    branch=None,
)
```

Identify the object by `object_id` **or** `hfid` (exactly one — neither or both fails the task). The content comes back base64-encoded in `result.binary`, plus a UTF-8 `result.text` for known text MIME types (`None` for binary). Pass `save_to` to also write the file locally; a directory receives the object's original file name, while an explicit path is used as-is.

```python
eos_devices = nr.filter(platform="eos")
result = eos_devices.run(
    task=download_file_object,
    kind="NetworkCircuitContract",
    hfid=["contract-2026"],
    save_to="/tmp/contracts/",
)
```

Downloads are also checksum-driven: when `save_to` points at an existing file whose SHA-1 matches the server, the write is skipped and `changed=False`; `changed` is only `True` when a local file is created or overwritten. Because the content is held in memory and embedded in the `Result`, prefer `save_to` for large payloads spread across many hosts.

## Error behavior

Unlike the artifact tasks — which let SDK errors propagate so a failing run raises — the file-object tasks **catch** SDK and validation errors and return a failed `Result` instead. On any problem (a `CoreFileObject` lookup miss, an invalid `kind`, inconsistent arguments) the task returns `Result(failed=True)` with a descriptive `result` message rather than raising.

```python
for host_name, multi_result in result.items():
    host_result = multi_result[0]
    if host_result.failed:
        print(f"{host_name}: {host_result.result}")
        continue
    print(host_name, host_result.object_id, "changed" if host_result.changed else "up to date")
```

For example, if the inventory's `InfrahubNode` lookup raises a `NodeNotFoundError` for an explicit `object_id`, the run does not raise — `result.failed` is `True` and `result.result` explains the miss.
