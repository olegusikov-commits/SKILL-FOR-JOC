from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Cheque:
    cheque_id: int
    received_at: str
    branch_id: str
    account_id: int
    payer_id: int
    channel: str
    ocr_amount: float
    ocr_amount_conf: float
    ocr_date_conf: float
    ocr_signature_score: float
    payer_prev_cheques: int
    is_duplicate_suspect: bool


@dataclass(frozen=True)
class Account:
    account_id: int
    status: str          # ACTIVE / BLOCKED / CLOSED
    segment: str         # private / business


@dataclass(frozen=True)
class Payer:
    payer_id: int
    payer_type: str      # PRIVATE / COMPANY / GOVERNMENT
    bank_code: str


@dataclass(frozen=True)
class Decision:
    result: str          # AUTO_APPROVED / TO_CLERK
    reason_code: str
    note: Optional[str] = None
