# Developing a Task Plugin

This guide walks you through adding a new Nornir task plugin to `nornir-infrahub`. Task plugins are plain functions that run against a host and act on its Infrahub node. Use the existing tasks in `nornir_infrahub/plugins/tasks/artifact.py` and `nornir_infrahub/plugins/tasks/file_object.py` as worked examples.

## 1. Write the task function

A task is a function whose first parameter is `task: Task` and which returns a `Result`. Add it to a module under `nornir_infrahub/plugins/tasks/` (group related tasks per file, as `artifact.py` does).

```python
from nornir.core.task import Result, Task


def get_node_description(task: Task) -> Result:
    """Fetch the description attribute of the host's Infrahub node."""
    node = task.host.data["InfrahubNode"]
    return Result(host=task.host, failed=False, result=node.description.value)
```

Keep the signature explicit: list any extra arguments after `task` (for example `artifact: str` in `regenerate_host_artifact`). Document the function with a docstring — the reference docs are generated from docstrings (`invoke generate-docs`).

## 2. Access the Infrahub node

Every host carries its source node at `task.host.data["InfrahubNode"]`. This is populated by the inventory plugin: in `InfrahubInventory.load()` (`nornir_infrahub/plugins/inventory/infrahub.py`), each fetched node is assigned with `host["data"] = {"InfrahubNode": host_node}`. The value is an `InfrahubNodeSync`, so you read attributes via `.value` (e.g. `node.name.value`) and traverse single-cardinality relations via `.peer`.

## 3. Call Infrahub

Reach the SDK client through the node with `node._client`. From there use the synchronous client API, as the existing tasks do:

- `node.artifact_generate(name=artifact)` — call a method on the node directly (`regenerate_host_artifact`).
- `node._client.get(kind="CoreArtifact", name__value=artifact, object__ids=[node.id])` — query a related node (`get_artifact`).
- `node._client.object_store.get(identifier=...)` — fetch stored content (`get_artifact`).

## 4. Return a Result

Always return a `Result(host=task.host, ...)`. Set the status fields to reflect what happened:

- `failed=False` on success; put a returned payload in `result=` (see `get_artifact`, which also passes a custom `content_type=` field).
- `failed=True, result=str(exc)` when an operation fails — `upload_file_object` catches SDK exceptions and returns a failed `Result` rather than letting them propagate.
- `changed=True` when the task mutated Infrahub state; `changed=False` when it was a no-op (the upload task sets this based on whether the checksum changed).

Raise `RuntimeError` only for caller mistakes such as invalid argument combinations (`get_artifact` does this when neither/both of `artifact` and `artifact_id` are given).

## 5. Export the task

Add the function to `nornir_infrahub/plugins/tasks/__init__.py` — both the import and the `__all__` tuple — so callers can `from nornir_infrahub.plugins.tasks import your_task`. Task plugins are imported directly; unlike the inventory plugin, they are not registered via `pyproject.toml` entry points.

## 6. Add a unit test

Add a test file under `tests/unit/` (for example `tests/unit/test_your_task.py`), mirroring `tests/unit/test_file_object.py`. No Infrahub or Docker is needed — build a mock task with `MagicMock`, stub the node and client, then assert on the returned `Result`:

```python
from unittest.mock import MagicMock


def _make_task():
    task = MagicMock()
    task.host.data = {"InfrahubNode": MagicMock()}
    return task


def test_get_node_description():
    task = _make_task()
    task.host.data["InfrahubNode"].description.value = "core router"

    result = get_node_description(task=task)

    assert result.failed is False
    assert result.result == "core router"
```

Run `pytest tests/unit/test_your_task.py` to verify, then `invoke format` and `invoke lint` before opening a pull request.
