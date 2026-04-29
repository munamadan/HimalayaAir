# Codex Session Template

Copy this at the start of every Codex session, replacing the phase number and name.

```text
Follow AGENTS.md.

Implement PHASE XX: PHASE NAME only.

Before editing code, read:
- docs/himalayaair-system-overview.md
- docs/codex/PHASE_INDEX.md
- docs/codex/phases/PHASE-XX-phase-name.md
- CHANGELOG.md if it exists
- prior summaries in docs/phase-summaries/ if they exist

Do not implement future phases. Do not change the approved architecture unless this phase file explicitly requires it.
Do not change `README.md` unless I explicitly request it.
Commit changes early and often, and keep commit messages lowercase.

At the end:
- run the verification commands listed in the phase file
- update CHANGELOG.md
- append the completed phase entry to CHANGELOG.md
- write docs/phase-summaries/PHASE-XX-summary.md
- report changed files, commands run, pass/fail results, and remaining risks
```
