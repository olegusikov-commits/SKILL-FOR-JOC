"""גישה לנתונים (SQLite בהדגמה; בייצור — SQL Server דרך אותו ממשק)."""
import sqlite3
from contextlib import closing

from .models import Account, Cheque, Decision, Payer


class ChequeRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def load(self, cheque_id: int):
        with closing(self._connect()) as conn:
            row = conn.execute(
                """SELECT c.cheque_id, c.received_at, c.branch_id, c.account_id, c.payer_id,
                          c.channel, c.ocr_amount, c.ocr_amount_conf, c.ocr_date_conf,
                          c.ocr_signature_score, c.payer_prev_cheques, c.is_duplicate_suspect,
                          a.status, a.segment, p.payer_type, p.bank_code
                   FROM cheques c
                   JOIN accounts a ON a.account_id = c.account_id
                   JOIN payers   p ON p.payer_id   = c.payer_id
                   WHERE c.cheque_id = ?""",
                (cheque_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"cheque {cheque_id} not found")
        cheque = Cheque(
            cheque_id=row["cheque_id"], received_at=row["received_at"],
            branch_id=row["branch_id"], account_id=row["account_id"], payer_id=row["payer_id"],
            channel=row["channel"], ocr_amount=row["ocr_amount"],
            ocr_amount_conf=row["ocr_amount_conf"], ocr_date_conf=row["ocr_date_conf"],
            ocr_signature_score=row["ocr_signature_score"],
            payer_prev_cheques=row["payer_prev_cheques"],
            is_duplicate_suspect=bool(row["is_duplicate_suspect"]),
        )
        account = Account(row["account_id"], row["status"], row["segment"])
        payer = Payer(row["payer_id"], row["payer_type"], row["bank_code"])
        return cheque, account, payer

    def save_decision(self, cheque_id: int, decided_at: str, decision: Decision) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """INSERT INTO auto_decisions (cheque_id, decided_at, result, reason_code)
                   VALUES (?, ?, ?, ?)""",
                (cheque_id, decided_at, decision.result, decision.reason_code),
            )
