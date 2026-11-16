<!--
Sync Impact Report
===================
Version change: 1.0.0 → 1.1.0 (Python support range widened to <3.15)
Modified principles:
  - Technology Constraints — Python range >=3.10,<3.14 → >=3.10,<3.15
Added sections:
  - Core Principles (5 principles)
  - Technology Constraints
  - Development Workflow
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md — ✅ compatible (no changes needed)
  - .specify/templates/spec-template.md — ✅ compatible (no changes needed)
  - .specify/templates/tasks-template.md — ✅ compatible (no changes needed)
  - No command files found in .specify/templates/commands/
Follow-up TODOs: None
-->

# nornir-infrahub Constitution

## Core Principles

### I. Plugin Contract Fidelity

All inventory and task plugins MUST conform to the Nornir plugin
interface contracts. The `InfrahubInventory` class MUST implement
Nornir's inventory plugin protocol. Task plugins MUST accept and
return Nornir `Result` objects. Breaking the plugin contract is a
blocking defect — no release may ship with a violated contract.

Infrahub SDK version bounds MUST be respected; any SDK upgrade that
changes query behavior or return types MUST be validated against
existing inventory and task functionality before merging.

### II. Type Safety and Data Validation

Pydantic models MUST be used for structured configuration and data
exchange. All public function signatures MUST carry type annotations.
The `ty` type checker and `pylint` MUST pass without errors on the
`nornir_infrahub` package. Suppression of type errors is permitted
only with an inline comment explaining why the suppression is
necessary (e.g., dynamic SDK types).

### III. Code Quality Gates

Every change MUST pass the full lint suite before merge:

- `ruff check` and `ruff format` for style and import ordering
- `pylint` for structural and semantic checks
- `yamllint` for YAML file hygiene
- `ty check` for type correctness

Line length limit is 120 characters (enforced by ruff). McCabe
complexity MUST NOT exceed 15. These gates are non-negotiable —
disable rules only when explicitly justified in `pyproject.toml`
with an inline comment.

### IV. Testing Discipline

Tests MUST be organized into `tests/unit/` and `tests/integration/`
directories. Unit tests MUST NOT require a running Infrahub instance
or network access. Integration tests MAY depend on external services
and MUST be clearly separated so they can be skipped in CI when
infrastructure is unavailable.

`pytest-asyncio` with `asyncio_mode = "auto"` is the async test
runner. New plugin functionality MUST include corresponding unit
tests. Coverage configuration tracks branch coverage and excludes
`TYPE_CHECKING` blocks and `NotImplementedError` raises.

### V. Simplicity and Focus

This project is a focused plugin library — not a framework, not a
CLI application, not a platform. Features MUST directly serve the
purpose of bridging Nornir and Infrahub. Scope creep MUST be
rejected: if functionality belongs in infrahub-sdk or nornir-core,
contribute it there instead.

Dependencies MUST be pinned with lower and upper bounds
(e.g., `>=1.17.0,<2`). New dependencies require justification —
prefer leveraging existing dependencies over adding new ones.
YAGNI applies: do not add abstractions or extension points for
hypothetical future use.

## Technology Constraints

- **Python**: >=3.10, <3.15. All code MUST work across this range.
- **Package manager**: uv (with `hatchling` build backend).
- **Core dependencies**: infrahub-sdk, nornir, pydantic, ruamel-yaml,
  nornir-utils, python-slugify. Bounds defined in `pyproject.toml`.
- **Dev dependencies**: pytest, ruff, pylint, ty, yamllint,
  pytest-asyncio, invoke. Managed via `dependency-groups.dev`.
- **Async**: The Infrahub SDK is async-first. Inventory loading and
  SDK interactions use `async`/`await`. Tests use `pytest-asyncio`.
- **License**: Apache-2.0. All contributions MUST be compatible.
- **Entry point**: Nornir discovers the plugin via the
  `nornir.plugins.inventory` entry point in `pyproject.toml`.

## Development Workflow

1. **Format**: Run `invoke format` (ruff format + ruff check --fix).
2. **Lint**: Run `invoke lint` (yamllint, ruff check, pylint, ty).
3. **Test**: Run `pytest` (unit tests by default via `testpaths`).
4. **Docs**: Run `invoke generate-docs` to regenerate plugin
   reference documentation from docstrings.

All four steps MUST pass before a pull request is eligible for
review. CI enforces these gates — local runs are expected before
pushing.

Commit messages MUST be descriptive of the change. Feature branches
MUST target the `stable` branch. Dependabot is configured for
dependency updates.

## Governance

This constitution is the authoritative reference for development
standards in nornir-infrahub. It supersedes informal conventions
and ad-hoc decisions.

**Amendment process**:

1. Propose the change with rationale in a pull request.
2. Update this document with the new version number.
3. All active contributors MUST be notified.
4. The Sync Impact Report (HTML comment at top) MUST be updated.

**Versioning**: MAJOR.MINOR.PATCH semantic versioning.

- MAJOR: Principle removed or fundamentally redefined.
- MINOR: New principle or section added, material expansion.
- PATCH: Clarifications, wording, typo fixes.

**Compliance**: All pull requests and code reviews MUST verify
adherence to these principles. Violations MUST be flagged and
resolved before merge.

**Version**: 1.1.0 | **Ratified**: 2026-04-10 | **Last Amended**: 2026-07-28
