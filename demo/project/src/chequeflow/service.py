"""נקודת הכניסה: עיבוד שיק שהתקבל מה-OCR."""
from datetime import datetime, timezone

from . import rules
from .models import Decision
from .repository import ChequeRepository


def process_cheque(repo: ChequeRepository, cheque_id: int) -> Decision:
    cheque, account, payer = repo.load(cheque_id)
    decision = rules.decide(cheque, account, payer)
    repo.save_decision(cheque_id, datetime.now(timezone.utc).isoformat(), decision)
    return decision
