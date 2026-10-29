---
name: deepen
description: Turn a question, task or prompt into a deeper version of itself, not a bigger one. Says what a top professional would do that wasn't asked for, the rawest material they would start from, the methods and tools they would use, and what other than the agent or the user would show the result is right, then rewrites the prompt to ask for exactly that. Use only when the user explicitly asks for it, as in /deepen, $deepen, "deepen this" or "use deepen", and never on your own for ordinary questions.
---

# deepen

This skill runs one prompt against the user's question or task:

> I want a deeper version of this task, not a bigger one. Before rewriting
> it: (1) say what a top professional in this field would do here that I'm
> not asking for; (2) name the rawest material they would start from instead
> of what has already been digested for me; (3) name the specific methods and
> tools they would use; (4) say what, other than you or me, would show the
> result is right. Then rewrite my prompt to ask for exactly that.

The task is the text the user gave with the skill; Claude Code passes it as
`ARGUMENTS:`. With no text, use the user's most recent request in this
conversation. The output is the four answers and the rewritten prompt, not
the work itself, so stop there unless the user also asked you to run it. In
that case show the rewritten prompt first, then carry it out.

## Ground it first

Take a few quick read-only looks at whatever the task names (files, docs, a
thread, a dataset) so the answers fit this case rather than the field in
general, and don't start answering the task itself. Repository and user rules
still apply. A repository may forbid tests or keep production data, logs and
credentials off-limits, so check what's allowed before naming sources or
methods.

## The four answers

Name the professional as specifically as the case allows ("a staff SRE who
has run this kind of migration", not "an expert"), then answer in order, a
few sentences or a short list each:

1. **What they would do that wasn't asked for.** Only steps that make the
   result more correct, or more useful for the same goal. Leave out anything
   that only adds scope; if real depth needs more scope, list it separately as
   an option.
2. **The rawest material.** The primary source they would start from instead
   of a digest: the code over its docs, the spec or doc over a post about it,
   raw rows, logs, filings, transcripts or receipts over a summary or
   dashboard. Name concrete locations (a path, URL, table, endpoint or
   dataset), confirm the ones a quick read-only check can confirm, and mark
   the rest unconfirmed. If the rawest material is off-limits or unavailable,
   say so and name the best permitted substitute.
3. **Methods and tools.** Named and specific: a technique, command, library,
   query or statistical test. Prefer what's already installed and allowed
   here, and say so when a better tool would need installing or permission.
4. **What, other than the agent or the user, would show it's right.** A check
   that can pass or fail without either party's judgment: a reproduction, a
   check the repository allows, a measurement against a stated threshold, a
   primary source that confirms the claim, or an independent reviewer. When
   the work is a matter of taste, such as design or tone, and the user's
   approval is the real acceptance test, say so and name what would make that
   approval well informed, such as a side-by-side specimen.

Leave out generic best practice. An item that would fit any task in the field
doesn't belong here.

## The rewritten prompt

Write it in the user's voice, ready to paste or run, in a fenced `text` block.
It keeps the original goal and size and states:

- the goal, and what the result is for when that's known
- the sources to start from (answer 2)
- the method (answers 1 and 3)
- what stays out of scope
- the finish check (answer 4) and what to return

Keep it as short as the task allows. Anything that needs the user's
permission, such as production data, paid calls or installs, stays out of the
prompt and goes in a question underneath it. If the original was already
deep, say so in a sentence and change only what helps. End with one line
offering to run it.
