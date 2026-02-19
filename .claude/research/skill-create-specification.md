# /skill-create Framework Specification

> From [everything-claude-code](https://github.com/affaan-m/everything-claude-code) by @affaan-m
> Cloned to /tmp/everything-claude-code for reference

## What Is It?

`/skill-create` is a **Claude Code slash command** that analyzes a git repository's history to extract coding patterns, conventions, and workflows, then generates a **SKILL.md** file — a structured markdown document that teaches Claude Code how your team/project works.

It's the "local version" of the Skill Creator GitHub App. Instead of needing a hosted service, it runs entirely within Claude Code using git commands.

## Core Concept: Skills

A **skill** in the ECC framework is a markdown file (always named `SKILL.md`) inside a named directory under `.claude/skills/` or `~/.claude/skills/`. Skills are:
- **Auto-triggered** by Claude Code based on context matching
- **Domain knowledge** that Claude uses to guide its behavior
- **Structured** with frontmatter (YAML) + sections describing when/how to use the knowledge

### SKILL.md Format

```markdown
---
name: {skill-name}
description: {what this skill teaches}
version: 1.0.0        # optional
source: local-git-analysis  # optional, for generated skills
analyzed_commits: 150       # optional, for generated skills
---

# {Skill Title}

{Brief description}

## When to Activate
- {condition 1}
- {condition 2}

## {Section 1 - e.g., Code Architecture}
{content}

## {Section 2 - e.g., Workflows}
{content}

## {Section N}
{content}
```

### Directory Structure

```
.claude/skills/                    # Project-level skills
  my-project-patterns/
    SKILL.md                       # Required filename
  another-skill/
    SKILL.md
    config.json                    # Optional supporting files
    scripts/                       # Optional

~/.claude/skills/                  # User-level skills (all projects)
  learned/                         # Auto-extracted patterns
    pattern-name.md
  {skill-name}/
    SKILL.md
```

## How /skill-create Works

### Step 1: Gather Git Data
```bash
# Recent commits with file changes
git log --oneline -n ${COMMITS:-200} --name-only --pretty=format:"%H|%s|%ad" --date=short

# File change frequency (most-modified files)
git log --oneline -n 200 --name-only | grep -v "^$" | grep -v "^[a-f0-9]" | sort | uniq -c | sort -rn | head -20

# Commit message patterns
git log --oneline -n 200 | cut -d' ' -f2- | head -50
```

### Step 2: Detect Patterns

| Pattern Type | Detection Method |
|---|---|
| Commit conventions | Regex on messages (feat:, fix:, chore:) |
| File co-changes | Files that always change together |
| Workflow sequences | Repeated file change patterns |
| Architecture | Folder structure and naming conventions |
| Testing patterns | Test file locations, naming, coverage |

### Step 3: Generate SKILL.md

Outputs a structured markdown file with:
- **Commit Conventions** — detected message patterns
- **Code Architecture** — folder structure and organization
- **Workflows** — repeating file change patterns (e.g., "Adding a component" always involves 3 files)
- **Testing Patterns** — test conventions

### Step 4 (Optional): Generate Instincts

With `--instincts` flag, also creates atomic instinct files for the continuous-learning-v2 system:

```yaml
---
id: {repo}-commit-convention
trigger: "when writing a commit message"
confidence: 0.8
domain: git
source: local-repo-analysis
---
# Use Conventional Commits
## Action
Prefix commits with: feat:, fix:, chore:, docs:, test:, refactor:
## Evidence
- Analyzed {n} commits
- {percentage}% follow conventional commit format
```

## Usage

```bash
/skill-create                    # Analyze current repo (200 commits)
/skill-create --commits 100      # Analyze last 100 commits
/skill-create --output ./skills  # Custom output directory
/skill-create --instincts        # Also generate instincts
```

## Output Locations

- **Skill file**: `.claude/skills/{repo-name}-patterns/SKILL.md`
- **Instincts**: `.claude/homunculus/instincts/inherited/{repo}-instincts.yaml`

## The Broader ECC Ecosystem

### Related Commands
- `/learn` — Extract patterns from current session (manual, one-off)
- `/skill-create` — Extract patterns from git history (automated, comprehensive)
- `/instinct-status` — View learned instincts with confidence scores
- `/instinct-import` — Import instincts from others
- `/evolve` — Cluster related instincts into skills/commands/agents

### The Learning Pipeline
```
Git History / Sessions
        │
        ▼
   /skill-create or /learn
        │
        ▼
   SKILL.md files + Instincts
        │
        ▼
   /evolve clusters instincts
        │
        ▼
   Generated skills/commands/agents
```

### Types of Skills in ECC (43 total)

**Framework & Language (16)**: coding-standards, python-patterns, golang-patterns, django-*, springboot-*, java-coding-standards, frontend-patterns, backend-patterns, cpp-*

**Database (3)**: clickhouse-io, jpa-patterns, postgres-patterns

**Workflow & Quality (8)**: tdd-workflow, verification-loop, continuous-learning, continuous-learning-v2, eval-harness, iterative-retrieval, security-review/scan, strategic-compact

**Meta/Advanced**: configure-ecc, project-guidelines-example, content-hash-cache-pattern, cost-aware-llm-pipeline, regex-vs-llm-structured-text, swift-*, nutrient-document-processing, deployment-patterns, database-migrations, api-design, e2e-testing, docker-patterns, django-security

## Key Insights for Our Use Case

1. **Skills are just markdown files** — no special tooling needed to create them
2. **The SKILL.md filename is required** — Claude Code discovers skills by looking for this filename
3. **Frontmatter matters** — `name` and `description` help Claude decide when to activate
4. **"When to Activate" section is critical** — tells Claude the trigger conditions
5. **Skills can reference other skills** — cross-referencing is common
6. **Git history analysis is the core technique** — commit patterns, file co-changes, folder structure
7. **Instincts are atomic** — one trigger, one action, with confidence scoring
8. **Skills are compound** — multiple related patterns grouped together

## How to Use for Extracting Learnings from Repos

To use `/skill-create` on a collection of repos:

1. **Clone each repo**
2. **Run `/skill-create`** in each repo (or manually replicate the git analysis steps)
3. **Collect the generated SKILL.md files**
4. **Optionally merge** related skills across repos
5. **Install** to `~/.claude/skills/` (user-level) or `.claude/skills/` (project-level)

Or, replicate the technique manually:
1. Analyze git log for patterns
2. Identify folder structures and naming conventions
3. Find co-change patterns (files that always change together)
4. Detect workflow sequences
5. Write a SKILL.md following the format above
