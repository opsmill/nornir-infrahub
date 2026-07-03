# Infrahub SDK Integration

This is the transport-layer reference: how `nornir-infrahub` actually talks to Infrahub.
For the overall two-halves map and dependency list see `dev/knowledge/architecture.md`; for
the inventory config models and mapping-resolution rules see
`dev/knowledge/inventory-data-model.md`. Here we cover only the SDK client, how it is
authenticated, how nodes are queried, and the `InfrahubNode` contract that carries the client
from the inventory into the tasks.

Everything goes through `infrahub-sdk` — there is no raw `httpx`/`requests` usage anywhere in
the package (see "Transport paths" below). The pin is `infrahub-sdk>=1.20.1,<2`
(`pyproject.toml:18`).

## Client construction and auth

The one client is built by the inventory plugin in `InfrahubInventory.__init__`
(`nornir_infrahub/plugins/inventory/infrahub.py:198`):

```python
self.client = InfrahubClientSync(config=Config(api_token=token, default_branch=branch), address=self.address)
```

It is the **synchronous** SDK client (`InfrahubClientSync`, imported alongside `Config` at
`infrahub.py:9`) — Nornir tasks run synchronously per host, so the async client is not used.
Auth is an API token: the `token` option (`infrahub.py:183`, `Optional[str]`, default `None`)
is passed as `Config(api_token=...)`. The server URL comes from the `address` option
(`infrahub.py:182`, default `http://localhost:8000`). The SDK also honours its own environment
variables for these values when the options are omitted — that fallback lives in the SDK's
`Config`, not in this plugin, which only forwards what it is given.

## Branch handling

Branch selection is a first-class option. `branch` (`infrahub.py:184`, default `"main"`) is
stored as `self.branch` and set as the client's `default_branch` in `Config`
(`infrahub.py:198`). Every inventory query then passes it explicitly:
`client.filters(kind=..., branch=self.branch, ...)` (`infrahub.py:319`). The file-object tasks
also accept a per-call `branch` argument that defaults to the client's default branch
(`file_object.py:95`, `file_object.py:256`), so a task can target a different branch than the
one the inventory was loaded from. The artifact tasks in `artifact.py` do not expose a branch
argument and operate on the client's default branch.

## Querying nodes (GraphQL via the SDK)

The plugin never writes GraphQL by hand — the SDK builds and sends the queries. Two SDK calls
do the work:

- **Schema fetch.** At construction time, `self.client.schema.get(kind=self.host_node.kind)`
  (`infrahub.py:206`) retrieves the host kind's schema so mappings can be validated against
  real relationship names before any data is fetched (the validation rules themselves are in
  `inventory-data-model.md`).
- **Node fetch.** `get_resources()` (`infrahub.py:314-320`) calls
  `client.filters(kind=..., branch=self.branch, populate_store=True, **kwargs, **filters)`.
  `kind` is the configured `host_node.kind`; `include`/`exclude`/`filters` from the `HostNode`
  model are spread straight through (`load()` calls `get_resources(**dict(self.host_node))`,
  `infrahub.py:261`). `populate_store=True` caches the fetched nodes in the SDK client's store
  so later relation lookups don't re-query.

`include` matters for the relations a mapping needs: any relation referenced by a
`schema_mapping`/`group_mapping` is added to `host_node.include` at construction
(`infrahub.py:225`), and the `HostNode` model always forces `member_of_groups` into `include`
(`infrahub.py:106-116`) so group membership can be read from the pre-fetched
`host_node.member_of_groups.peers` (`infrahub.py:293`) without an extra round trip.

## Node objects and the `host.data["InfrahubNode"]` contract

`client.filters()` returns `InfrahubNodeSync` objects (imported at `infrahub.py:10`). For each
one, `load()` stores the node on its Nornir host: `host["data"] = {"InfrahubNode": host_node}`
(`infrahub.py:288`). This single key is the contract that ties the inventory to the tasks
(also documented in `AGENTS.md`): every task plugin reaches back through it.

Crucially, the stored node carries its **bound SDK client**. Tasks reuse it rather than
building a new one:

- The shared helper `get_client(task)` returns `task.host.data["InfrahubNode"]._client`
  (`nornir_infrahub/utils.py:12-14`), used by the file-object tasks (`file_object.py:152`,
  `file_object.py:312`).
- The artifact tasks reach `node._client` directly (`artifact.py:107`, `artifact.py:167`).

So there is exactly one authenticated client per Nornir run — created by the inventory,
threaded into every host, and reused by every task. Tasks inherit the inventory's address,
token, and default branch for free.

## Transport paths — all SDK

`AGENTS.md` still notes that "artifact tasks use direct HTTP calls with `httpx` rather than the
SDK for some operations." That note is **stale**: a `grep` for `httpx`/`requests`/`urllib`
across `nornir_infrahub/` returns nothing. The direct-HTTP path was removed when artifact tasks
were migrated to SDK-provided functions (commit `576b83c`, "Migrate artifact tasks to SDK
provided artifact functions"). What the code does today, all through the SDK:

- **`regenerate_host_artifact`** — `node.artifact_generate(name=artifact)` (`artifact.py:56`).
- **`generate_artifacts`** — `node._client.get(kind="CoreArtifactDefinition", ...)` then
  `.generate()` (`artifact.py:107-108`).
- **`get_artifact`** — fetches the `CoreArtifact` node with `client.get(...)`
  (`artifact.py:170` / `172`) and pulls its stored bytes via
  `client.object_store.get(identifier=artifact_node.storage_id.value)` (`artifact.py:174`).
- **File objects** — upload uses `client.create(...)` plus the SDK's
  `upload_if_changed(source, upload_name)` (`file_object.py:236-237`, `197`); download uses the
  SDK's `obj.download_file()` and `obj.matches_local_checksum(...)` (`file_object.py:344-348`).
  The object-store content transfer (streaming file bytes, checksum comparison) is handled
  entirely inside these SDK methods.

Inference (not stated in code): the object-store operations above are exactly the kind of
binary/streaming transfers a hand-rolled `httpx` call would have covered before the SDK grew
first-class helpers for them. The migration commit is consistent with that reading, but the
current code shows only SDK usage.

## Error handling patterns

Two distinct styles, by module:

- **Inventory** raises. `resolve_node_mapping` raises `RuntimeError` on an unresolvable path or
  a `many`-cardinality relation (`infrahub.py:39`, `infrahub.py:49`); construction-time mapping
  validation raises `ValueError` (`infrahub.py:213`, `infrahub.py:219`). Per-property mapping
  failures during `load()` are swallowed with a `continue` (two open `TODO`s,
  `infrahub.py:285`, `infrahub.py:303`).
- **Artifact tasks** let SDK exceptions propagate; the only explicit guard is a `RuntimeError`
  when neither or both of `artifact`/`artifact_id` are given (`artifact.py:161-164`).
- **File-object tasks** catch and convert. Bad arguments, a kind that doesn't inherit
  `CoreFileObject`, `NodeNotFoundError`, and SDK exceptions are returned as
  `Result(failed=True, result=...)` instead of raising (`file_object.py:147-169`,
  `file_object.py:198-199`, `file_object.py:238-239`, `file_object.py:324-325`), so a single
  host's failure does not abort the Nornir run.

## See also

- `dev/knowledge/architecture.md` — the overall two-halves map and dependency list.
- `dev/knowledge/inventory-data-model.md` — config models and mapping-resolution algorithm.
