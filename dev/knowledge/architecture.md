# Architecture

`nornir-infrahub` is a [Nornir](https://github.com/nornir-automation/nornir) plugin that integrates
with [Infrahub](https://github.com/opsmill/infrahub) by OpsMill. It has two halves:

1. an **inventory plugin** that turns Infrahub nodes into Nornir hosts and groups, and
2. a set of **task plugins** for managing Infrahub artifacts (device configs, compliance reports, and
   other generated documents).

Both halves are built on top of `infrahub-sdk` (`InfrahubClientSync` / `InfrahubNodeSync`) and the
contract between them is a single piece of host data: `host.data["InfrahubNode"]`.

## The inventory plugin

`InfrahubInventory` (`nornir_infrahub/plugins/inventory/infrahub.py`) connects to the Infrahub API with
`InfrahubClientSync` and maps nodes to Nornir hosts. It is configured with:

- **`host_node`** — a dict selecting the Infrahub node kind to map to hosts, plus optional
  `include` / `exclude` / `filters` (modelled by the `HostNode` pydantic model). A `model_validator`
  always appends `member_of_groups` to `include`, because that relation must be pre-fetched to determine
  group membership.
- **`schema_mappings`** — a list of `{name, mapping}` entries describing how a Nornir host property maps
  to an attribute or relation on the node (e.g. `hostname` ← `primary_address.address`). A mapping named
  `name` customizes the Nornir host name; otherwise the node's `name` attribute is used.
- **`group_mappings`** — a list of attribute/relation paths used to derive Nornir groups
  (e.g. `site.name`).
- Optional **`defaults_file`** (`defaults.yaml`) and **`group_file`** (`group.yaml`) YAML files loaded
  with `ruamel.yaml` to seed Nornir defaults and statically-defined groups.

At construction time the inventory fetches the host node's schema, validates every mapping, and rejects
paths spanning more than one relation hop (`MAX_RELATIONSHIP_HOPS = 2`, i.e. at most one `.`). Any
relation referenced by a mapping is added to `host_node.include` so the SDK pre-fetches it.

`load()` does the work:

- Fetches nodes via `get_resources()`, which calls `client.filters(kind=..., populate_store=True, ...)`.
- For each node, resolves the host name and each `schema_mapping` through `resolve_node_mapping()`,
  walking relations (cardinality `many` is unsupported) and reading attribute values. The special-case
  `value_mapper` converts `IPHost` attributes to a bare IP string.
- Stores the originating node on the host as **`host.data["InfrahubNode"]`** — the contract the task
  plugins depend on.
- Builds groups from two sources: the node's `member_of_groups` peers of type `CoreStandardGroup`, and
  each `group_mapping` (slugified and prefixed, e.g. `site__jfk1`). Groups are created on demand and
  attached as `ParentGroups`.

### Error handling

`resolve_node_mapping()` raises `RuntimeError` when a mapping path cannot be resolved (unknown
attribute/relation, or a `many`-cardinality relation). The `name` mapping wraps that into a clearer
`RuntimeError`; per-property `schema_mapping` and `group_mapping` failures are currently swallowed and the
property/group is skipped (two `TODO`s mark these as open decisions). Construction-time validation raises
plain `ValueError` for malformed mapping paths.

## The task plugins

`nornir_infrahub/plugins/tasks/artifact.py` provides three Nornir tasks, all of which read
`task.host.data["InfrahubNode"]` and reuse its bound SDK client (`node._client`):

- **`regenerate_host_artifact(task, artifact)`** — calls `node.artifact_generate(name=artifact)` to
  regenerate one host's artifact.
- **`generate_artifacts(task, artifact, timeout=10)`** — looks up the `CoreArtifactDefinition` by name and
  calls `.generate()`, regenerating the artifact for every target in the definition. Run once per
  definition. `timeout` is retained for compatibility but ignored.
- **`get_artifact(task, artifact=None, artifact_id=None)`** — fetches the `CoreArtifact` node (by name +
  object id, or by id) and downloads its content via `client.object_store.get(...)`. JSON content types are
  parsed; everything else is returned as text. Raises `RuntimeError` if neither or both of `artifact` /
  `artifact_id` are given.

Note: all artifact operations now go through the SDK (`artifact_generate`, `CoreArtifactDefinition`,
`object_store`). Historically some used direct `httpx` calls; that was migrated to the SDK-provided
functions.

Alongside the three artifact tasks, `nornir_infrahub/plugins/tasks/file_object.py` provides
`upload_file_object` and `download_file_object` for moving file content to/from `CoreFileObject` nodes
in the object store (both checksum-driven and idempotent). Unlike the artifact tasks, these catch SDK
errors and return a failed `Result` (`Result(failed=True, ...)`) rather than letting them raise.

## Entry-point registration

The inventory plugin is registered through `pyproject.toml`:

```toml
[project.entry-points."nornir.plugins.inventory"]
InfrahubInventory = "nornir_infrahub.plugins.inventory.infrahub:InfrahubInventory"
```

This lets Nornir discover it by name (`"plugin": "InfrahubInventory"`), though it can also be registered
explicitly via `InventoryPluginRegister.register(...)`. The task plugins are plain callables imported from
`nornir_infrahub.plugins.tasks` and passed to `nr.run(task=...)`.

## Data flow

```
                     +----------------------+
                     |    Infrahub API      |
                     |  (InfrahubClientSync)|
                     +----------+-----------+
                                | filters(kind=host_node.kind, populate_store=True)
                                v
                     +----------------------+      defaults.yaml / group.yaml
                     |   InfrahubInventory  |<---- (ruamel.yaml)
                     |   .load()            |
                     +----------+-----------+
       schema_mappings -> host props        group_mappings + member_of_groups -> groups
                                |
                                v
        +-----------------------+------------------------+
        | Nornir Inventory                               |
        |   hosts[name].data["InfrahubNode"] = node      |
        |   hosts[name].groups = ParentGroups([...])     |
        +-----------------------+------------------------+
                                | nr.run(task=...)
                                v
        +-----------------------+------------------------+
        | Task plugins (artifact.py)                     |
        |   read host.data["InfrahubNode"], node._client |
        |   get_artifact / generate_artifacts /          |
        |   regenerate_host_artifact                     |
        +-----------------------+------------------------+
                                | SDK: artifact_generate / object_store
                                v
                     +----------------------+
                     |  Infrahub artifacts  |
                     +----------------------+
```

## Key dependencies

- `infrahub-sdk` (>=1.20.1,<2) — API client, node model, object store.
- `nornir` (>=3.5.0,<4) + `nornir-utils` — automation framework and result printing.
- `pydantic` (v2) — `HostNode` model and `SchemaMappingNode` validation.
- `ruamel.yaml` — defaults/group file parsing.
- `python-slugify` — group-name slugification.
