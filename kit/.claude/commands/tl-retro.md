---
description: Learning — the kit looks back at its work in this project (its mistakes, the user's corrections, terms, style, habits, repeated procedures) and proposes lessons, glossary terms, profile items and project skills; the user approves each; also show / forget / share the glossary
argument-hint: "[empty: review observations] | show [kit] | term <word> | forget <L-nnn or item> | share"
---

Learning in this project. User input: $ARGUMENTS

Formats, rules and budgets: `.claude/tech-lead-kit/LEARNING.md` — read it first. Tool:
`python .claude/tech-lead-kit/scripts/tl_learn.py` (or `py -3 …`). The memory changes only after the
user's yes (or an explicit "remember …"); CORE always wins over a lesson.

**No arguments — review:**
1. **Collect.** Run `tl_learn.py harvest`, then read the new (`[ ]`) lines of
   `.claude/tl-memory/learn/INBOX.md`, all of `LESSONS.md` (the rejected ones too), `PROFILE.md`, the
   glossary (`GLOSSARY.md` in `learn/`, or its published copy listed in `KNOWLEDGE.md`) and the project
   skills `.claude/skills/tlp-*/SKILL.md`. Run `tl_learn.py lint` for stale, duplicate or over-budget items.
2. **Group and filter.** Observations with one cause become one proposal with evidence ("видели 3×",
   dates). Drop and tick `[x]`: one-off details of a single task, what a spec, ADR, `PROJECT_CONTEXT.md` or
   CORE already says, what repeats a `rejected` lesson without new evidence, what would weaken CORE.
3. **Propose** at most 8, the most useful first (how often × how much it changes the result):
   - **lesson** (scope · when · rule · why) — the kit's mistakes and the user's corrections;
   - **term** — glossary row; check the meaning in code / data first (`tl-researcher` if wider than ~5 files);
   - **profile** — style, a habit, a standing answer to a question the kit keeps asking;
   - **project skill** `tlp-<slug>` — only for work seen ≥ 3 times with the same steps; show its
     description and steps;
   - **kit** — a problem of the kit itself: a lesson with scope `kit` (a workaround here, and a note
     for the kit author, shown by `show kit`);
   - **retire / merge** — what lint marked stale or duplicate, or what exceeds a budget.
   Two lessons that conflict in one scope are shown together; the user picks.
4. **Ask** with buttons (KIT_GUIDE "Questions"): one question per proposal, up to 4 per call, at most
   2 calls; options "Принять (рекомендуется)" / "Отклонить", and the user can type a changed wording.
   Reply length, format and chat language the user asked for directly are applied without a question
   and listed in the report. What did not fit stays `[ ]` for the next round.
5. **Write.** Accepted lesson → next `L-nnn`, `active`; rejected → `rejected` with the reason (it is
   knowledge); term → glossary row; profile → item in its section; project skill → `.claude/skills/tlp-<slug>/SKILL.md`
   from `.claude/tech-lead-kit/templates/project-skill.md`; retired → `retired`. Tick every handled INBOX
   line `[x]`. Then `tl_learn.py render`, `tl_learn.py lint` (fix every ERROR) and
   `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.
6. **Report** in Russian: accepted, rejected, applied without a question, left for later, kit notes for
   the author; a new project skill works from the next session.

**Modes:**
- `show` — what the kit knows here, from `ACTIVE.md` plus counts (lessons, terms, profile, skills, waiting
  observations). `show kit` — the lessons with scope `kit` as a list the user can pass to the kit author.
- `term <word> [= meaning]` — find where the word lives in code and data, propose the row, write after yes.
- `forget <L-nnn | term | profile item | tlp-name>` — show what goes, then: lesson → `retired`, term or
  item → removed, project skill → moved to `.claude/tl-memory/skills-disabled/`; `render`.
- `share` — publish the glossary for the team: `tl_knowledge.py check` then `tl_knowledge.py publish` on
  its file (Hebrew, no `.claude/` paths, no kit commands). Lessons and the profile are never published:
  they are about the kit and the person. Team facts belong in the `tl-agents` block of `PROJECT_CONTEXT.md`.

End with the step card.
