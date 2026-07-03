# Documentation Guidelines

Conventions for the published documentation in `nornir-infrahub`. The primary
source is the "Documentation Guidelines" section of the repository `AGENTS.md`;
this file records where docs live, how they are generated, and how to preview,
build, and lint them.

This `dev/` layer is separate internal reference for contributors and is **not**
part of the published documentation site.

## Where docs live

The published docs are a [Docusaurus](https://docusaurus.io/) site under `docs/`
(`docusaurus.config.ts`, `package.json`, `sidebars.ts`). Pages live in
`docs/docs/` and follow the [Diataxis framework](https://diataxis.fr/), organized
into three category directories:

- `docs/docs/guides/` — task-oriented how-to pages.
- `docs/docs/topics/` — understanding-oriented explanations.
- `docs/docs/references/` — information-oriented reference (plugin API under
  `references/plugins/`).

Navigation is defined by hand in `docs/sidebars.ts` (the `nornirSidebar`); a new
page must be added there to appear in the sidebar. There is currently no
`tutorials/` directory even though the Diataxis framework in `AGENTS.md` names
tutorials as a category — add pages under the directories that exist.

## Hand-written vs. generated pages

Most pages (`getting-started.mdx`, the docs-root `readme.mdx`, and everything under
`guides/` and `topics/`) are written and maintained by hand.

The per-plugin **reference** pages under `docs/docs/references/plugins/` are
**generated** from the plugin source docstrings by `invoke generate-docs`
(`generate_docs` in `tasks.py`). It walks `nornir_infrahub/plugins/{inventory,tasks}/`
(skipping `__init__.py`), parses each module/class/function docstring with
`docstring_parser`, and renders `docs/_templates/plugin.mdx.j2` to
`references/plugins/<name>_<type>.mdx`. It also renders `_templates/readme.mdx.j2`
to `references/plugins/_plugin_index.mdx`.

Because the plugin API pages come from docstrings, **do not hand-edit the
generated `<name>_<type>.mdx` files** — improve the docstring in the plugin source
and re-run `invoke generate-docs`. Public classes and functions should carry
docstrings with `Args:`, `Returns:`, `Raises:`, and an `Example:` block (see the
Python guidelines) so the reference renders completely. The docs-root `readme.mdx`
is maintained by hand; `invoke generate-docs` only writes the generated
`_plugin_index.mdx` (there is no hand-maintained readme under `references/plugins/`).

## Preview and build

Run the docs tasks (defined in `tasks.py`) from the repo root:

```bash
invoke docs-install    # install npm dependencies under docs/ (once)
invoke docs-serve      # dev server with live reload at http://localhost:3000
invoke docs-build      # production build (npm run build); exits non-zero on failure
```

`docs-serve` and `docs-build` run `npm install` automatically if `docs/node_modules`
is missing.

## Quality gates

Per `AGENTS.md`, run both linters whenever a `.md` or `.mdx` file changes:

- **Vale** — prose style, configured by `.vale.ini`. It applies the `Infrahub`
  style (rules in `.vale/styles/Infrahub/`) with `MinAlertLevel = warning`, maps
  `mdx` to Markdown, and ignores import statements and code blocks under
  `docs/**` (both `.md` and `.mdx` files). Spelling exceptions live in
  `.vale/styles/spelling-exceptions.txt`.
- **rumdl** — Markdown structure and formatting, configured by `[tool.rumdl]` in
  `pyproject.toml`. Check with `invoke lint-markdown` (or `rumdl check .`) and auto-fix
  with `rumdl fmt .` (also run by `invoke format`).

Run `vale` directly against the changed files (there is no `invoke` target wrapping it).

## Tone and terminology

Follow the tone and style rules in the `AGENTS.md` "Documentation Guidelines"
section rather than duplicating them here. In short:

- Professional but approachable, concise, informative over promotional.
- Guides: address the user directly with imperative verbs and stay task-focused.
- Topics: use a discursive tone that explains the "why" and gives rationale.
- Define new terms on first use and stay consistent with Infrahub's data-model
  and UI naming conventions.

## Publishing

Docs are synced to the central `opsmill/infrahub-docs` repository by the
`Sync Docs Folders` GitHub Actions workflow (`.github/workflows/sync-docs.yml`).
It triggers on pushes to `stable` that touch `docs/docs/**` or `docs/sidebars.ts`,
copies `docs/docs/*` into `docs-nornir/` and `sidebars.ts` into
`sidebars-nornir.ts` in the target repo, and commits/pushes the changes there.
Merging documentation changes to `stable` is what publishes them.
