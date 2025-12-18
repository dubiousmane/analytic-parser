import pdfplumber
import logging
from datetime import datetime
from decimal import Decimal
import re

from config import (
    DATE_START_RE, TX_HEAD_RE, KNOWN_OPERATIONS
)
from cleaner import clean_description

logger = logging.getLogger(__name__)


def parse_pdf(path: str) -> list[dict]:
    txs = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            txs.extend(_parse_page(lines))

    return txs


def _parse_page(lines: list[str]) -> list[dict]:
    txs = []
    current = None

    def flush():
        nonlocal current
        if current:
            current["description"] = clean_description(current["description"])
            txs.append(current)
            current = None

    for line in lines:
        if DATE_START_RE.match(line):
            flush()
            head = _parse_head(line)
            if head:
                current = head
            continue

        if current:
            current["description"] += " " + line

    flush()
    return txs


def _parse_head(line: str) -> dict | None:
    m = TX_HEAD_RE.match(line)
    if not m:
        return None

    date = datetime.strptime(m.group("date"), "%d.%m.%Y")

    raw_amount = m.group("amount")
    amount = _to_decimal(raw_amount)
    if raw_amount.startswith(("−", "-")):
        amount = -abs(amount)

    op = m.group("operation").capitalize()
    if op not in KNOWN_OPERATIONS:
        op = "Покупка"

    return {
        "date": date,
        "amount": amount,
        "currency": m.group("currency"),
        "operation": op,
        "description": m.group("details") or "",
        "direction": "expense",
        "transfer_type": None,
    }


def _to_decimal(v: str) -> Decimal:
    v = v.replace("−", "-").replace(" ", "")
    if "." in v and "," in v:
        v = v.replace(",", "")
    else:
        v = v.replace(",", ".")
    v = re.sub(r"[^0-9\.\-]", "", v)
    return Decimal(v or "0")
