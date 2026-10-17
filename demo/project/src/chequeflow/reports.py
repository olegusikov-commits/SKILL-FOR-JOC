import sqlite3


def daily_report(db_path, day):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT c.cheque_id, c.branch_id, c.channel, c.ocr_amount, c.ocr_amount_conf, "
        "d.result, d.reason_code FROM cheques c JOIN auto_decisions d ON d.cheque_id = c.cheque_id "
        "WHERE substr(c.received_at, 1, 10) = '" + day + "'"
    ).fetchall()
    total = 0
    auto = 0
    big = 0
    low_conf = 0
    by_branch = {}
    for r in rows:
        total += 1
        if r[5] == "AUTO_APPROVED":
            auto += 1
        if r[3] > 1000:
            big += 1
        if r[4] < 0.9:
            low_conf += 1
        if r[1] not in by_branch:
            by_branch[r[1]] = [0, 0]
        by_branch[r[1]][0] += 1
        if r[5] == "AUTO_APPROVED":
            by_branch[r[1]][1] += 1
    lines = []
    lines.append("Daily report " + day)
    lines.append("total: " + str(total))
    lines.append("auto: " + str(auto))
    if total > 0:
        lines.append("auto %: " + str(round(auto * 100.0 / total, 2)))
    lines.append("over limit: " + str(big))
    lines.append("low OCR: " + str(low_conf))
    for b in by_branch:
        t, a = by_branch[b]
        try:
            lines.append(b + ": " + str(t) + " / " + str(a) + " = " + str(round(a * 100.0 / t, 1)) + "%")
        except Exception:
            pass
    conn.close()
    return "\n".join(lines)


def weekly_report(db_path, days):
    out = []
    for d in days:
        out.append(daily_report(db_path, d))
    return "\n\n".join(out)
