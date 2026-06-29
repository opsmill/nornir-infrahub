# ADR-001: Adopt the Canonical OpsMill Agentic Structure

**Status**: Accepted
**Date**: 2026-06-29
**Source**: PR #82 (`bot/agentic-drift`) — `detecting-repo-drift` / `auditing-agentic-structure`

## Context

`nornir-infrahub` is one of several OpsMill repositories that AI coding agents (Claude Code, Codex, and future tools) operate on. Sibling repositories — `infrahub`, `styrmin`, `infrahub-mcp` — had converged on a shared, vendor-neutral layout for agent-consumed content, but this repository had drifted from it.

In particular, the spec-kit skills were committed as real files directly under `.claude/skills/`. That made the content Claude-specific and created a single Claude-only copy with no neutral source. Any second consumer (Codex, the spec-kit CLI, another agent) would need its own copy, and copies drift. The repository also lacked the `.agents/` source-of-truth directory, the pinned shared `opsmill-dev` skills, and the `dev/` reference layer that the sibling repositories use to record durable, human-facing rationale.

The goal was to align this Nornir plugin's repository with the canonical OpsMill agentic layout so that all current and future agents share one portable source of truth, and so that the same tooling Infrahub uses (spec-kit plus the OpsMill extensions and shared skills) works here unchanged.

## Decision

Adopt the canonical OpsMill agentic structure, with `.agents/` as the vendor-neutral source of truth and per-tool adapters layered on top of it.

- **`.agents/` is the single source of truth**: All agent-consumed content (spec-kit, OpsMill, and shared dev skills) lives under `.agents/skills/`. It is engine-agnostic — no tool's name appears in the canonical path.
- **Claude is exposed via a committed symlink**: `.claude/skills` is a committed symlink to `../.agents/skills` (git mode `120000`) rather than a second copy of the files. Claude Code reads its skills through the link, and spec-kit writes through the same link, so there is exactly one set of bytes and nothing can drift between a "Claude copy" and an "`.agents` copy".
- **Upgrade spec-kit to 0.11.9**: Bumped core spec-kit from `0.6.1.dev0` to **0.11.9** (upstream `github/spec-kit`), bringing the bundled `agent-context` extension, the `speckit-converge` skill, and `.specify/workflows/`.
- **Install the OpsMill spec-kit extensions**: Install the `opsmill` extension (v1.1.0, from `opsmill/opsmill-speckit`) and the bundled `agent-context` extension (`installed: [agent-context, opsmill]` in `.specify/extensions.yml`), adding the `speckit-opsmill-*` skills and hooks Infrahub uses.
- **Pin the shared `opsmill-dev` skills**: Install the seven shared `opsmill-dev` skills (`commit`, `creating-issues`, `creating-prd`, `grilling-ideas`, `monitoring-pull-requests`, `pr`, `rebase`) from `opsmill/opsmill-skills` and pin them with content hashes in `skills-lock.json`; the lockfile hashes match Infrahub's.
- **Establish the `dev/` reference layer**: Create `dev/{adr,guides,guidelines,knowledge}/` as the durable, human-facing record of *why* — architecture knowledge, Python guidelines, task-plugin and inventory guides, and these ADRs — separate from the agent-executable skills under `.agents/`.

## Consequences

- There is now a single source of truth for agent-consumed content. The Claude adapter is a symlink, not a copy, so the two cannot diverge.
- The layout is agent-agnostic. A future Codex adapter (or any other tool) points at the same `.agents/` content instead of forking its own copy.
- Spec-kit continues to work unchanged: because `.claude/skills` resolves to `.agents/skills`, spec-kit reads and writes through the link with no second location to maintain.
- The repository matches the canonical layout of `infrahub`, `styrmin`, and `infrahub-mcp`, so contributors and agents moving between repositories find the same structure, and the `auditing-agentic-structure` check passes (0 errors / 0 warnings).
- The seven shared skills are version-pinned, so they update deliberately (refresh the lockfile) rather than silently.
- Trade-off — committed symlinks require `core.symlinks=true` to materialize correctly on Windows and in some CI checkouts; a misconfigured client will see `.claude/skills` as a plain text file containing the link target instead of a directory. This is recorded as an informational note rather than a blocker.
- Trade-off — the third-party `review` and `critique` spec-kit extensions were deferred. They come from community repositories and their installation triggers an interactive trust prompt that cannot be answered from the agent sandbox, so adopting them is left as a separate, human-driven decision.

## Alternatives Considered

- **Keep spec-kit skills as real files under `.claude/skills/`**: Rejected — Claude-specific, no neutral source, and any second agent forces a divergent copy.
- **Duplicate the skills into both `.agents/skills/` and `.claude/skills/` as real files**: Rejected — two copies of the same content drift the moment one side is edited and the other is not.
- **Point Claude at `.agents/` through configuration instead of a symlink**: Rejected — a committed symlink is the convention the sibling repositories already use, keeps spec-kit's read/write path identical to its default, and needs no per-tool wiring.
- **Adopt the `review` and `critique` extensions now**: Deferred — third-party origin and an interactive trust prompt make this a human decision, not part of this mechanical alignment.
