# Git Workflow

How contributions flow into `nornir-infrahub`. This complements the "Boundaries"
section in [`AGENTS.md`](../../AGENTS.md), which is the authoritative source for what
you may and may not do.

## Branch model

- `stable` is the default and protected branch — all work targets it.
- Never push directly to `stable`. Create a feature branch and open a pull request
  against `stable`.
- `origin/HEAD` resolves to `origin/stable`. `main` and `develop` are stale refs
  (untouched for years) — ignore them.

## Pre-commit gate (local)

Run these before pushing, in order:

- `invoke format` — `ruff format .`, `ruff check . --fix`, then `rumdl fmt .` (Markdown).
- `invoke lint` — all linters, in order: yamllint, ruff, pylint, ty, and rumdl (Markdown).

All lint gates must pass. Individual linters are available if you need to isolate a
failure: `invoke lint-ruff`, `invoke lint-pylint`, `invoke lint-ty`, `invoke lint-yaml`,
`invoke lint-markdown`. Keep unit tests green too — a bare `pytest` runs the unit suite
(integration tests are excluded by default).

A `.pre-commit-config.yaml` wires the fast checks (ruff, rumdl, whitespace/EOF/YAML/TOML
hooks) into git. Install once with `uv run pre-commit install`; run on demand with
`uv run pre-commit run --all-files`.

Do not weaken or disable a lint/type gate to get CI green. If a suppression is truly
warranted, scope it narrowly with an inline `# noqa: <code>` or
`# pylint: disable=<symbol>` and justify it; disabling a rule globally in
`pyproject.toml` requires an inline justification.

## Commit messages

No enforced convention, but follow what the recent history uses:

- Conventional-commit prefixes for direct work: `fix:`, `docs(dev):`,
  `chore(agentic):`, etc.
- Merged pull requests carry the PR number as a suffix, e.g.
  `Migrate artifact tasks to SDK provided artifact functions (#29)`.

Write imperative, scoped subjects that describe the change.

## Changelog

Changes are recorded with [towncrier](https://towncrier.readthedocs.io/). `CHANGELOG.md`
is generated — never edit a released section by hand.

Add a fragment under `changelog/`, named `<issue-or-pr>.<type>.md`, or
`+<slug>.<type>.md` when there is no issue or pull request to reference:

- Available types: `security`, `removed`, `deprecated`, `added`, `changed`, `fixed`,
  and `housekeeping`.
- Write a complete sentence describing the change from the reader's perspective. The
  fragment is the changelog entry, so avoid internal shorthand.
- One change may warrant several fragments when it spans types — a fix that also adds
  a capability gets both a `fixed` and an `added` fragment.

Preview the rendered entry without consuming the fragments:

```bash
uv run towncrier build --draft --version <next-version>
```

At release time, bump `version` in `pyproject.toml`, run `uv lock` to sync
`uv.lock`, then build the entry — this deletes the fragments, so commit it in one go:

```bash
uv run towncrier build --version <next-version>
```

## Pull requests

- Target `stable`.
- CI must be green before merge. The `CI` workflow (`.github/workflows/ci.yml`) runs
  only the jobs whose files changed (via `opsmill/paths-filter`):
  - `python-lint` (Python 3.14): `ruff check`, `ruff format --check`, `ty check
    nornir_infrahub`, and `pylint nornir_infrahub *.py` — mirrors `invoke lint`.
  - `python-tests`: `pytest -v tests/` across Python 3.10, 3.11, 3.12, 3.13, 3.14.
  - `yaml-lint`: `yamllint -s .`
  - `markdown-lint`: `rumdl check .` over Markdown files.
  - `documentation` / `validate-documentation-style`: build the docs site and run Vale
    (only when docs change).

## Dependencies

- Adding, removing, or bumping a dependency in `pyproject.toml` needs justification —
  ask first (per `AGENTS.md`).
- Pin every dependency with both a lower and an upper bound, e.g.
  `infrahub-sdk>=1.20.1,<2`, `pydantic>=2.0.0,<3`.

## Ask first before you commit

Per `AGENTS.md`, these changes require sign-off before they land:

- Changing the public plugin API or the `nornir.plugins.inventory` entry point
  (`InfrahubInventory`).
- Altering inventory mapping semantics (`host_node`, `schema_mappings`,
  `group_mappings`, defaults/static-group YAML).
- Upgrading `infrahub-sdk` in a way that changes query behaviour or return types.

## Never

- Push directly to `stable`.
- Commit secrets or tokens — use the test admin-token fixture
  (`PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]`), never hardcode.
- Weaken or disable lint/type gates to pass CI.
