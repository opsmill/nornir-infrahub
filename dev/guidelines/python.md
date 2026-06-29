# Python Guidelines

Conventions for Python code in `nornir-infrahub`. The package targets Python
`>=3.10,<3.14` and ships a Nornir inventory plugin plus artifact task plugins.

## Tooling

Manage dependencies with `uv` — run `uv sync` to install the project and the `dev`
dependency group. All quality commands are exposed as `invoke` tasks (`tasks.py`):

- `invoke format` — runs `ruff format .` then `ruff check . --fix`.
- `invoke lint` — runs all linters in order: yamllint, ruff, pylint, ty.
- `invoke lint-ruff` — `ruff check .`
- `invoke lint-pylint` — `pylint nornir_infrahub *.py`
- `invoke lint-ty` — `ty check nornir_infrahub`
- `invoke lint-yaml` — `yamllint .`

Format and lint clean before pushing. Ruff is configured with line length 120,
double-quoted strings, space indentation, and an `isort` import order; let the
formatter own all formatting so pylint and black/ruff never disagree. Ruff's enabled
rule families include `E`, `F`, `I`, `PL` (pylint), `C90` (mccabe, max complexity 15),
`ASYNC`, `DTZ`, `Q`, and `TCH`. Prefer fixing lint at the source over suppressing it;
when a suppression is warranted, scope it narrowly (an inline `# noqa: <code>` or
`# pylint: disable=<symbol>`) rather than disabling a rule globally.

## Typing

Type-hint all public functions, parameters, and return values — the existing modules
annotate everything (see `nornir_infrahub/plugins/inventory/infrahub.py`). `ty` is the
type checker (`ty check nornir_infrahub`). A few `ty` rules are relaxed in
`pyproject.toml` for the Infrahub SDK's dynamic types (`unresolved-import`,
`invalid-argument-type`, `possibly-missing-attribute`); do not widen these without
reason.

Use Pydantic v2 (`>=2.0,<3`) for structured/validated config objects. Follow the
patterns already in the inventory plugin: `BaseModel` subclasses with typed fields and
`Field(default_factory=...)`, `@model_validator(mode="before")` for pre-processing
input, and `@dataclass` from `pydantic.dataclasses` for simple records. Guard fallible
input early and raise rather than silently proceeding.

## Code style

- Naming: `PascalCase` classes, `snake_case` functions/variables, leading-underscore
  for module-private helpers (`_get_defaults`, `_iter_mappings`).
- Docstrings: every public class and function carries a docstring with `Args:`,
  `Returns:`, `Raises:`, and an `Example:` code block — these are extracted to generate
  reference docs (`invoke generate-docs`). Private (`_`) and `test_` functions need no
  docstring.
- Logging: use module-level `logger = logging.getLogger(__name__)`; do not `print`
  from library code (`tasks.py` may print task progress).
- Error handling: raise `RuntimeError` for mapping/resolution failures and `ValueError`
  for invalid configuration (e.g. multi-hop mappings). Chain causes with
  `raise ... from exc`. Mark unresolved decisions with `# TODO:` comments.

## Sync, not async

The runtime code is **synchronous**. The inventory plugin uses `InfrahubClientSync`
and `InfrahubNodeSync`; task plugins call SDK methods synchronously. There are no
`async def` functions in the plugins — do not introduce async patterns into plugin
code. (`pytest-asyncio` exists only for the test suite, where `asyncio_mode = "auto"`.)

## YAML

Read and parse YAML with `ruamel.yaml` in safe mode (`ruamel.yaml.YAML(typ="safe")`),
as the inventory plugin does for its defaults and group files. Always open files with
`encoding="utf-8"` and tolerate empty files (`yml.load(f) or {}`).

## Testing

Tests use `pytest` and live under `tests/`. Unit tests run by default; integration
tests are marked `@pytest.mark.integration` and excluded via
`addopts = "-m 'not integration' ..."` in `pyproject.toml`.

- `pytest` — unit tests only.
- `pytest tests/unit/test_inventory.py::test_function` — a single test.
- `pytest -m integration` — integration tests (requires Docker; spins up a fresh
  Infrahub container per test class via `infrahub-testcontainers`, minutes per class).

For integration tests, get the admin token from
`infrahub_testcontainers.helpers.PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]`
— never hardcode it. Magic numbers and deferred imports are permitted under `tests/**`.
