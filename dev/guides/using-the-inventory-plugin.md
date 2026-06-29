# Using the Inventory Plugin

The `InfrahubInventory` plugin sources Nornir hosts and groups directly from Infrahub. It maps an Infrahub node kind to Nornir hosts and builds groups from node attributes, relations, and `CoreStandardGroup` membership.

## Register the inventory

The plugin is registered as a Nornir entry point in `pyproject.toml`:

```toml
[project.entry-points."nornir.plugins.inventory"]
InfrahubInventory = "nornir_infrahub.plugins.inventory.infrahub:InfrahubInventory"
```

Because it is an entry point, `InitNornir` resolves `InfrahubInventory` by name once `nornir-infrahub` is installed; no manual registration is needed in a config file. (When initializing Nornir purely in Python, call `InventoryPluginRegister.register("InfrahubInventory", InfrahubInventory)` first.)

## Configure it in `config.yaml`

```yaml
---
inventory:
  plugin: InfrahubInventory
  options:
    address: "http://localhost:8000"   # Infrahub URL (default)
    token: "06438eb2-8019-4776-878c-0941b1f1d1ec"  # Infrahub API token
    branch: "main"                     # Infrahub branch (default)

    # Which Infrahub node kind becomes a Nornir host
    host_node:
      kind: "InfraDevice"
      include:
        - "platform"
      # exclude: []
      # filters: {}

    # Map Nornir host properties to node attributes/relations.
    # A mapping named "name" customizes the Nornir host name
    # (otherwise the node's "name" attribute is used).
    schema_mappings:
      - name: "hostname"
        mapping: "primary_address.address"
      - name: "platform"
        mapping: "platform.nornir_platform"

    # Build Nornir groups from node attributes/relations.
    # Each value yields a group named "<first_part>__<slugified-value>",
    # e.g. site.name -> "site__paris".
    group_mappings:
      - "site.name"
      - "role.name"

    # Optional YAML files for static defaults and groups
    defaults_file: "defaults.yaml"     # default: defaults.yaml
    group_file: "group.yaml"           # default: group.yaml

runner:
  plugin: threaded
  options:
    num_workers: 20
```

Initialize Nornir with `nr = InitNornir(config_file="config.yaml")`.

## Mapping rules

- A `mapping` may traverse at most one relation hop (e.g. `primary_address.address`); deeper paths raise a `ValueError`.
- Relations used in `schema_mappings` / `group_mappings` are added to `host_node.include` automatically.
- `member_of_groups` is always included automatically, so any `CoreStandardGroup` a node belongs to becomes a Nornir group without extra configuration.

## Supplying address and token from the environment

The plugin reads `address` and `token` as literal options, so set them from env vars in Python before init:

```python
import os
from nornir import InitNornir

nr = InitNornir(
    inventory={
        "plugin": "InfrahubInventory",
        "options": {
            "address": os.environ["INFRAHUB_ADDRESS"],
            "token": os.environ["INFRAHUB_API_TOKEN"],
            "host_node": {"kind": "InfraDevice"},
        },
    }
)
```
