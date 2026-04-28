# HimalayaAir Codex Phase Workflow Pack

Copy these files into the root of your HimalayaAir repository.

Recommended layout after copying:

```text
AGENTS.md
docs/himalayaair-system-overview.md
docs/codex/PHASE_INDEX.md
docs/codex/SESSION_TEMPLATE.md
docs/codex/phases/PHASE-00-codex-governance.md
...
docs/phase-summaries/PHASE-SUMMARY-TEMPLATE.md
prompts/PHASE-00-codex-governance-prompt.md
...
```

How to use:

1. Open a new Codex session.
2. Paste the prompt from the matching file in `prompts/`.
3. Let Codex implement that phase only.
4. Review the diff.
5. Ensure tests/checks, CHANGELOG.md, and phase summary are present.
6. Commit.
7. Start the next session with the next phase prompt.

Do not ask Codex to implement multiple phases in one session unless you intentionally want a large, high-risk diff.
