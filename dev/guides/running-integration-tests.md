# Running Integration Tests

Integration tests exercise the plugin against a live Infrahub stack. Each test class spins up a fresh Infrahub container via `infrahub-testcontainers`, so Docker must be running. They live in `tests/integration/` and are marked with `@pytest.mark.integration`.

## Prerequisites

- **Docker** must be running. `infrahub-testcontainers` starts a real Infrahub server per test class.
- Dependencies synced with `uv sync` — the `dev` group pins `infrahub-testcontainers>=1.9.3` (see `pyproject.toml`).
- Expect **~minutes per test class**: each class boots its own container and re-bootstraps schema and data.

## 1. Run the integration suite

Integration tests are excluded from the default `pytest` run. The `addopts` in `pyproject.toml` sets `-m 'not integration'`, and the `integration` marker is registered as `markers = ["integration: marks tests as integration tests (requires Docker)"]`. Opt in explicitly with the marker:

```bash
pytest -m integration
```

## 2. Run a single class or file

Narrow the run to one file or one class to shorten the container boot cost while iterating:

```bash
pytest -m integration tests/integration/test_inventory.py
pytest -m integration tests/integration/test_inventory.py::TestInventoryBasic
```

## What the container gives you

The base class `NornirInfrahubIntegration(TestInfrahubDocker)` in `tests/integration/conftest.py` provides:

- `infrahub_port` — from `TestInfrahubDocker`; the mapped port of the running container.
- `infrahub_address` — a class-scoped fixture returning `http://localhost:{infrahub_port}`.
- `bootstrap` — a class-scoped, `autouse=True` fixture that loads the `SCHEMA` (`InfraPlatform`, `InfraSite`, `InfraIPAddress`, `InfraDevice`) with `client.schema.load(..., wait_until_converged=True)`, then creates platforms, sites, IP addresses, three devices, a `CoreStandardGroup` (`core-routers`), and a `test-branch` containing a fourth device (`router-3`).

The admin token comes from the fixture, never hardcoded:

```python
from infrahub_testcontainers.helpers import PROJECT_ENV_VARIABLES, TestInfrahubDocker

TEST_TOKEN = PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]
```

The client is built as `InfrahubClientSync(config=Config(api_token=TEST_TOKEN), address=infrahub_address)`.

## Write a new integration test

1. Import the base class and token from the conftest, and subclass `NornirInfrahubIntegration`:

   ```python
   import pytest
   from .conftest import TEST_TOKEN, NornirInfrahubIntegration


   @pytest.mark.integration
   class TestMyFeature(NornirInfrahubIntegration):
       def test_something(self, infrahub_address: str) -> None:
           ...
   ```

2. Mark the class (or each test) `@pytest.mark.integration` so it is skipped by the default run and selected by `pytest -m integration`.
3. Take the container address from the `infrahub_address` fixture and authenticate with `TEST_TOKEN` — never hardcode a token. `test_inventory.py` builds the inventory with `InfrahubInventory(host_node={"kind": "InfraDevice"}, address=infrahub_address, token=TEST_TOKEN).load()`.
4. Rely on the `autouse` `bootstrap` fixture for the base data. To layer extra schema on top, add your own class-scoped fixture that depends on `bootstrap` and calls `client.schema.load(...)` again — `test_file_object.py` does this with its `file_object_schema` fixture to add a `CoreFileObject`-inheriting kind.

## Debugging

- **Docker not running** → testcontainers cannot start Infrahub and the tests error out. Start Docker and re-run.
- **Container lifecycle** — the container is class-scoped and managed by `TestInfrahubDocker` from `infrahub-testcontainers`. Because `bootstrap` is `scope="class"`, a fresh, freshly seeded stack is created per class; state does not leak between classes but is shared across tests within a class.
- **Apple Silicon** — `addopts` includes `-p no:pytest-infrahub-performance-test` to disable a testcontainers plugin that crashes on arm64 via `psutil.cpu_freq()`. Keep this flag when overriding `addopts`.

## CI note

CI does **not** run the integration tests. The `python-tests` job in `.github/workflows/ci.yml` runs `uv run pytest -v tests/`, which inherits the `-m 'not integration'` default from `pyproject.toml`. Run `pytest -m integration` locally (with Docker) to exercise them.
