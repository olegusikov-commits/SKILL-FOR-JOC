import unittest

from chequeflow.models import Account, Cheque, Payer
from chequeflow.rules import AUTO_APPROVED, TO_CLERK, decide


def make_cheque(**overrides):
    values = dict(
        cheque_id=1, received_at="2026-05-01T10:00:00", branch_id="B01", account_id=10,
        payer_id=20, channel="BRANCH_SCAN", ocr_amount=500.0, ocr_amount_conf=0.99,
        ocr_date_conf=0.99, ocr_signature_score=0.95, payer_prev_cheques=5,
        is_duplicate_suspect=False,
    )
    values.update(overrides)
    return Cheque(**values)


ACTIVE = Account(10, "ACTIVE", "private")
PAYER = Payer(20, "PRIVATE", "010")


class DecideTests(unittest.TestCase):
    def test_good_cheque_is_auto_approved(self):
        self.assertEqual(decide(make_cheque(), ACTIVE, PAYER).result, AUTO_APPROVED)

    def test_blocked_account_goes_to_clerk(self):
        d = decide(make_cheque(), Account(10, "BLOCKED", "private"), PAYER)
        self.assertEqual((d.result, d.reason_code), (TO_CLERK, "ACCOUNT_BLOCKED"))

    def test_amount_over_limit_goes_to_clerk(self):
        d = decide(make_cheque(ocr_amount=1500.0), ACTIVE, PAYER)
        self.assertEqual(d.reason_code, "AMOUNT_LIMIT")

    def test_mobile_channel_goes_to_clerk(self):
        d = decide(make_cheque(channel="MOBILE"), ACTIVE, PAYER)
        self.assertEqual(d.reason_code, "CHANNEL_NOT_ALLOWED")

    def test_new_payer_goes_to_clerk(self):
        d = decide(make_cheque(payer_prev_cheques=0), ACTIVE, PAYER)
        self.assertEqual(d.reason_code, "NEW_PAYER")


if __name__ == "__main__":
    unittest.main()
