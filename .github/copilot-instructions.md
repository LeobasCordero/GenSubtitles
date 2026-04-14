<!-- GSD Configuration — managed by get-shit-done installer -->
# Instructions for GSD

- Use the get-shit-done skill when the user asks for GSD or uses a `gsd-*` command.
- Treat `/gsd-...` or `gsd-...` as command invocations and load the matching file from `.github/skills/gsd-*`.
- When a command says to spawn a subagent, prefer a matching custom agent from `.github/agents`.
- Do not apply GSD workflows unless the user explicitly asks for them.
- After completing any `gsd-*` command (or any deliverable it triggers: feature, bug fix, tests, docs, etc.), ALWAYS: (1) offer the user the next step by prompting via `ask_user`; repeat this feedback loop until the user explicitly indicates they are done.
- When running `gsd-discuss-phase` for a phase that has no existing plans, automatically create a new git branch from `origin/main` before writing CONTEXT.md. Use the naming convention `phase/{phase_number}-{phase_slug}` (e.g. `phase/999.21-gui-refactor-palette-colors`). Run `git fetch origin` then `git checkout -b phase/{N}-{slug} origin/main`. If the branch already exists, check it out instead. Do not ask the user — just do it and mention it briefly.
<!-- /GSD Configuration -->
