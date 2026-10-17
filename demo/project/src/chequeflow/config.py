"""ספי ההחלטה האוטומטית לאישור שיקים."""

# סכום מקסימלי (₪) לאישור אוטומטי
AUTO_APPROVE_MAX_AMOUNT = 1000.0

# ביטחון מינימלי של OCR בזיהוי הסכום
OCR_AMOUNT_MIN_CONF = 0.95

# ביטחון מינימלי של OCR בזיהוי התאריך
OCR_DATE_MIN_CONF = 0.90

# ציון מינימלי של התאמת חתימה
SIGNATURE_MIN_SCORE = 0.85

# מספר מינימלי של שיקים קודמים מאותו מושך לאותו חשבון
MIN_PAYER_HISTORY = 3

# ערוצים שמהם מותר אישור אוטומטי (MOBILE לא מותר — איכות סריקה נמוכה)
AUTO_APPROVE_CHANNELS = frozenset({"BRANCH_SCAN", "ATM"})

DB_PATH = "chequemis.db"
