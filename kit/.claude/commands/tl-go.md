---
description: Navigator — say what you want in your own words (or nothing) and get the right route; shows unfinished work and the next step; "new <request>" runs the whole FLOW of a new task with stops only for approval
argument-hint: "[what you want, in your words] | new <request> | (empty: where am I)"
disable-model-invocation: true
---

Navigator. User input: $ARGUMENTS

You choose and start kit routes; you never write production code yourself here — the route you
start does, under its own rules. Routes, depth levels, FLOW, questions and the step card:
KIT_GUIDE (already in your context).

1. **Where we are.** Run `python .claude/tech-lead-kit/scripts/tl_knowledge.py status`
   (`py -3 …` on Windows if `python` is missing). It lists open task flows with their next step,
   documents waiting for approval, plans with open tasks, and "kit updated → /tl-init".

2. **No arguments** → show that list in 3–8 short lines, then ask with AskUserQuestion (no tool →
   numbered text) which next step to take: 2–4 options from the list, the most useful first with
   "(рекомендуется)". Kit updated or no `PROJECT_CONTEXT.md` → `/tl-init` is the first option.
   Run the chosen one (step 5).

3. **A request in words** → classify it with the routes table:
   - read `.claude/tl-memory/KNOWLEDGE.md` — an approved spec or a design for this area changes
     the answer (e.g. "build X" with an approved SPEC → `/tl-implement SPEC-nnn`, not a new spec);
   - choose **the smallest route that safely closes it**; risk, an unclear goal or a wide reach
     move it one step up (code → design → requirement);
   - propose 1–3 options (a route, or a chain such as "requirement → code"), each with one line
     "why" and the level (`mvp` / `standard` / `full`), via AskUserQuestion — your recommendation
     first. One clear match for a small task → say it in one line and start it without asking.

4. **`new <request>`** — the FLOW of a new task (KIT_GUIDE "FLOW"):
   - ask once, together (one AskUserQuestion call): the level (`mvp` recommended for something new,
     `full` when money, decision rules or PROD data are involved) and, if the request is ambiguous
     between routes, the route;
   - start the requirement: read `.claude/commands/tl-spec.md` and follow its mode `new` with the
     request text and the chosen level (it creates `REQUEST.md` + `FLOW.md`); tick stage 0 in the new
     `FLOW.md`. Then the next stages in order, each by reading and following its command file with
     the task id: `tl-design.md` (LARGE and level is not `mvp`), `tl-implement.md`, `tl-review.md`.
     **Stop at every gate** (approval of `SPEC.md`, of the design; the review choice) and end with
     the step card.
   - next session: `/tl-go` (no args) finds the open `FLOW.md` and continues from its `Дальше:` line.

5. **Start the route:** Read `.claude/commands/<route>.md` and follow it exactly with the user's
   words (or the task id) as `$ARGUMENTS`. Tell the user in one line which route runs and that next
   time they can call it directly.

Every reply ends with the step card.
