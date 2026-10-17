#!/usr/bin/env python3
"""Compute the reference ("true") answers for the demo from the generated chequemis.db.

The analyst never sees this file. Its output is what the analyst's numbers are scored against
(see EXPECTED.md). Error definition used here (the one the analyst should arrive at):
the LAST clerk review is final; error = REJECTED, or APPROVED with corrected_amount.

Usage: python reference_answers.py PATH/TO/chequemis.db
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "kit", ".claude", "skills", "tl-analytics", "scripts"))
from an_stats import stability, verdict  # noqa: E402

BASE = """
WITH last_review AS (
    SELECT r.* FROM clerk_reviews r
    WHERE r.review_id = (SELECT MAX(r2.review_id) FROM clerk_reviews r2 WHERE r2.cheque_id = r.cheque_id)
),
base AS (
    SELECT c.*, substr(c.received_at, 1, 7) AS month, a.status, a.segment, a.branch_id AS acc_branch,
           p.payer_type, p.bank_code, d.result, d.reason_code,
           lr.decision, lr.corrected_amount, lr.is_spot_check,
           CASE WHEN lr.decision = 'REJECTED' THEN 1 ELSE 0 END AS is_reject,
           CASE WHEN lr.decision = 'REJECTED' OR lr.corrected_amount IS NOT NULL THEN 1 ELSE 0 END AS is_err
    FROM cheques c
    JOIN accounts a ON a.account_id = c.account_id
    JOIN payers p ON p.payer_id = c.payer_id
    JOIN auto_decisions d ON d.cheque_id = c.cheque_id
    LEFT JOIN last_review lr ON lr.cheque_id = c.cheque_id
    WHERE c.received_at >= '{start}' AND c.received_at < '2026-10-01'
)
"""

HARD = "status = 'ACTIVE' AND is_duplicate_suspect = 0"
SOFT = {
    "channel": "channel IN ('BRANCH_SCAN','ATM')",
    "amount": "ocr_amount <= 1000",
    "ocr": "ocr_amount_conf >= 0.95",
    "date": "ocr_date_conf >= 0.90",
    "sig": "ocr_signature_score >= 0.85",
    "payer": "payer_prev_cheques >= 3",
}


def soft_except(*names, **replace):
    parts = [replace.get(k, v) for k, v in SOFT.items() if k not in names or k in replace]
    return " AND ".join(parts)


RULES = {
    "R1 recurring COMPANY/GOV (prev>=6), amount<=5000, non-mobile":
        f"payer_type IN ('COMPANY','GOVERNMENT') AND payer_prev_cheques >= 6 AND ocr_amount <= 5000 AND "
        f"{soft_except('amount', 'payer')}",
    "R2 GOVERNMENT prev>=1, amount<=5000, non-mobile":
        f"payer_type = 'GOVERNMENT' AND payer_prev_cheques >= 1 AND ocr_amount <= 5000 AND "
        f"{soft_except('amount', 'payer')}",
    "R1 + allow MOBILE (trap)":
        f"payer_type IN ('COMPANY','GOVERNMENT') AND payer_prev_cheques >= 6 AND ocr_amount <= 5000 AND "
        f"{soft_except('amount', 'payer', 'channel')}",
    "MOBILE relax for otherwise passing (trap: FAIL)": soft_except("channel"),
    "OCR amount conf relax to 0.90 (fails only with corrections)":
        soft_except("ocr") + " AND ocr_amount_conf >= 0.90",
    "PRIVATE amount limit 1000 -> 3000 (FAIL)":
        f"payer_type = 'PRIVATE' AND ocr_amount <= 3000 AND {soft_except('amount')}",
    "COMPANY prev>=1, amount<=5000 (unstable: Aug, bank 010)":
        f"payer_type = 'COMPANY' AND payer_prev_cheques >= 1 AND ocr_amount <= 5000 AND "
        f"{soft_except('amount', 'payer')}",
    "risk_flag = 'OK' (LEAKAGE — must be rejected)": "risk_flag = 'OK'",
    "CHQ-512 as written in the patch (before hard stops, no channel check, prev>6)":
        "payer_type IN ('COMPANY','GOVERNMENT') AND payer_prev_cheques > 6 AND ocr_amount <= 5000 AND "
        "ocr_amount_conf >= 0.95 AND ocr_date_conf >= 0.90 AND ocr_signature_score >= 0.85",
    "CHQ-512 as the task requires (= R1)":
        f"{HARD} AND payer_type IN ('COMPANY','GOVERNMENT') AND payer_prev_cheques >= 6 AND ocr_amount <= 5000 AND "
        f"{soft_except('amount', 'payer')}",
}


def run_rule(db, start, predicate, hard=True):
    cond = f"({HARD}) AND ({predicate})" if hard else f"({predicate})"
    rows = db.execute(BASE.format(start=start) + f"""
        SELECT month, COUNT(*) AS n_all,
               SUM(CASE WHEN result <> 'AUTO_APPROVED' AND decision IS NOT NULL AND {cond} THEN 1 ELSE 0 END),
               SUM(CASE WHEN result <> 'AUTO_APPROVED' AND decision IS NOT NULL AND {cond} THEN is_err ELSE 0 END),
               SUM(CASE WHEN result <> 'AUTO_APPROVED' AND decision IS NOT NULL AND {cond} THEN is_reject ELSE 0 END)
        FROM base GROUP BY month ORDER BY month""").fetchall()
    return rows


def report(db, title, start, predicate, hard=True):
    rows = run_rule(db, start, predicate, hard)
    n_all = sum(r[1] for r in rows)
    n_new = sum(r[2] for r in rows)
    k_err = sum(r[3] for r in rows)
    k_rej = sum(r[4] for r in rows)
    v = verdict(k_err, n_new, 0.02)
    v_rej = verdict(k_rej, n_new, 0.02)
    st = stability([(r[0], r[2], r[3]) for r in rows], 0.02)
    gain = 100.0 * n_new / n_all if n_all else 0
    stab = "stable" if st["stable"] else "UNSTABLE " + ",".join(st["unstable_periods"])
    if st["watch_periods"]:
        stab += " watch " + ",".join(st["watch_periods"])
    print(f"- {title}\n    gain +{gain:.2f} p.p. (n_new={n_new}); error {k_err}/{n_new} "
          f"point={100 * (v['point'] or 0):.2f}% upper={100 * v['upper']:.2f}% → {v['verdict']}; "
          f"reject-only upper={100 * v_rej['upper']:.2f}% → {v_rej['verdict']}; "
          f"{stab}")


def main():
    db = sqlite3.connect(sys.argv[1])
    print("## Baseline (automatic approval share)")
    for start, label in (("2026-01-01", "Jan–Sep (incl. old OCR)"), ("2026-04-01", "Apr–Sep (after OCR switch)")):
        n, k = db.execute(BASE.format(start=start) + "SELECT COUNT(*), SUM(result='AUTO_APPROVED') FROM base").fetchone()
        print(f"- {label}: {k}/{n} = {100 * k / n:.2f}%")
    n_rows, n_obj = db.execute("""SELECT COUNT(*), COUNT(DISTINCT c.cheque_id) FROM cheques c
                                   JOIN clerk_reviews r ON r.cheque_id = c.cheque_id""").fetchone()
    print(f"- join cheques×clerk_reviews: {n_rows} rows for {n_obj} cheques (duplicates = {n_rows - n_obj})")
    n_all, could = db.execute(BASE.format(start="2026-04-01") + """
        SELECT COUNT(*), SUM(CASE WHEN result <> 'AUTO_APPROVED' AND decision IS NOT NULL AND is_err = 0
                                  THEN 1 ELSE 0 END) FROM base""").fetchone()
    print(f"- ceiling Apr–Sep: {could}/{n_all} = {100 * could / n_all:.1f}% approved by clerk without correction")
    spot = db.execute(BASE.format(start="2026-04-01") + """
        SELECT COUNT(*), SUM(is_err) FROM base WHERE result = 'AUTO_APPROVED' AND is_spot_check = 1""").fetchone()
    print(f"- spot checks of current automatic approvals Apr–Sep: {spot[1]}/{spot[0]} errors")

    for start, label in (("2026-07-01", "Period B (Jul–Sep)"), ("2026-04-01", "Apr–Sep")):
        print(f"\n## Rules on {label} (newly automated cheques; hard stops applied unless stated)")
        for title, pred in RULES.items():
            report(db, title, start, pred, hard=not title.startswith("CHQ-512"))
        union = " OR ".join(f"({RULES[t]})" for t in list(RULES)[:2])
        report(db, "UNION R1 ∪ R2", start, union)


if __name__ == "__main__":
    main()
