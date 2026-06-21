---
name: example-skill
description: Template skill — REPLACE THIS. Write a clear, specific description of WHEN this skill should be used (the triggers), since Claude reads this line to decide relevance. e.g. "Use when the user wants to add a new API endpoint to the FastAPI backend."
---

# Example Skill

This file is a template. Replace its contents with your skill's instructions.

## How skills work

- The folder name (`example-skill`) is the skill's identifier. Invoke it as `/example-skill`.
- The `description` in the frontmatter is what Claude uses to decide when the skill is relevant — make it specific and trigger-oriented.
- Everything below the frontmatter is the instruction body Claude follows when the skill runs.

## What to put here

Write step-by-step instructions, conventions, checklists, or domain knowledge for a
repeatable task. For example, a skill for this project might document:

1. The exact steps to add a new backend endpoint (router → schema → wire into `main.py`).
2. Project conventions to follow (async SQLAlchemy, ownership checks via `get_owned_page`).
3. How to verify the change (byte-compile, `tsc --noEmit`, rebuild).

## Bundling files

You can place helper scripts or reference docs in this folder and point to them, e.g.
"run `scripts/seed.py`" or "follow the checklist in `checklist.md`". Reference them by
relative path from this skill folder.
