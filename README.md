# GoatSkills

Private backup of personal AI agent skills, with an inventory of provider-managed skills. Keep this repository private: the backup preserves project examples and local setup instructions.

## Personal and project skills

The 2026-11-06 snapshot contains 78 global skills and 36 project-local skill folders, with 1020 files. Definitions, scripts, references, examples, fonts, and license notices are preserved byte for byte. Executable permissions are recorded. Symlinked installations are copied once; project variants keep their own paths under `projects/`.

Global skills come from `~/.agents/skills` and the additional local skill folders for Claude, Codex, Cursor, and OpenCode. Project skills come from `.agents/skills`, `.claude/skills`, `.github/skills`, `.codex/skills`, and `.cursor/skills` in the immediate projects under `~/Github`.

| Global skill | Source |
| --- | --- |
| [architect](architect/SKILL.md) | `~/.agents/skills/architect` |
| [arena](arena/SKILL.md) | `~/.agents/skills/arena` |
| [automate-me](automate-me/SKILL.md) | `~/.agents/skills/automate-me` |
| [babysit-pr](babysit-pr/SKILL.md) | `~/.agents/skills/babysit-pr` |
| [benchmark-checklist](benchmark-checklist/SKILL.md) | `~/.agents/skills/benchmark-checklist` |
| [bento](bento/SKILL.md) | `~/.agents/skills/bento` |
| [blast-radius](blast-radius/SKILL.md) | `~/.agents/skills/blast-radius` |
| [bro](bro/SKILL.md) | `~/.agents/skills/bro` |
| [copywriting](copywriting/SKILL.md) | `~/.agents/skills/copywriting` |
| [correct](correct/SKILL.md) | `~/.agents/skills/correct` |
| [council](council/SKILL.md) | `~/.agents/skills/council` |
| [create-formal-verification-skill](create-formal-verification-skill/SKILL.md) | `~/.agents/skills/create-formal-verification-skill` |
| [create-verification-skill](create-verification-skill/SKILL.md) | `~/.agents/skills/create-verification-skill` |
| [deepen](deepen/SKILL.md) | `~/.agents/skills/deepen` |
| [diagram-design](diagram-design/SKILL.md) | `~/.agents/skills/diagram-design` |
| [figure-it-out](figure-it-out/SKILL.md) | `~/.agents/skills/figure-it-out` |
| [file-pr](file-pr/SKILL.md) | `~/.agents/skills/file-pr` |
| [frontend-design](frontend-design/SKILL.md) | `~/.agents/skills/frontend-design` |
| [full-send](full-send/SKILL.md) | `~/.agents/skills/full-send` |
| [full-stop](full-stop/SKILL.md) | `~/.agents/skills/full-stop` |
| [how](how/SKILL.md) | `~/.agents/skills/how` |
| [in-your-own-words](in-your-own-words/SKILL.md) | `~/.agents/skills/in-your-own-words` |
| [interrogate](interrogate/SKILL.md) | `~/.agents/skills/interrogate` |
| [ketchup](ketchup/SKILL.md) | `~/.agents/skills/ketchup` |
| [ketchup-video](ketchup-video/SKILL.md) | `~/.agents/skills/ketchup-video` |
| [leaving-pr-comments](leaving-pr-comments/SKILL.md) | `~/.agents/skills/leaving-pr-comments` |
| [maintain-formal-verification-skill](maintain-formal-verification-skill/SKILL.md) | `~/.agents/skills/maintain-formal-verification-skill` |
| [maintain-verification-skill](maintain-verification-skill/SKILL.md) | `~/.agents/skills/maintain-verification-skill` |
| [make-bot-ui](make-bot-ui/SKILL.md) | `~/.agents/skills/make-bot-ui` |
| [modernize](modernize/SKILL.md) | `~/.agents/skills/modernize` |
| [no-comments](no-comments/SKILL.md) | `~/.agents/skills/no-comments` |
| [pls](pls/SKILL.md) | `~/.agents/skills/pls` |
| [poteto-help](poteto-help/SKILL.md) | `~/.agents/skills/poteto-help` |
| [poteto-mode](poteto-mode/SKILL.md) | `~/.agents/skills/poteto-mode` |
| [principle-attack-the-premise](principle-attack-the-premise/SKILL.md) | `~/.agents/skills/principle-attack-the-premise` |
| [principle-boundary-discipline](principle-boundary-discipline/SKILL.md) | `~/.agents/skills/principle-boundary-discipline` |
| [principle-build-the-lever](principle-build-the-lever/SKILL.md) | `~/.agents/skills/principle-build-the-lever` |
| [principle-encode-lessons-in-structure](principle-encode-lessons-in-structure/SKILL.md) | `~/.agents/skills/principle-encode-lessons-in-structure` |
| [principle-exhaust-the-design-space](principle-exhaust-the-design-space/SKILL.md) | `~/.agents/skills/principle-exhaust-the-design-space` |
| [principle-experience-first](principle-experience-first/SKILL.md) | `~/.agents/skills/principle-experience-first` |
| [principle-explain-the-number](principle-explain-the-number/SKILL.md) | `~/.agents/skills/principle-explain-the-number` |
| [principle-fix-root-causes](principle-fix-root-causes/SKILL.md) | `~/.agents/skills/principle-fix-root-causes` |
| [principle-foundational-thinking](principle-foundational-thinking/SKILL.md) | `~/.agents/skills/principle-foundational-thinking` |
| [principle-guard-the-context-window](principle-guard-the-context-window/SKILL.md) | `~/.agents/skills/principle-guard-the-context-window` |
| [principle-laziness-protocol](principle-laziness-protocol/SKILL.md) | `~/.agents/skills/principle-laziness-protocol` |
| [principle-make-operations-idempotent](principle-make-operations-idempotent/SKILL.md) | `~/.agents/skills/principle-make-operations-idempotent` |
| [principle-migrate-callers-then-delete-legacy-apis](principle-migrate-callers-then-delete-legacy-apis/SKILL.md) | `~/.agents/skills/principle-migrate-callers-then-delete-legacy-apis` |
| [principle-minimize-reader-load](principle-minimize-reader-load/SKILL.md) | `~/.agents/skills/principle-minimize-reader-load` |
| [principle-model-the-domain](principle-model-the-domain/SKILL.md) | `~/.agents/skills/principle-model-the-domain` |
| [principle-never-block-on-the-human](principle-never-block-on-the-human/SKILL.md) | `~/.agents/skills/principle-never-block-on-the-human` |
| [principle-outcome-oriented-execution](principle-outcome-oriented-execution/SKILL.md) | `~/.agents/skills/principle-outcome-oriented-execution` |
| [principle-prove-it-works](principle-prove-it-works/SKILL.md) | `~/.agents/skills/principle-prove-it-works` |
| [principle-redesign-from-first-principles](principle-redesign-from-first-principles/SKILL.md) | `~/.agents/skills/principle-redesign-from-first-principles` |
| [principle-separate-before-serializing-shared-state](principle-separate-before-serializing-shared-state/SKILL.md) | `~/.agents/skills/principle-separate-before-serializing-shared-state` |
| [principle-sequence-verifiable-units](principle-sequence-verifiable-units/SKILL.md) | `~/.agents/skills/principle-sequence-verifiable-units` |
| [principle-subtract-before-you-add](principle-subtract-before-you-add/SKILL.md) | `~/.agents/skills/principle-subtract-before-you-add` |
| [principle-test-behavior-not-implementation](principle-test-behavior-not-implementation/SKILL.md) | `~/.agents/skills/principle-test-behavior-not-implementation` |
| [principle-type-system-discipline](principle-type-system-discipline/SKILL.md) | `~/.agents/skills/principle-type-system-discipline` |
| [recall](recall/SKILL.md) | `~/.agents/skills/recall` |
| [reflect](reflect/SKILL.md) | `~/.agents/skills/reflect` |
| [setup-pstack](setup-pstack/SKILL.md) | `~/.agents/skills/setup-pstack` |
| [sharpen](sharpen/SKILL.md) | `~/.agents/skills/sharpen` |
| [show-me-your-work](show-me-your-work/SKILL.md) | `~/.agents/skills/show-me-your-work` |
| [sol-loop](sol-loop/SKILL.md) | `~/.agents/skills/sol-loop` |
| [statechart](statechart/SKILL.md) | `~/.agents/skills/statechart` |
| [swarm](swarm/SKILL.md) | `~/.agents/skills/swarm` |
| [takeover](takeover/SKILL.md) | `~/.agents/skills/takeover` |
| [tdd](tdd/SKILL.md) | `~/.agents/skills/tdd` |
| [teach](teach/SKILL.md) | `~/.agents/skills/teach` |
| [technical-writing](technical-writing/SKILL.md) | `~/.agents/skills/technical-writing` |
| [typescript-best-practices](typescript-best-practices/SKILL.md) | `~/.agents/skills/typescript-best-practices` |
| [unslop](unslop/SKILL.md) | `~/.agents/skills/unslop` |
| [untangle-codebase](untangle-codebase/SKILL.md) | `~/.agents/skills/untangle-codebase` |
| [why](why/SKILL.md) | `~/.agents/skills/why` |
| [domain-modeling](domain-modeling/SKILL.md) | `~/.claude/skills/domain-modeling` |
| [grill-me](grill-me/SKILL.md) | `~/.claude/skills/grill-me` |
| [grill-with-docs](grill-with-docs/SKILL.md) | `~/.claude/skills/grill-with-docs` |
| [grilling](grilling/SKILL.md) | `~/.claude/skills/grilling` |

Project variants are grouped below. The [personal inventory](inventory/personal-skills.json) lists every source path, destination, file checksum, and executable flag.

| Project | Skill folders |
| --- | --- |
| Caldera | [caveman](projects/Caldera/agents/caveman/SKILL.md), [diagnose](projects/Caldera/agents/diagnose/SKILL.md), [grill-me](projects/Caldera/agents/grill-me/SKILL.md), [grill-with-docs](projects/Caldera/agents/grill-with-docs/SKILL.md), [handoff](projects/Caldera/agents/handoff/SKILL.md), [improve-codebase-architecture](projects/Caldera/agents/improve-codebase-architecture/SKILL.md), [prototype](projects/Caldera/agents/prototype/SKILL.md), [setup-matt-pocock-skills](projects/Caldera/agents/setup-matt-pocock-skills/SKILL.md), [tdd](projects/Caldera/agents/tdd/SKILL.md), [zoom-out](projects/Caldera/agents/zoom-out/SKILL.md) |
| GoatGit | [brainstorming](projects/GoatGit/agents/brainstorming/SKILL.md) |
| GoatSaas | [ui-ux-pro-max](projects/GoatSaas/agents/ui-ux-pro-max/SKILL.md) |
| KolFluent | [frontend-design](projects/KolFluent/agents/frontend-design/SKILL.md) |
| KoleneDesign | [brandkit](projects/KoleneDesign/agents/brandkit/SKILL.md), [design-taste-frontend](projects/KoleneDesign/agents/design-taste-frontend/SKILL.md), [design-taste-frontend-v1](projects/KoleneDesign/agents/design-taste-frontend-v1/SKILL.md), [full-output-enforcement](projects/KoleneDesign/agents/full-output-enforcement/SKILL.md), [gpt-taste](projects/KoleneDesign/agents/gpt-taste/SKILL.md), [high-end-visual-design](projects/KoleneDesign/agents/high-end-visual-design/SKILL.md), [image-to-code](projects/KoleneDesign/agents/image-to-code/SKILL.md), [imagegen-frontend-mobile](projects/KoleneDesign/agents/imagegen-frontend-mobile/SKILL.md), [imagegen-frontend-web](projects/KoleneDesign/agents/imagegen-frontend-web/SKILL.md), [industrial-brutalist-ui](projects/KoleneDesign/agents/industrial-brutalist-ui/SKILL.md), [minimalist-ui](projects/KoleneDesign/agents/minimalist-ui/SKILL.md), [redesign-existing-projects](projects/KoleneDesign/agents/redesign-existing-projects/SKILL.md), [stitch-design-taste](projects/KoleneDesign/agents/stitch-design-taste/SKILL.md) |
| Syndica | [yeet](projects/Syndica/agents/yeet/SKILL.md) |
| noise | [copywriting](projects/noise/agents/copywriting/SKILL.md), [frontend-design](projects/noise/agents/frontend-design/SKILL.md), [code-review](projects/noise/github/code-review/SKILL.md) |
| t3code | [contribution-triage](projects/t3code/agents/contribution-triage/SKILL.md), [test-t3-app](projects/t3code/agents/test-t3-app/SKILL.md), [test-t3-mobile](projects/t3code/agents/test-t3-mobile/SKILL.md) |
| t3code-transcript-view | [contribution-triage](projects/t3code-transcript-view/agents/contribution-triage/SKILL.md), [test-t3-app](projects/t3code-transcript-view/agents/test-t3-app/SKILL.md), [test-t3-mobile](projects/t3code-transcript-view/agents/test-t3-mobile/SKILL.md) |

## Refresh and verify the snapshot

Run these commands from this repository:

```bash
uv run --no-project python scripts/sync-skills.py --write
uv run --no-project python scripts/sync-skills.py
scripts/check-secrets
```

The first command refreshes the copied skills and inventories. The second checks file contents, executable flags, and the inventories without changes. It exits with an error when the installed sources differ from the backup. Refreshing removes only stale files listed in the previous personal inventory. Installed skills remain unchanged. Git metadata, bytecode, caches, virtual environments, and dependency directories are excluded. A credential-shaped file or nested file symlink stops the refresh for review.

## Provider-managed skills

The [provider inventory](inventory/provider-skills.json) records 112 definitions from the latest locally cached plugin versions, Codex system skills, Claude synced skills, and Cursor built-ins. Each entry has its package, version where available, relative path, and SHA-256 checksum. Presence on disk does not prove that a skill is enabled. Provider-managed packages and account settings are not copied.

## Secret checks

Install [Gitleaks](https://github.com/gitleaks/gitleaks), then run from any directory:

```bash
/path/to/GoatSkills/scripts/check-secrets
```

Run `uv run --no-project python scripts/test-secret-check.py` from the repository to test the scanner exception and history detection with temporary synthetic fixtures.

The check scans the working directory and all locally available Git history with redacted output. Fetch remote branches and tags before checking history. A failed scan must be reviewed before pushing. The configuration permits only the exact deterministic signing test key in `pls/scripts/noise_sig.py`; it does not exempt the rest of the file.

[The audit notes](AUDIT.md) explain what was checked and which non-secret details remain. A passing secret scan is not approval to make this backup public.

## Sources and licenses

Original repository material uses the [MIT license](LICENSE). Copied third-party skills and assets retain their upstream terms and attribution; the root license does not replace them.

- `frontend-design`: installed from [anthropics/skills](https://github.com/anthropics/skills), with its Apache 2.0 license retained.
- `copywriting`: installed from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills), with local revisions and attribution in the skill.
- `diagram-design`: installed from [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design), declaring MIT in its definition.
- Bundled font license notices remain under `bento/assets/fonts/`.

Additional copied skills and project variants retain the license notices and attribution supplied with their installed files.
