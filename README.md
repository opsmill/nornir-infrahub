<!-- markdownlint-disable -->
![Infrahub Logo](https://assets-global.website-files.com/657aff4a26dd8afbab24944b/657b0e0678f7fd35ce130776_Logo%20INFRAHUB.svg)
<!-- markdownlint-restore -->

# Infrahub by OpsMill

[Infrahub](https://github.com/opsmill/infrahub) by [OpsMill](https://opsmill.com) is taking a new approach to Infrastructure Management by providing a new generation of datastore to organize and control all the data that defines how an infrastructure should run.

At its heart, Infrahub is built on 3 fundamental pillars:

- **Powerful Schema**: that's easily extensible
- **Unified Version Control**: for data and files
- **Data Synchronization**: with traceability and ownership

## [Nornir](https://github.com/nornir-automation/nornir) plugin for [Infrahub](https://github.com/opsmill/infrahub)

### Installation

```bash
pip install nornir_infrahub
```

### Infrahub as the Nornir inventory

Infrahub can be used as an inventory source for Nornir.
An example of this can be found in [./examples/nornir_inventory.py](./examples/nornir_inventory.py)

### Infrahub Artifact Tasks

A set of tasks are provided to operate on Infrahub Artifacts:

- `generate_artifacts`: generates the Artifacts for a Artifact Definition
- `regenerate_artifact`: re-generates an Artifact for a Nornir Host
- `get_artifact`: retrieve an Artifact for a Nornir Host

An example of this can be found in [./examples/nornir_tasks.py](./examples/nornir_tasks.py)
