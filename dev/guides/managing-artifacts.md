# Managing Artifacts

This guide shows how to use the artifact task plugins shipped in `nornir-infrahub` inside a Nornir run. For writing your own task, see [Developing a Task Plugin](developing-a-task-plugin.md); this guide covers calling the existing tasks defined in `nornir_infrahub/plugins/tasks/artifact.py`.

## Prerequisites

Every artifact task reads the host's source node from `task.host.data["InfrahubNode"]`. That entry is populated by `InfrahubInventory` when the inventory loads, so your Nornir instance must use the Infrahub inventory plugin (see [Using the Inventory Plugin](using-the-inventory-plugin.md)). Running these tasks against hosts from any other inventory will raise a `KeyError`.

Import the tasks from the package's task module:

```python
from nornir_infrahub.plugins.tasks import (
    get_artifact,
    generate_artifacts,
    regenerate_host_artifact,
)
```

## Generate artifacts for a definition (`generate_artifacts`)

`generate_artifacts(task, artifact, timeout=10)` looks up the `CoreArtifactDefinition` whose `artifact_name` matches `artifact` and triggers its generation. The definition generates artifacts for **all** of its targets, so you only need to run this once per definition — filter down to a single host. The `timeout` argument is retained for compatibility and is ignored by the SDK path.

```python
run_once = nr.filter(name="jfk1-edge1")
result = run_once.run(task=generate_artifacts, artifact="startup-config")
```

## Regenerate one host's artifact (`regenerate_host_artifact`)

`regenerate_host_artifact(task, artifact)` calls `artifact_generate(name=artifact)` directly on each host's own node, regenerating just that host's named artifact.

```python
eos_devices = nr.filter(platform="eos")
result = eos_devices.run(task=regenerate_host_artifact, artifact="startup-config")
```

## Fetch artifact content (`get_artifact`)

`get_artifact(task, artifact=None, artifact_id=None)` retrieves a `CoreArtifact` and downloads its stored content from the Infrahub object store. Provide **exactly one** of `artifact` (the artifact name, matched against the host's node) or `artifact_id` — passing neither or both raises a `RuntimeError`. If the artifact's content type is `application/json` the result is parsed into a Python object; otherwise it is returned as text.

```python
from nornir_utils.plugins.functions import print_result

eos_devices = nr.filter(platform="eos")
result = eos_devices.run(task=get_artifact, artifact="startup-config")
print_result(result)
```

## Reading the returned `Result`

`run()` returns an `AggregatedResult` keyed by host name; index it to get each host's `Result`:

```python
for host_name, multi_result in result.items():
    host_result = multi_result[0]
    if host_result.failed:
        print(f"{host_name}: failed")
        continue
    # get_artifact populates .result (and a custom .content_type attribute)
    print(host_name, host_result.content_type, host_result.result)
```

- `failed` — `False` on success. The artifact tasks let SDK errors propagate rather than catching them, so a failing run typically raises (and Nornir marks the result failed) instead of returning `failed=True`.
- `changed` — not set by these tasks; they leave it at its default.
- `result` — only `get_artifact` sets a payload (the JSON or text content); `generate_artifacts` and `regenerate_host_artifact` return `Result(host=task.host, failed=False)` with no `result`.
