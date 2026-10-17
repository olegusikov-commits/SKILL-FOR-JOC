"""כללי ההחלטה האוטומטית: לאשר שיק אוטומטית או להעביר לפקיד.

סדר הבדיקות חשוב: הבדיקה הראשונה שנכשלת קובעת את קוד הסיבה.
"""
from . import config
from .models import Account, Cheque, Decision, Payer

AUTO_APPROVED = "AUTO_APPROVED"
TO_CLERK = "TO_CLERK"


def decide(cheque: Cheque, account: Account, payer: Payer) -> Decision:
    # עצירות קשיחות: אסור לאשר אוטומטית בשום מקרה
    if account.status != "ACTIVE":
        return Decision(TO_CLERK, "ACCOUNT_BLOCKED")
    if cheque.is_duplicate_suspect:
        return Decision(TO_CLERK, "DUPLICATE_SUSPECT")

    if cheque.channel not in config.AUTO_APPROVE_CHANNELS:
        return Decision(TO_CLERK, "CHANNEL_NOT_ALLOWED")
    if cheque.ocr_amount > config.AUTO_APPROVE_MAX_AMOUNT:
        return Decision(TO_CLERK, "AMOUNT_LIMIT")
    if cheque.ocr_amount_conf < config.OCR_AMOUNT_MIN_CONF:
        return Decision(TO_CLERK, "LOW_OCR_AMOUNT")
    if cheque.ocr_date_conf < config.OCR_DATE_MIN_CONF:
        return Decision(TO_CLERK, "LOW_OCR_DATE")
    if cheque.ocr_signature_score < config.SIGNATURE_MIN_SCORE:
        return Decision(TO_CLERK, "LOW_SIGNATURE")
    if cheque.payer_prev_cheques < config.MIN_PAYER_HISTORY:
        return Decision(TO_CLERK, "NEW_PAYER")

    return Decision(AUTO_APPROVED, "OK")
