---
name: code-review
description: Review NOISE pull requests against its routing, transport, persistence, casino, migration, sidecar, security, and public-contract rules. Use this for code review or pull request review in the NOISE repository.
---

# NOISE code review

This is a read-only review guide. The root `AGENTS.md` is authoritative; use
this skill to select the right source paths and invariants without duplicating
that policy.

## Review sequence

1. Read `AGENTS.md`, then read the applicable sections of
   `references/review-matrix.md`.
2. Inspect the complete diff against the target base. Establish whether each
   finding is introduced by the diff or is a pre-existing condition that the
   diff makes reachable. Read callers, callees, registration, persistence, and
   delivery code instead of reviewing isolated hunks.
3. Trace the changed behavior to every affected surface: command declaration
   and help, Signal and Discord delivery, worker/deferred execution,
   persistence and recovery, migrations, sidecars and deployment mapping, and
   public documentation.
4. Check the relevant invariants in the matrix. Treat an intentional exception
   as a contract only when the source or authoritative documentation proves it.
5. Return ranked findings first. Do not make edits or propose a patch as if it
   had been applied.

## Finding contract

Every finding must include:

- a severity (`High`, `Medium`, or `Low`) and a concise title;
- an exact repository file and line supporting the claim;
- the changed path or call chain that causes the problem;
- concrete impact, including data, money, authorization, delivery, recovery,
  or public-boundary consequences where applicable;
- confidence and whether the evidence is source-only or functionally exercised;
- the smallest fix direction, without applying it;
- the important surfaces that were not exercised.

Use `High` for data loss, ledger or balance corruption, authorization/privacy
exposure, duplicate financial side effects, or an outage/recovery failure.
Use `Medium` for broken command or transport contracts, migration/restart
hazards, or cross-service behavior that can fail in production. Use `Low` for
documentation, maintainability, or bounded correctness concerns without those
effects. Do not report style preferences as findings.

If no reportable finding remains after tracing the applicable paths, say so and
list the relevant surfaces that were not exercised. Do not treat existing
Copilot comments or the pull-request description as proof that the full diff
was reviewed.

## Permitted verification

Use the smallest non-prohibited proof from `AGENTS.md`:

- `git diff --check` for every review;
- `clojure -J-Dnoise.skip-storage-init=true -M:verify` after visible command
  surface changes;
- the repository migration verifier against disposable state after migration
  changes;
- `uv run python -m py_compile` for changed Python scripts.

Do not run unit tests, linting, formatting, `scripts/verify.py`, live bot,
scheduled jobs, live network or LLM behavior, or commands that touch active
databases unless Goat explicitly authorizes that exact operation. Never create
or use GitHub Actions or workflow files for review setup. Do not use MCP tools
that can write, publish, merge, deploy, modify issues, or mutate repository
state.
