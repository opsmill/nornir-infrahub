# AGENTS.md

This file provides guidance to AI coding assistants working with this repository.

## Repository Overview

`nornir-infrahub` is a Nornir plugin that integrates with Infrahub by OpsMill. It provides an inventory plugin that fetches network device data from Infrahub and maps it to Nornir hosts and groups, along with task plugins for managing Infrahub artifacts (device configurations, compliance reports, etc.).

## Project Structure

- `nornir_infrahub/plugins/inventory/infrahub.py` — `InfrahubInventory` class: connects to Infrahub API, maps nodes to Nornir hosts via configurable schema mappings
- `nornir_infrahub/plugins/tasks/artifact.py` — `get_artifact()`, `generate_artifacts()`, `regenerate_host_artifact()`
- `tests/unit/` — unit tests (no Docker required)
- `tests/integration/` — integration tests against a live Infrahub stack via `infrahub-testcontainers` (requires Docker)
- `docs/` — Docusaurus documentation site

## Quick Reference

### Install dependencies

```bash
uv sync
```

### Format code

```bash
invoke format
```

### Run linting

```bash
invoke lint              # Run all linters (yaml, ruff, pylint, ty, rumdl)
invoke lint-ruff         # Run ruff linter only
invoke lint-pylint       # Run pylint only
invoke lint-ty           # Run ty type checking only
invoke lint-yaml         # Run yamllint only
invoke lint-markdown     # Run rumdl (Markdown) only
```

### Run tests

```bash
pytest                                              # Unit tests only (integration tests excluded by default)
pytest tests/unit/test_inventory.py                 # Run specific test file
pytest tests/unit/test_inventory.py::test_function  # Run single test function
pytest -m integration                               # Integration tests (requires Docker, ~minutes per class)
```

### Documentation

```bash
invoke docs-install      # Install npm dependencies for docs
invoke docs-serve        # Start dev server at http://localhost:3000
invoke docs-build        # Build documentation website
invoke generate-docs     # Generate plugin reference docs from docstrings
```

## Architecture Notes

### Key dependencies

- `infrahub-sdk`: Primary SDK for Infrahub API interactions
- `nornir`: Core automation framework
- `pydantic`: Data validation and settings management
- `ruamel.yaml`: YAML processing for configuration files

### Configuration pattern

The inventory plugin expects:

- `host_node`: Dict defining which Infrahub node kind maps to Nornir hosts
- `schema_mappings`: List mapping Nornir host properties to Infrahub node attributes/relations
- `group_mappings`: List of Infrahub attributes to create Nornir groups from
- Optional YAML files for defaults and static groups

### Plugin registration

```toml
[project.entry-points."nornir.plugins.inventory"]
InfrahubInventory = "nornir_infrahub.plugins.inventory.infrahub:InfrahubInventory"
```

### Important notes

- All task plugins expect the host to have an `InfrahubNode` in `host.data["InfrahubNode"]`
- The inventory plugin automatically includes `member_of_groups` relation for group membership
- All Infrahub access goes through `infrahub-sdk` — there is no raw `httpx`/`requests` usage in the package (artifact tasks were migrated to SDK-provided functions; see `dev/knowledge/infrahub-sdk-integration.md`)
- Error handling uses `RuntimeError` for mapping resolution failures (TODO items exist for improvement)

### Integration tests

- Located in `tests/integration/`, marked with `@pytest.mark.integration`
- Excluded from the default `pytest` run via `addopts = "-m 'not integration' ..."` in `pyproject.toml`
- Each test class inherits `NornirInfrahubIntegration` (in `tests/integration/conftest.py`), which spins up a fresh Infrahub container per class via `infrahub-testcontainers` and bootstraps schema + test data
- The admin token comes from `infrahub_testcontainers.helpers.PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]` — do not hardcode

## Boundaries

### Always Do

- Run `invoke format` then `invoke lint` (yamllint, ruff, pylint, ty, rumdl) before committing — all gates must pass (Constitution §III).
- Keep unit tests passing and add unit tests for new plugin functionality (`pytest` runs `tests/unit/` by default; unit tests must not require Docker or network).
- Keep changes minimal and focused on bridging Nornir and Infrahub — reject scope creep and unused abstractions (Constitution §V, YAGNI).
- Preserve the task-plugin contract: tasks read the host's `InfrahubNode` from `host.data["InfrahubNode"]`.
- Carry type annotations on all public function signatures and use Pydantic models for structured config/data (Constitution §II).
- Pin any dependency with both lower and upper bounds (e.g. `>=1.17.0,<2`).

### Ask First

- Changing the public plugin API or the `nornir.plugins.inventory` entry point (`InfrahubInventory`).
- Adding, removing, or bumping dependencies in `pyproject.toml` — new deps require justification.
- Changes that alter inventory mapping semantics (`host_node`, `schema_mappings`, `group_mappings`, defaults/static-group YAML).
- Upgrading `infrahub-sdk` in a way that changes query behavior or return types — validate against inventory and task functionality first (Constitution §I).

### Never Do

- Push directly to the protected `stable` branch (feature branches target `stable` via PR).
- Commit secrets or tokens — use the test admin-token fixture (`PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]`), never hardcode.
- Weaken or disable lint/type gates to pass CI — disable a rule only with an inline justification in `pyproject.toml` (Constitution §III).
- Break the Nornir plugin contract (inventory protocol or `Result`-returning tasks) — this is a blocking defect (Constitution §I).

## Documentation Guidelines

### Writing guidelines

**Applies to:** All MDX files (`**/*.mdx`)

**Structure:** Follows [Diataxis framework](https://diataxis.fr/)

- **Tutorials** (learning-oriented)
- **How-to guides** (task-oriented)
- **Explanation** (understanding-oriented)
- **Reference** (information-oriented)

**Tone and style:**

- Professional but approachable: avoid jargon unless well defined
- Concise and direct: prefer short, active sentences
- Informative over promotional: focus on explaining how and why
- Consistent and structured: follow a predictable pattern across sections

**For guides:**

- Address the user directly using imperative verbs: "Configure...", "Create...", "Deploy..."
- Focus on practical tasks and problems, not the tools themselves
- Maintain focus on the specific goal without digressing into explanations

**For topics:**

- Use a more discursive, reflective tone that invites understanding
- Include context, background, and rationale behind design decisions
- Make connections between concepts and to users' existing knowledge

**Terminology:**

- Always define new terms when first used
- Be consistent with Infrahub's data model and UI naming conventions

**Reference files:**

- Vale styles: `.vale/styles/Infrahub/`
- Spelling exceptions: `.vale/styles/spelling-exceptions.txt`

### Checklist

- Always run rumdl (`invoke lint-markdown`, or `rumdl check .` / `rumdl fmt .`) when `.md` or `.mdx` files change
- Always run vale when `.md` or `.mdx` files change
