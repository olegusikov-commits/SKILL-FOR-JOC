#!/usr/bin/env python3
"""Generate the demo data for the ChequeFlow demo project.

Creates in TARGET (a copy of demo/project):
  chequemis.db   — cheques, automatic decisions, clerk reviews (with planted patterns)
  checkov.db     — clerks and an audit log (second MCP server)
  docs/process.docx — business process description in Hebrew

The planted patterns and the expected analyst findings are documented in demo/EXPECTED.md.
This file must NOT be copied into the project the analyst sees.

Usage: python make_demo.py TARGET [--seed 7] [--per-month 4000]
"""
import argparse
import os
import random
import sqlite3
import sys
import zipfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "project", "src"))
from chequeflow.models import Account, Cheque, Payer  # noqa: E402
from chequeflow.rules import decide  # noqa: E402

MONTHS = [(2026, m) for m in range(1, 10)]          # Jan..Sep 2026
OCR_SWITCH = datetime(2026, 4, 1)                   # OCR v2 -> v3
FRAUD_MONTH = (2026, 8)                             # fraud wave: COMPANY payers of bank 010
BANKS = ["010", "011", "012", "020", "031", "054"]


def schema_sql():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project", "sql", "schema.sql")
    with open(path, encoding="utf-8") as f:
        return f.read()


def clamp(x, lo=0.0, hi=0.999):
    return max(lo, min(hi, x))


def conf_value(rng, channel, v3):
    """OCR amount confidence; mobile scans are worse."""
    u = rng.random()
    if channel == "MOBILE":
        u -= 0.15
    if u < 0.15:
        return round(rng.uniform(0.60, 0.90), 3)
    if u < 0.32:
        return round(rng.uniform(0.90, 0.95), 3)
    return round(rng.uniform(0.95, 0.999), 3)


def reject_probability(payer, prev, cheque, account, month):
    if account.status != "ACTIVE":
        return 0.60
    if cheque.is_duplicate_suspect:
        return 0.50
    t = payer.payer_type
    if t == "PRIVATE":
        r = 0.08 if prev == 0 else 0.04 if prev < 3 else 0.012 if prev < 6 else 0.006
    elif t == "COMPANY":
        r = 0.03 if prev == 0 else 0.008 if prev < 6 else 0.002
    else:  # GOVERNMENT
        r = 0.01 if prev == 0 else 0.002
    if cheque.ocr_signature_score < 0.85:
        r += 0.10
    if cheque.ocr_date_conf < 0.90:
        r += 0.03
    if cheque.channel == "MOBILE":
        r += 0.025
    if t == "PRIVATE" and cheque.ocr_amount > 1000:
        r += 0.015
    if cheque.ocr_amount > 5000:
        r += 0.02
    if (month == FRAUD_MONTH and t == "COMPANY" and payer.bank_code == "010" and prev < 6):
        r += 0.20
    return min(r, 0.95)


def correction_probability(conf, v3):
    if v3:
        return 0.003 if conf >= 0.95 else 0.02 if conf >= 0.90 else 0.12
    return 0.02 if conf >= 0.95 else 0.05 if conf >= 0.90 else 0.15


def build_chequemis(path, rng, per_month):
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript(schema_sql())

    branches = [(f"B{i:02d}", f"סניף {i}", rng.choice(["צפון", "מרכז", "דרום", "ירושלים"]))
                for i in range(1, 21)]
    db.executemany("INSERT INTO branches VALUES (?,?,?)", branches)

    accounts = []
    for aid in range(1, 8001):
        branch = rng.choice(branches)[0]
        opened = datetime(2010, 1, 1) + timedelta(days=rng.randint(0, 5800))
        segment = "business" if rng.random() < 0.2 else "private"
        u = rng.random()
        status = "BLOCKED" if u < 0.03 else "CLOSED" if u < 0.04 else "ACTIVE"
        accounts.append(Account(aid, status, segment))
        db.execute("INSERT INTO accounts VALUES (?,?,?,?,?)",
                   (aid, branch, opened.date().isoformat(), segment, status))

    payers = []
    for pid in range(1, 3001):
        u = rng.random()
        ptype = "PRIVATE" if u < 0.62 else "COMPANY" if u < 0.90 else "GOVERNMENT"
        payers.append(Payer(pid, ptype, rng.choice(BANKS)))
    db.executemany("INSERT INTO payers VALUES (?,?,?)",
                   [(p.payer_id, p.payer_type, p.bank_code) for p in payers])
    account_branch = dict(db.execute("SELECT account_id, branch_id FROM accounts").fetchall())

    cheque_id, review_id = 0, 0
    for (year, month) in MONTHS:
        start = datetime(year, month, 1)
        end = datetime(year + (month == 12), month % 12 + 1, 1)
        seconds = int((end - start).total_seconds())
        stamps = sorted(start + timedelta(seconds=rng.randint(0, seconds - 1)) for _ in range(per_month))
        for ts in stamps:
            cheque_id += 1
            v3 = ts >= OCR_SWITCH
            payer = rng.choice(payers)
            account = rng.choice(accounts)
            u = rng.random()
            channel = "BRANCH_SCAN" if u < 0.50 else "MOBILE" if u < 0.80 else "ATM"
            if payer.payer_type == "PRIVATE":
                prev = min(int(rng.expovariate(1 / 4.0)), 40)
                amount = round(min(rng.lognormvariate(6.3, 0.8), 60000), 2)
            elif payer.payer_type == "COMPANY":
                prev = 0 if rng.random() < 0.15 else rng.randint(1, 5) if rng.random() < 0.35 else rng.randint(6, 30)
                amount = round(min(rng.lognormvariate(7.9, 0.5), 60000), 2)
            else:
                prev = 0 if rng.random() < 0.10 else rng.randint(1, 24)
                amount = round(min(rng.lognormvariate(7.6, 0.45), 60000), 2)
            conf = conf_value(rng, channel, v3)
            if not v3:  # OCR v2 was over-confident
                conf = round(clamp(conf + 0.02), 3)
            date_conf = round(rng.uniform(0.70, 0.90) if rng.random() < 0.12 else rng.uniform(0.90, 0.999), 3)
            signature = round(rng.uniform(0.50, 0.85) if rng.random() < 0.15 else rng.uniform(0.85, 0.999), 3)
            duplicate = rng.random() < 0.015
            cheque = Cheque(cheque_id, ts.isoformat(timespec="seconds"), account_branch[account.account_id],
                            account.account_id, payer.payer_id, channel, amount, conf, date_conf,
                            signature, prev, duplicate)
            decision = decide(cheque, account, payer)

            reviews = []
            reviewed = decision.result == "TO_CLERK" or rng.random() < 0.03
            if reviewed:
                p_rej = reject_probability(payer, prev, cheque, account, (year, month))
                rejected = rng.random() < p_rej
                corrected = None
                if not rejected and rng.random() < correction_probability(conf, v3):
                    corrected = round(amount * rng.choice([0.1, 10, 0.9, 1.1, 1.01]), 2)
                rtime = ts + timedelta(hours=rng.randint(1, 30))
                reviews.append((rtime, "REJECTED" if rejected else "APPROVED", corrected,
                                rng.choice(["SIGNATURE", "FUNDS", "FRAUD", "DATE", "OTHER"]) if rejected else None,
                                0 if decision.result == "TO_CLERK" else 1))
                # supervisor re-review for some cheques: the LAST review is the final decision
                if decision.result == "TO_CLERK" and rng.random() < 0.015:
                    flip = rng.random() < 0.2
                    final_rej = (not rejected) if flip else rejected
                    reviews.append((rtime + timedelta(hours=rng.randint(2, 48)),
                                    "REJECTED" if final_rej else "APPROVED", corrected,
                                    "FRAUD" if final_rej else None, 0))
            final = reviews[-1][1] if reviews else None
            if final is None:
                risk_flag = None
            elif final == "REJECTED":
                risk_flag = "SUSPICIOUS" if rng.random() < 0.9 else "OK"
            else:
                risk_flag = "SUSPICIOUS" if rng.random() < 0.02 else "OK"

            db.execute(
                "INSERT INTO cheques VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cheque_id, cheque.received_at, cheque.branch_id, account.account_id, payer.payer_id,
                 channel, "v3.1" if v3 else "v2.4", amount, conf, date_conf, signature, prev,
                 int(duplicate), risk_flag))
            db.execute("INSERT INTO auto_decisions VALUES (?,?,?,?)",
                       (cheque_id, (ts + timedelta(seconds=rng.randint(2, 40))).isoformat(timespec="seconds"),
                        decision.result, decision.reason_code))
            for rtime, dec, corr, reason, spot in reviews:
                review_id += 1
                db.execute("INSERT INTO clerk_reviews VALUES (?,?,?,?,?,?,?,?)",
                           (review_id, cheque_id, rtime.isoformat(timespec="seconds"),
                            rng.randint(1, 40), dec, corr, reason, spot))
    db.commit()
    db.close()


def build_checkov(path, rng):
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE clerks (clerk_id INTEGER PRIMARY KEY, full_name TEXT NOT NULL,
                             team TEXT NOT NULL, is_supervisor INTEGER NOT NULL);
        CREATE TABLE audit_log (log_id INTEGER PRIMARY KEY, logged_at TEXT NOT NULL,
                                clerk_id INTEGER NOT NULL, action TEXT NOT NULL, cheque_id INTEGER);
        CREATE INDEX ix_audit_log_logged_at ON audit_log(logged_at);
    """)
    for cid in range(1, 41):
        db.execute("INSERT INTO clerks VALUES (?,?,?,?)",
                   (cid, f"פקיד {cid}", rng.choice(["צוות א", "צוות ב", "צוות ג"]), int(cid <= 4)))
    for lid in range(1, 2001):
        db.execute("INSERT INTO audit_log VALUES (?,?,?,?,?)",
                   (lid, (datetime(2026, 9, 1) + timedelta(minutes=lid * 13)).isoformat(timespec="seconds"),
                    rng.randint(1, 40), rng.choice(["LOGIN", "VIEW", "APPROVE", "REJECT"]),
                    rng.randint(1, 36000)))
    db.commit()
    db.close()


# ---------------------------------------------------------------- docx (Hebrew, RTL)
PROCESS_DOC = [
    ("h1", "תהליך אישור שיקים — ChequeFlow"),
    ("p", "מסמך זה מתאר את תהליך הטיפול בשיקים שמופקדים בסניפים, באפליקציה (MOBILE) ובכספומטים."),
    ("h2", "שלבי התהליך"),
    ("p", "1. השיק נסרק. מנוע ה-OCR מזהה סכום, תאריך וחתימה ומחזיר רמת ביטחון לכל שדה."),
    ("p", "2. בעת קבלת השיק המערכת מחשבת את מספר השיקים הקודמים מאותו מושך לאותו חשבון "
          "(payer_prev_cheques) ובודקת חשד לכפילות."),
    ("p", "3. כללי ההחלטה האוטומטית מאשרים את השיק או מעבירים אותו לבדיקת פקיד."),
    ("p", "4. הפקיד בודק את השיק: מאשר, מאשר לאחר תיקון סכום (corrected_amount), או דוחה. "
          "בזמן הבדיקה הפקיד מסמן גם את דגל הסיכון risk_flag בטבלת השיקים."),
    ("p", "5. במקרים מסוימים מפקח מבצע בדיקה חוזרת. במקרה כזה ההחלטה האחרונה היא הקובעת."),
    ("p", "6. מדגם של כ-3% מהשיקים שאושרו אוטומטית נבדק בדיעבד על ידי פקיד (is_spot_check = 1)."),
    ("h2", "מצב נוכחי"),
    ("p", "כיום כ-8% מהשיקים מאושרים אוטומטית. כל השאר עוברים לפקיד, וזה עומס גדול על הצוות."),
    ("p", "ב-1 באפריל 2026 הוחלף מנוע ה-OCR לגרסה v3.1. לגרסה הקודמת (v2.4) היו רמות ביטחון "
          "גבוהות מדי ביחס לאיכות הזיהוי בפועל."),
    ("p", "ניסיון הצוות: שיקים של מעסיקים וגופים ממשלתיים (משכורות, קצבאות) כמעט אף פעם לא נדחים. "
          "שיקים שנסרקו באפליקציה בעייתיים יותר בגלל איכות הצילום."),
    ("h2", "קודי סיבה"),
    ("table", [["קוד", "משמעות"],
               ["ACCOUNT_BLOCKED", "החשבון חסום או סגור — עצירה קשיחה"],
               ["DUPLICATE_SUSPECT", "חשד לכפילות — עצירה קשיחה"],
               ["CHANNEL_NOT_ALLOWED", "ערוץ שאינו מאושר לאישור אוטומטי (MOBILE)"],
               ["AMOUNT_LIMIT", "הסכום מעל 1,000 ₪"],
               ["LOW_OCR_AMOUNT", "ביטחון נמוך בזיהוי הסכום"],
               ["LOW_OCR_DATE", "ביטחון נמוך בזיהוי התאריך"],
               ["LOW_SIGNATURE", "התאמת חתימה נמוכה"],
               ["NEW_PAYER", "פחות מ-3 שיקים קודמים מהמושך"],
               ["OK", "אושר אוטומטית"]]),
    ("h2", "יעד"),
    ("p", "להגדיל את שיעור האישור האוטומטי, בתנאי ששיעור הטעויות באישורים האוטומטיים החדשים "
          "לא יעלה על 2%."),
]


def _esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _para(text, style=None):
    ppr = "<w:pPr>" + (f'<w:pStyle w:val="{style}"/>' if style else "") + '<w:bidi/><w:jc w:val="right"/></w:pPr>'
    return f'<w:p>{ppr}<w:r><w:rPr><w:rtl/></w:rPr><w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:p>'


def write_docx(path):
    body = []
    for kind, content in PROCESS_DOC:
        if kind == "h1":
            body.append(_para(content, "Heading1"))
        elif kind == "h2":
            body.append(_para(content, "Heading2"))
        elif kind == "p":
            body.append(_para(content))
        else:
            rows = "".join("<w:tr>" + "".join(f"<w:tc>{_para(c)}</w:tc>" for c in row) + "</w:tr>"
                           for row in content)
            body.append(f'<w:tbl><w:tblPr><w:bidiVisual/></w:tblPr>{rows}</w:tbl>')
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f'<w:body>{"".join(body)}</w:body></w:document>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style>'
              '</w:styles>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", doc_rels)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--per-month", type=int, default=4000)
    args = ap.parse_args(argv)
    rng = random.Random(args.seed)
    os.makedirs(os.path.join(args.target, "docs"), exist_ok=True)
    build_chequemis(os.path.join(args.target, "chequemis.db"), rng, args.per_month)
    build_checkov(os.path.join(args.target, "checkov.db"), rng)
    write_docx(os.path.join(args.target, "docs", "process.docx"))
    print(f"demo data written to {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
