# [Nornir](https://github.com/nornir-automation/nornir) plugin for [Infrahub](https://github.com/opsmill/infrahub)

## Installation

	pip install nornir_infrahub

## Infrahub as the Nornir inventory

Infrahub can be used as an inventory source for Nonir.
An example of this can be found in [./examples/nornir_inventory.py](./examples/nornir_inventory.py)

## Infrahub Artifact Tasks

A set of tasks are provided to operate on Infrahub Artifacts.
- `generate_artifacts`: generates the Artifacts for a Artifact Definition
- `regenerate_artifact`: re-generates an Artifact for a Nornir Host
- `get_artifact`: retrieve an Artifact for a Nornir Host

An example of this can be found in [./examples/nornir_tasks.py](./examples/nornir_tasks.py)
