# GoatSkills

Private backup of personal AI agent skills, with an inventory of provider-managed skills. Keep this repository private: the backup preserves project examples and local setup instructions.

## Personal skills

The October 29, 2026 snapshot contains 15 skills from `~/.agents/skills`, plus the existing Goatnomious skill. Definitions, scripts, references, examples, fonts, and existing license notices are preserved. Bytecode and caches are excluded.

| Skill | Purpose |
| --- | --- |
| [babysit-pr](babysit-pr/SKILL.md) | Monitor pull requests through review and CI. |
| [bento](bento/SKILL.md) | Create announcement and release images. |
| [copywriting](copywriting/SKILL.md) | Write and improve marketing copy. |
| [council](council/SKILL.md) | Gather reviews from multiple model providers. |
| [deepen](deepen/SKILL.md) | Refine a task into a stronger prompt. |
| [diagram-design](diagram-design/SKILL.md) | Create diagrams and charts. |
| [file-pr](file-pr/SKILL.md) | Open concise pull requests. |
| [frontend-design](frontend-design/SKILL.md) | Guide interface design. |
| [full-send](full-send/SKILL.md) | Finish authorized development work through merge. |
| [full-stop](full-stop/SKILL.md) | Prepare development work for a human to merge. |
| [goatnomious](goatnomious/SKILL.md) | Plan and execute multi-step development work. |
| [leaving-pr-comments](leaving-pr-comments/SKILL.md) | Follow conventions for GitHub comments. |
| [modernize](modernize/SKILL.md) | Bring older pull requests up to date. |
| [pls](pls/SKILL.md) | Publish documents through the configured page service. |
| [sol-loop](sol-loop/SKILL.md) | Iterate on code review findings. |
| [takeover](takeover/SKILL.md) | Take over existing work. |

[The personal inventory](inventory/personal-skills.json) records a SHA-256 checksum for every copied file. This is a snapshot, not an automatic sync; the installed skills remain unchanged.

## Provider-managed skills

[The provider inventory](inventory/provider-skills.json) records 94 skill definitions with names, package versions where available, relative paths, and checksums. It covers the latest locally cached plugin versions, Codex system skills, and Claude synced skills; presence on disk does not prove that a skill is currently enabled. Provider-managed content and account settings are not copied.

## Secret checks

Install [Gitleaks](https://github.com/gitleaks/gitleaks), then run from any directory:

```bash
/path/to/GoatSkills/scripts/check-secrets
```

Run `python3 scripts/test-secret-check.py` from the repository to test the scanner exception and history detection with temporary synthetic fixtures.

The check scans the working directory and all locally available Git history with redacted output. Fetch remote branches and tags before checking history. A failed scan must be reviewed before pushing. The configuration permits only the exact deterministic signing test key in `pls/scripts/noise_sig.py`; it does not exempt the rest of the file.

[The audit notes](AUDIT.md) explain what was checked and which non-secret details remain. A passing secret scan is not approval to make this backup public.

## Sources and licenses

Original repository material uses the [MIT license](LICENSE). Copied third-party skills and assets retain their upstream terms and attribution; the root license does not replace them.

- `frontend-design`: installed from [anthropics/skills](https://github.com/anthropics/skills), with its Apache 2.0 license retained.
- `copywriting`: installed from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills), with local revisions and attribution in the skill.
- `diagram-design`: installed from [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design), declaring MIT in its definition.
- Bundled font license notices remain under `bento/assets/fonts/`.
