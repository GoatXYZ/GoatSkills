# 🐐 GoatSkills

**A collection of AI agent skills and autonomous development workflows.**

Define, document, and share reusable skill definitions for AI coding agents. Each skill is self-contained with its own specification, invocation rules, and agent configurations.

---

## ✨ Skills

### 🤖 Goatnomious

A plan-first autonomous development workflow for AI agents. Gathers clarifications, writes detailed implementation plans, self-critiques through multiple iterations, then executes task-by-task.

**Key capabilities:**
- 📋 **Plan writing** — Comprehensive task mapping with exact file paths and commands
- 🔄 **Self-hardening** — Up to 5 iterations of autonomous plan critique
- ⚡ **Task execution** — Subagent dispatch with spec and code-quality review
- 🛑 **Hard stops** — Pauses only for missing dependencies, contradictory failures, or blocked tasks

**Invocation:** Explicit only — use `$goatnomious` or direct naming.

---

## 🏗️ Structure

```
GoatSkills/
└── goatnomious/
    ├── SKILL.md              # Complete skill specification
    └── agents/
        └── openai.yaml       # OpenAI agent configuration
```

Each skill lives in its own directory with:
- 📄 `SKILL.md` — Full specification, phases, and execution rules
- ⚙️ `agents/` — Platform-specific agent configurations (OpenAI, Claude, etc.)

---

## ➕ Adding a Skill

1. Create a new directory: `my-skill/`
2. Write `SKILL.md` with invocation rules, workflow phases, and execution guidelines
3. Add agent configs in `agents/` for each target platform
4. Open a PR

---

## 📄 License

MIT

---

<p align="center">
  🐐 Built by <a href="https://github.com/GoatXYZ">GOAT.XYZ</a>
</p>
