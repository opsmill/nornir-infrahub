# Inventory Data Model

This is an implementation-level reference for the data model and mapping-resolution
algorithm inside `nornir_infrahub/plugins/inventory/infrahub.py`. It assumes you already
know *what* the inventory plugin is for (see `dev/knowledge/architecture.md`) and *how*
to configure it (see `dev/guides/using-the-inventory-plugin.md`). Here we go through the
internal models, the resolution functions, and the exact rules they enforce.

## The configuration models

Two small models capture the user-supplied configuration.

`SchemaMappingNode` (lines 93-96) is a pydantic `@dataclass` with two string fields,
`name` and `mapping`. Each entry of the `schema_mappings` option becomes one of these.
`name` is the Nornir host property to set; `mapping` is a dotted path into the Infrahub
node. The list is built in `__init__` via
`[SchemaMappingNode(**mapping) for mapping in schema_mappings]` (line 201).

`HostNode` (lines 100-116) is a pydantic `BaseModel` describing the node selection:

- `kind: str` — the Infrahub node kind that becomes a Nornir host.
- `include: List[str]` — relations to pre-fetch (defaults to empty).
- `exclude: List[str]` — relations to skip (defaults to empty).
- `filters: Dict[str, Any]` — query filters passed to the SDK (defaults to empty).

A `@model_validator(mode="before")` named `validate_include` (lines 106-116) always
appends `"member_of_groups"` to `include` (or creates `include = ["member_of_groups"]`
when the key is absent). This relation **must** be pre-fetched, because group membership
is later read from `host_node.member_of_groups.peers` (line 293) without an extra query.

`group_mappings` is *not* modelled — it is stored as the raw list of dotted-path strings
on `self.group_mappings` (line 204).

## Construction-time validation

`__init__` (lines 179-225) fetches the host node's schema with
`self.client.schema.get(kind=self.host_node.kind)` (line 206) and collects its
relationship names into `host_rel_names` (line 207). It then walks every mapping via the
`_iter_mappings()` generator (lines 227-231), which yields `("schema_mapping", sm.mapping)`
for each `SchemaMappingNode` and `("group_mapping", gm)` for each group path. The source
label is used only to produce clearer error messages.

For each `mapping` it splits on `.` and enforces the relationship-hop limit using
`MAX_RELATIONSHIP_HOPS = 2` (line 26):

- `len(parts) > MAX_RELATIONSHIP_HOPS` (i.e. more than one `.`) raises `ValueError`:
  "spans more than one relation hop; only single-hop mappings (e.g.
  'primary_address.address') are supported" (lines 212-216).
- `len(parts) == MAX_RELATIONSHIP_HOPS` (exactly one `.`) requires `parts[0]` to be a real
  relationship on the host kind; otherwise `ValueError`: "references '<parts[0]>', which is
  not a relationship on <kind>" (lines 217-222). Valid first hops are accumulated into
  `mapping_relations`.

Finally `self.host_node.include` is replaced with
`sorted(set(self.host_node.include) | mapping_relations)` (line 225), so every relation a
mapping needs is pre-fetched by the SDK. The single-`.` rule means a mapping is either a
bare attribute (`hostname`) or one relation hop plus a terminal attribute
(`primary_address.address`); deeper traversal is rejected before any data is fetched.

## Mapping resolution: `resolve_node_mapping`

`resolve_node_mapping(node, attrs)` (lines 34-49) is the core algorithm. It receives an
`InfrahubNodeSync` and the already-split path (`mapping.split(".")`), then iterates the
parts, reassigning `node` as it hops:

1. If `attr in node._schema.relationship_names`, treat it as a relation. Read
   `getattr(node, attr)`; if `relation.schema.cardinality == "many"` raise
   `RuntimeError("Relations with many cardinality are not supported!")` (lines 38-39).
   Otherwise advance `node = relation.peer` and continue to the next part.
2. If `attr in node._schema.attribute_names`, it is a terminal attribute. Read
   `getattr(node, attr)`, then run it through `value_mapper` (lines 43-46): the only
   special case maps the `IPHost` kind through `ip_interface_to_ip_string` (lines 30-31,
   which returns `str(ip_interface.ip)` — the bare IP without prefix length); any other
   kind falls back to the identity `lambda value: value`. Return `mapper(node_attr.value)`.
3. Otherwise raise `RuntimeError("Unable to resolve mapping")` (line 49).

Because attribute resolution `return`s, an attribute is always the last segment; relation
resolution falls through the loop to the next part. This is exactly why the hop limit caps
paths at one relation plus one attribute.

## `load()`: building hosts and groups

`load()` (lines 233-312) assembles the `Inventory`:

1. Parse `defaults_file` and `group_file` with `ruamel.yaml` (typ `"safe"`). Missing files
   yield `{}`. `defaults_dict` is turned into a `Defaults` via `_get_defaults` (lines
   66-75); each static group in `groups_dict` becomes a `Group` via `_get_inventory_element`
   (lines 78-90), and their parent `groups` lists are rewired into `ParentGroups`
   (lines 256-257). Both helpers pull the standard Nornir fields (`hostname`, `port`,
   `username`, `password`, `platform`, `data`, `connection_options`) from the dict;
   `_get_inventory_element` also carries `groups` as a temporary list.
2. Fetch nodes via `self.get_resources(**dict(self.host_node))` (line 261). `get_resources`
   (lines 314-320) pops `filters` out of the kwargs and calls
   `client.filters(kind=..., branch=self.branch, populate_store=True, **kwargs, **filters)`.
   Spreading `dict(self.host_node)` passes `include`/`exclude`/`filters` straight through.
3. Resolve the host name (lines 263-277). If a `schema_mapping` is named `"name"`, the name
   comes from `resolve_node_mapping(host_node, name_mapping.mapping.split("."))`, wrapped on
   failure into a clearer `RuntimeError`. Otherwise it uses `host_node.name.value`, and if
   the node has no `name` attribute the node is skipped (`continue`).
4. For every `schema_mapping`, set `host[mapping.name] = resolve_node_mapping(...)`
   (lines 279-286). A `RuntimeError` here is swallowed (`continue`, with a `TODO`), so an
   unresolved property is simply omitted.
5. Set `host["data"] = {"InfrahubNode": host_node}` (line 288) — the contract every task
   plugin reads — then create the `Host` via `_get_inventory_element` (line 289).

## Group derivation

Groups come from two sources (lines 291-310). First, `member_of_groups.peers` is filtered
to peers whose `typename == "CoreStandardGroup"`, taking each `peer.name.value` verbatim
(lines 291-295). Second, each `group_mapping` is resolved and formatted as
`f"{attrs[0]}__{slugify(resolve_node_mapping(host_node, attrs))}"` (line 301): the prefix is
the *first* path segment (not the leaf), and the resolved value is slugified — so
`site.name` resolving to "Paris HQ" yields `site__paris-hq`. Resolution failures are again
swallowed with a `TODO`. Any group name not already present is created on demand
(lines 306-308), and the host's `groups` is set to `ParentGroups([groups[g] ...])`
(line 310). The fully built `Inventory(hosts, groups, defaults)` is returned (line 312).
