<!-- markdownlint-disable -->
![Infrahub Logo](https://assets-global.website-files.com/657aff4a26dd8afbab24944b/657b0e0678f7fd35ce130776_Logo%20INFRAHUB.svg)
<!-- markdownlint-restore -->

# Nornir plugin for Infrahub

[Infrahub](https://github.com/opsmill/infrahub) by [OpsMill](https://opsmill.com) acts as a central hub to manage the data, templates and playbooks that powers your infrastructure. At its heart, Infrahub is built on 3 fundamental pillars:

- **A Flexible Schema**: A model of the infrastructure and the relation between the objects in the model, that's easily extensible.
- **Version Control**: Natively integrated into the graph database which opens up some new capabilities like branching, diffing, and merging data directly in the database.
- **Unified Storage**: By combining a graph database and git, Infrahub stores data and code needed to manage the infrastructure.

## Nornir

A [Nornir](https://github.com/nornir-automation/nornir) plugin for Infrahub. Infrahub can be used as an inventory source for Nornir.

## Installation

```console
pip install nornir-infrahub
```

## Documentation

Documentation for using Nornir is available in the [Nornir-Infrahub documentation](https://docs.infrahub.app/nornir/).

## Development

### Setup

```console
poetry install
```

### Linting and Formatting

```console
invoke lint          # Run all linters (yaml, ruff, pylint, mypy)
invoke format        # Auto-format code with ruff
```

### Documentation

```console
invoke docs-install  # Install npm dependencies for docs
invoke docs-serve    # Start dev server at http://localhost:3000
invoke docs-build    # Build production documentation
invoke generate-docs # Generate plugin reference docs from docstrings
```

### Testing

```console
pytest               # Run all tests
```
