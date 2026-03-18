---
name: goatnomious
description: Plan-first autonomous development for feature work, implementation requests, and multi-step code changes. Use only when the user explicitly invokes Goatnomious or `$goatnomious`, or directly instructs the agent to use Goatnomious by name. This skill gathers clarifications in one batch, writes a detailed implementation plan to `docs/plans/YYYY-MM-DD-feature.md`, hardens that plan without human input, then executes task-by-task with subagent-driven implementation and review.
---

# Goatnomious

## Overview

Use this skill only on explicit invocation. When invoked, operate as a deterministic plan-first development workflow: gather context, ask one batched set of clarifying questions, write the implementation plan file, harden it through self-critique, then execute the final plan without waiting for further human input unless a hard stop condition is hit.

## Invocation Rules

- Do not use this skill implicitly.
- Do not activate this skill for generic autonomy requests that do not name Goatnomious.
- Accept any explicit invocation that clearly names Goatnomious, including `$goatnomious`, `Use Goatnomious`, or direct instructions to use Goatnomious by name.

## Phase 1: Plan Writing

When given a goal or feature request:

1. Analyze the request and inspect the local codebase first.
2. Generate all clarifying questions in one batch. Use a brainstorming-style intent-refinement pass:
   - ask only the questions needed to remove execution ambiguity
   - group related questions together
   - prefer concrete, answerable questions over open-ended fishing
   - do not ask one question at a time
3. After receiving answers, map the full file impact:
   - which files will be created
   - which files will be modified
   - which files will be deleted
4. Write a complete implementation plan to `docs/plans/YYYY-MM-DD-<feature>.md`.
5. Use this exact header template at the top of the plan file:

```md
# [Feature] Implementation Plan

> **For agentic workers:** Execute this plan task-by-task using subagent-driven-development.

**Goal:** [One sentence]
**Architecture:** [2-3 sentences]
**Tech Stack:** [Key technologies]
***
```

6. Write the rest of the plan as bite-sized checkbox tasks using `- [ ]`.
7. Make every task TDD-first and executable in 2-5 minutes.
8. For every task, include:
   - exact file paths
   - exact commands
   - expected output
9. Make the plan decision-complete. A skilled developer with zero codebase context must be able to execute it without guessing.

## Phase 2: Autonomous Plan Hardening

After the plan is written, harden the same plan file in place with zero human input.

Repeat until three consecutive passes find zero issues, capped at five total iterations:

1. Attack the plan as a hostile critic.
2. Ask:
   - what assumptions are wrong
   - what is missing
   - what breaks if a referenced file, tool, or dependency does not exist
   - what ambiguity would cause an agent to guess wrong
3. List every issue found, no matter how small.
4. Revise the plan to fix every issue.
5. Re-read the revised plan cold as if you did not write it.
6. Check whether a skilled developer with zero codebase knowledge could execute every step without guessing.
7. If issues remain, reset the consecutive-clean counter to zero and continue.
8. If a pass is clean, increment the consecutive-clean counter.
9. Stop early only after three consecutive clean passes.
10. If iteration five finishes without reaching three consecutive clean passes, surface the remaining issues to the human and stop.

## Phase 3: Autonomous Execution

Load the final plan and execute it without waiting for human input unless a hard stop condition is hit.

For each task in the plan:

1. Dispatch a fresh implementation subagent with only:
   - the task text
   - the minimum task-local context required to complete it
2. Do not pass the full session history.
3. Require the implementation subagent to:
   - write tests first
   - make the tests pass
   - self-review the change
   - commit the change
4. Dispatch a fresh spec-compliance reviewer and ask whether the implementation matches the spec exactly, no more and no less.
5. If spec review fails, return the findings to the implementer, fix the task, and re-review.
6. Dispatch a fresh code-quality reviewer.
7. If code-quality review fails, return the findings to the implementer, fix the task, and re-review.
8. Mark the task complete only when both reviews pass.
9. Proceed to the next task only after the current task is complete or blocked.

## Hard Stop Conditions

Pause for human input only when one of these occurs:

- a dependency or tool is missing and cannot be installed
- a test fails in a way that contradicts the plan's core assumption
- two consecutive subagents report `BLOCKED` on the same task

Do not pause for any other reason.

## Completion Requirements

After all tasks are complete:

1. Run all tests.
2. Report a concise implementation summary.
3. Open a PR.

If the environment cannot open a PR, treat that as an operational blocker and report it explicitly rather than silently skipping it.

## Output Standard

Return:

- what changed
- how it was validated
- what remains blocked or uncertain, if anything
