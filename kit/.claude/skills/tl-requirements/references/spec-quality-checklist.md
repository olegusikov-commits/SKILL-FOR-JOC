# Specification quality checklist

Used three ways: the author's self-check before presenting, `/tl-spec check` on someone else's
spec, and the `tl-spec-skeptic` review. Each finding: severity, location (section / row / line),
what is wrong, evidence (code `file:line`, query, document), and the exact fix (replacement text).

## Severities
- **חוסם (BLOCKER)** — a developer following the spec would build something wrong or unsafe:
  contradiction between sections; a rule that bypasses a hard stop or an existing safety check;
  a condition on a field that does not exist, or that is not known at decision time (leakage);
  the spec's own goal is not met on data but the spec says it is; a decision table without an
  "אחרת" row, or with a gap that real data falls into; conflict with an approved spec or an
  accepted ADR that the spec does not acknowledge.
- **מהותי (MAJOR)** — the developer must guess: boundary without inclusive/exclusive or unit;
  undefined business term; requirement that cannot be tested; REQ without AC; data claim that
  does not match the data; a consumer of the data / codes not listed in impact; NULL handling
  missing; an open question that changes behaviour, without a proposed answer.
- **שיפור (MINOR)** — wording, structure, a missing source tag, a missing example.

## Checklist
**Goal and scope**
- [ ] Goal stated with a metric, today's value, the target and how it is measured.
- [ ] Guardrail (what must not get worse) with a number.
- [ ] In scope, out of scope, and **what does not change** — explicit.

**Requirements**
- [ ] Each REQ is one testable statement with a source; type and priority set.
- [ ] Each REQ has at least one AC; each AC names an existing REQ.
- [ ] No vague words without a number — Hebrew: מהיר, בערך, סביר, וכו', וכד', לפי הצורך, במידת
      הצורך, במידת האפשר, בדרך כלל, אמור, גמיש, ידידותי, מספיק, הרבה, קבוע (as a business term),
      ותיק, קטן, גדול; English: fast, reasonable, appropriate, as needed, etc., user-friendly.

**Rules (see `decision-tables.md`)**
- [ ] Every rule is a DT with order, hard stops first, an "אחרת" row.
- [ ] Every threshold: inclusive/exclusive, unit, precision — checked against real values.
- [ ] Every input known at decision time; no field filled after the decision.
- [ ] Values present in data but not named by the table are handled on purpose.
- [ ] As-is table calibrated against actual decisions (agreement ~100%).
- [ ] Row volumes measured; dead rows and a huge "אחרת" explained.

**Data**
- [ ] Every business term → `table.column` (or code / document); "לא נמצא" → question.
- [ ] Every number in the text has a query (Q-n) or a document source; numbers recomputed match.
- [ ] Data changes (columns, codes, config keys) listed, or "אין".

**Impact and operation**
- [ ] Every consumer of changed data, codes or config listed (reports, modules, batch, mainframe,
      documents such as reason-code tables) with what must change.
- [ ] Rollout, monitoring metric with an alert threshold, and rollback.
- [ ] Non-functional needs that matter here (volume, latency, audit, permissions).

**Acceptance and effect**
- [ ] AC cover each DT row, each boundary (on it and just beyond), each hard stop's precedence,
      the "אחרת" row, and missing data.
- [ ] Expected effect measured on history: KPI before / after, guardrail with its bound, verdict,
      stability by month — or the reason it was not measured.

**Consistency**
- [ ] No contradictions between sections (thresholds, codes, scope, numbers).
- [ ] No conflict with approved specs / accepted ADRs in `KNOWLEDGE.md` — or the conflict is
      named and resolved.
- [ ] Assumptions listed with what depends on them; ≤ 5 open questions, each with a proposed
      answer.

## Verdict of a check
- **מוכן לפיתוח** — no BLOCKER, no MAJOR.
- **מוכן אחרי תיקונים** — no BLOCKER; MAJOR findings have exact fixes the author can apply.
- **לא מוכן** — any BLOCKER, or the goal is not achievable as written.
