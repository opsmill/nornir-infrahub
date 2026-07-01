# Local Development Setup

This guide walks you through setting up a local development environment for `nornir-infrahub`, from installing dependencies to running the test suite and the documentation site.

## Prerequisites

Install the following before you begin:

- **Python 3.10–3.13** (`requires-python = ">=3.10,<3.14"`).
- **[uv](https://docs.astral.sh/uv/)** for dependency and virtual environment management.
- **Docker** (running) — required only for the integration tests, which spin up a live Infrahub stack.
- **Node.js and npm** — required only for the documentation site (`invoke docs-install` / `docs-serve` / `docs-build`).

## Install dependencies

Clone the repository, then sync the environment. `uv sync` creates a virtual environment and installs the project together with its `dev` dependency group (pytest, ruff, pylint, ty, yamllint, invoke, `infrahub-testcontainers`, and more):

```bash
uv sync
```

The example commands below run tools inside that environment. Either activate it (`source .venv/bin/activate`) or prefix each command with `uv run` (for example, `uv run invoke lint`); `uv sync` alone does not activate your shell.

## Format and lint

Format all Python files with ruff before committing:

```bash
invoke format
```

Run the full linting suite (yamllint, ruff, pylint, and the `ty` type checker):

```bash
invoke lint
```

Run a single linter when you want faster feedback:

```bash
invoke lint-ruff         # ruff only
invoke lint-pylint       # pylint only
invoke lint-ty           # ty type checking only
invoke lint-yaml         # yamllint only
```

## Run tests

Unit tests require no Docker and run quickly. The default `pytest` run excludes integration tests via the `-m 'not integration'` option configured in `pyproject.toml`:

```bash
pytest                                              # Unit tests only
pytest tests/unit/test_inventory.py                 # A specific test file
pytest tests/unit/test_inventory.py::test_function  # A single test function
```

Integration tests live in `tests/integration/` and are marked with `@pytest.mark.integration`. Each test class inherits `NornirInfrahubIntegration` (see `tests/integration/conftest.py`), which uses `infrahub-testcontainers` to start a fresh Infrahub container per class and bootstrap the schema and test data. Make sure Docker is running, then opt in explicitly:

```bash
pytest -m integration    # Requires Docker; expect ~minutes per test class
```

The integration suite authenticates with the admin token from `infrahub_testcontainers.helpers.PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]`. Use that value rather than hardcoding a token.

## Documentation site

The documentation is a Docusaurus site under `docs/`. Install its npm dependencies, then serve it locally with live reload:

```bash
invoke docs-install      # Install npm dependencies for the docs site
invoke docs-serve        # Start the dev server at http://localhost:3000
```

To produce a production build of the site, or to regenerate the plugin reference docs from docstrings:

```bash
invoke docs-build        # Build the documentation website
invoke generate-docs     # Generate plugin reference docs from docstrings
```
