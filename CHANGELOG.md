# Changelog

All notable changes to this project are documented in this file.

This file is generated with [towncrier](https://towncrier.readthedocs.io/) from the
change fragments in the `changelog/` directory. Do not edit the released sections by
hand — add a fragment instead.

Releases before v1.2.0 predate this file; see the
[GitHub releases](https://github.com/opsmill/nornir-infrahub/releases) for their notes.

<!-- towncrier release notes start -->

## [nornir-infrahub - v1.2.0](https://github.com/opsmill/nornir-infrahub/tree/v1.2.0) - 2026-07-30

### Security

- Updated locked transitive dependencies to address reported vulnerabilities: `urllib3` to 2.6.3 (CVE-2026-21441), `ujson` to 5.12.0 (CVE-2026-32875, CVE-2026-32874), and `Pygments` to 2.20.0 (CVE-2026-4539). ([#70](https://github.com/opsmill/nornir-infrahub/issues/70))

### Removed

- Dropped support for Python 3.9, which is required by `infrahub-sdk` 1.16 and later. ([#60](https://github.com/opsmill/nornir-infrahub/issues/60))

### Added

- Added the `upload_file_object` and `download_file_object` task plugins for managing files on Infrahub nodes that inherit from `CoreFileObject`. Uploads are idempotent through SHA-1 checksum comparison and accept either a file path or in-memory bytes, and downloads decode text MIME types as UTF-8 while returning binary content base64-encoded, with an optional local save that skips writing when the local checksum already matches. ([#71](https://github.com/opsmill/nornir-infrahub/issues/71))
- Added support for customizing the Nornir host name through a schema mapping named `name`, for example `{"name": "name", "mapping": "hostname"}`. Without this mapping the inventory keeps using the node's `name` attribute. ([#75](https://github.com/opsmill/nornir-infrahub/issues/75))
- Added support for Python 3.14. The supported range is now Python 3.10 through 3.14.

### Changed

- The artifact tasks now go through the Infrahub SDK instead of issuing raw REST calls with `httpx`. `regenerate_host_artifact` uses `node.artifact_generate()`, `generate_artifacts` uses `artifact_definition.generate()`, and `get_artifact` uses `client.object_store.get()`. The `timeout` argument on `generate_artifacts` is retained for backwards compatibility but is now ignored, because request timeouts are governed by the SDK client configuration. ([#3](https://github.com/opsmill/nornir-infrahub/issues/3))
- Schema mappings and group mappings are now validated when the inventory is initialized. A mapping that spans more than one relation hop, or that references a name which is not a relationship on the host node kind, raises a `ValueError` with an explanatory message instead of failing later during resolution. Single-hop mappings such as `primary_address.address` are unaffected. ([#74](https://github.com/opsmill/nornir-infrahub/issues/74))
- Updated the runtime dependency constraints. `infrahub-sdk` now requires `>=1.20.1,<2` and no longer pulls in its `tests` extra, `pydantic` is constrained to `>=2.0.0,<3` to match the Pydantic v2 API the plugins already use, and `ruamel-yaml` is widened to `>=0.18.17,<0.20`.

### Fixed

- Fixed schema mappings that read an attribute through a relation, such as `primary_address.address`, failing with `AttributeError: 'NoneType' object has no attribute 'ip'`. The inventory previously pre-fetched each related kind separately and then fetched the host nodes, which overwrote the hydrated peers in the SDK store with minimal stubs. Related nodes are now hydrated in a single host fetch using `include=`, derived automatically from the configured mappings, so the manual `host_node.include` workaround is no longer needed. ([#74](https://github.com/opsmill/nornir-infrahub/issues/74))
- Fixed the inventory failing on node kinds that do not define a `name` attribute. Such nodes are now skipped unless a `name` schema mapping tells the inventory which attribute to use as the Nornir host name. ([#75](https://github.com/opsmill/nornir-infrahub/issues/75))

### Housekeeping

- Migrated the build and development toolchain from Poetry to `uv`, converting `pyproject.toml` to PEP 621 metadata with `hatchling` as the build backend and dependency groups for development dependencies, and replaced `mypy` with `ty` for type checking. ([#60](https://github.com/opsmill/nornir-infrahub/issues/60))
- Added an integration test suite that validates `InfrahubInventory` against a live Infrahub instance spun up per test class with `infrahub-testcontainers`, covering inventory loading, schema and group mappings, `CoreStandardGroup` membership, host filters, and branch routing. The suite is marked `integration` and excluded from the default `pytest` run; run it with `pytest -m integration` (requires Docker). ([#79](https://github.com/opsmill/nornir-infrahub/issues/79))
- Refreshed the documentation site: upgraded Docusaurus, reworked the Nornir documentation pages, and fixed the generated plugin reference template so it renders return types and escapes pipe characters in type names.
- Replaced `markdownlint` with `rumdl` for Markdown linting and formatting, carrying over the previously disabled rules and wiring it into `invoke lint` and the pre-commit hooks.
- Restructured the contributor tooling and reference material, recorded in ADR-001: a single source of truth for AI assistant skills and spec-kit extensions under `.agents/`, a ratified project constitution, contributor boundaries in `AGENTS.md`, and `dev/` reference content covering architecture, the inventory data model, SDK integration, testing, and task-plugin and artifact guides.
- Updated CI actions and development dependency bounds: `actions/checkout` 3 to 7, `actions/setup-python` 5 to 6, `crazy-max/ghaction-github-labeler` 4 to 6, and widened bounds for `ruff`, `pylint`, `invoke`, `rich`, and `docstring-parser`.
