# .agents/

Vendor-neutral source of truth for content that AI coding agents consume.

Portable material is authored **once** here and exposed to each agent through a thin
adapter (`.claude/`, `.codex/`, …), so adding or switching an agent is a wiring change
rather than a rewrite.

| Directory | Holds |
|-----------|-------|
| `skills/` | `SKILL.md` skills this repository defines for itself |
| `commands/` | Thin user-invoked entrypoints (present only if used) |
| `rules/` | Behavioural rules, authored once (present only if used) |

`skills/` is the load-bearing directory; `commands/` and `rules/` exist only when the
repository actually uses them. This directory was scaffolded as the structural home —
deciding which procedures are worth packaging as skills is authoring work tracked
separately.
