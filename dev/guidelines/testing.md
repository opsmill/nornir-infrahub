# Testing Guidelines

How to write and run tests for `nornir-infrahub`. This complements the brief
"Testing" section in [`python.md`](python.md) (which lists the run commands) and goes
deeper on the conventions for each test layer. Tests use `pytest` with
`pytest-asyncio` in `asyncio_mode = "auto"`, and live under `tests/`.

## Two layers: unit and integration

The suite is split into `tests/unit/` and `tests/integration/`, and the two layers are
fundamentally different in cost and dependencies.

- **Unit tests** are the default. A bare `pytest` runs unit tests only, because
  `addopts` in `pyproject.toml` includes `-m 'not integration'`. They are fast, hit no
  network, and require no Docker — every Infrahub interaction is mocked.
- **Integration tests** are opt-in via the `integration` marker. Run them with
  `pytest -m integration`. Each test class spins up a real Infrahub stack in Docker
  (minutes per class), so they are slow and require a working Docker daemon.

Pick the layer by what you are verifying: plugin logic, validation, branching, and
error paths belong in unit tests; end-to-end behaviour against a live Infrahub API
(inventory loading, schema mappings resolving to real values, branch awareness) belongs
in integration tests.

## Unit tests: mock everything

Unit tests must not touch the network or Docker. There are two established mocking
styles, both visible in `tests/unit/`:

- **Real SDK objects, no I/O.** For logic that operates on an `InfrahubNode` and its
  schema (e.g. `resolve_node_mapping`), construct a real `InfrahubNodeSync` from a
  `NodeSchemaAPI` and a data dict, using a client pointed at a dummy address
  (`InfrahubClient(address="http://mock")`). The `client`, `*_schema`, and `*_data`
  fixtures in `tests/unit/conftest.py` provide these; no request is ever sent.
- **`MagicMock` for the client and node.** For task plugins (`test_file_object.py`),
  build a fake Nornir `task` whose `task.host.data["InfrahubNode"]` is a `MagicMock`,
  and drive the SDK client off it (`task.host.data["InfrahubNode"]._client`). Stub
  return values and side effects on the mock — `client.create.return_value`,
  `client.get.side_effect = NodeNotFoundError(...)`, `obj.upload_if_changed.return_value`
  — then assert with `assert_called_once_with(...)` / `assert_not_called()`.

To exercise `InfrahubInventory` without a server, patch the client class itself:
`patch("nornir_infrahub.plugins.inventory.infrahub.InfrahubClientSync")` and give the
mock a schema with `relationships`/`relationship_names` set (see the `_patched_inventory`
helper). This lets you assert on the config passed to the constructor and on how
`filters`/`schema.get` are called.

Assert on the **Nornir `Result`** for task plugins: check `result.failed`,
`result.changed`, and that `result.result` (or download fields like `result.binary`,
`result.text`, `result.save_to`) carries the expected substring. The `file_object` tasks
return a failed `Result` at each guard rather than raising, so test those guard paths by
inspecting the `Result`, not with `pytest.raises`. The artifact tasks
(`artifact.py`) behave differently — they do not catch errors, so they raise: `get_artifact`
raises `RuntimeError` when neither/both of `artifact`/`artifact_id` are given, and all three
artifact tasks let SDK errors propagate. Use `pytest.raises` for code that genuinely raises
(`RuntimeError`, `ValueError`, Pydantic `ValidationError`). Use `tmp_path` for
any filesystem work so tests stay hermetic.

## Integration tests: inherit the base class

Every integration test class inherits `NornirInfrahubIntegration` (in
`tests/integration/conftest.py`), which extends `TestInfrahubDocker` from
`infrahub-testcontainers`. The base class provides a class-scoped `bootstrap`
fixture (`autouse=True`) that loads the schema and creates the platforms, sites, IP
addresses, devices, a `CoreStandardGroup`, and a `test-branch` that every test in the
class relies on. The container is **per class**, so keep related assertions together to
amortise startup; mark the class (or test) with `@pytest.mark.integration`.

Connect using the `infrahub_address` fixture and the admin token from
`infrahub_testcontainers.helpers.PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]`
(imported as `TEST_TOKEN`) — **never hardcode a token**. Tests construct an
`InfrahubInventory(...).load()` and assert on the resulting `inventory.hosts` /
`inventory.groups`. If you add a new scenario that needs new data, extend the `SCHEMA`
constant and the `bootstrap` fixture rather than mutating data inside a test.

## Conventions

- `tests/**` relaxes two lint rules (`pyproject.toml`): magic numbers (`PLR2004`) and
  deferred imports (`PLC0415`) are allowed, so `unittest.mock` imports inside a test
  body are fine.
- Test functions and `_`-prefixed helpers need no docstring (pylint `no-docstring-rgx`).
- Use `parametrize` for tabular cases (see the branch-config test) and group related
  task cases into `Test*` classes as `test_file_object.py` does.
- Run a single test with
  `pytest tests/unit/test_inventory.py::test_valid_mapping` for fast feedback.
