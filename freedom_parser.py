"""
freedom_parser.py

Парсер PDF-выписок Freedom Bank.
Самый сложный файл из-за кривого PDF-формата.

Особенности:
- Нет нормальных таблиц
- Операции могут быть растянуты на несколько строк
- Используется state-machine подход
"""

import pdfplumber
from datetime import datetime
from decimal import Decimal
import re

from config import DATE_START_RE, TX_HEAD_RE, KNOWN_OPERATIONS
from cleaner import clean_description


def parse_freedom_pdf(path: str) -> list[dict]:
    """
    Основная функция парсинга Freedom PDF.

    Возвращает список транзакций в едином формате.
    """
    transactions: list[dict] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            # Разбиваем страницу на строки
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            transactions.extend(_parse_page(lines))

    # Помечаем источник
    for tx in transactions:
        tx["source"] = "freedom"

    return transactions


def _parse_page(lines: list[str]) -> list[dict]:
    """
    Парсит одну страницу PDF.

    State-machine:
    - строка с датой → начало новой операции
    - остальные строки → продолжение description
    """
    txs: list[dict] = []
    current_tx: dict | None = None

    def flush():
        """
        Завершает текущую операцию и кладёт её в список.
        """
        nonlocal current_tx
        if current_tx:
            current_tx["description"] = clean_description(
                current_tx["description"]
            )
            txs.append(current_tx)
            current_tx = None

    for line in lines:
        # --- новая операция ---
        if DATE_START_RE.match(line):
            flush()
            head = _parse_head_line(line)
            if head:
                current_tx = head
            continue

        # --- продолжение описания ---
        if current_tx:
            current_tx["description"] += " " + line

    flush()
    return txs


def _parse_head_line(line: str) -> dict | None:
    """
    Парсит первую строку операции (заголовок).

    Пример:
    17.12.2025  -500,00 KZT Перевод Безвозмездный перевод
    """
    match = TX_HEAD_RE.match(line)
    if not match:
        return None

    date = datetime.strptime(match.group("date"), "%d.%m.%Y")

    raw_amount = match.group("amount")
    amount = _to_decimal(raw_amount)

    # корректируем знак
    if raw_amount.startswith(("−", "-")):
        amount = -abs(amount)
    else:
        amount = abs(amount)

    # направление операции
    direction = (
        "expense" if amount < 0
        else "income" if amount > 0
        else "neutral"
    )

    operation = match.group("operation").capitalize()
    if operation not in KNOWN_OPERATIONS:
        operation = "Покупка"

    return {
        "date": date,
        "amount": amount,
        "currency": match.group("currency"),
        "operation": operation,
        "description": match.group("details") or "",
        "direction": direction,
        "transfer_type": None,
    }


def _to_decimal(value: str) -> Decimal:
    """
    Приводит строку суммы к Decimal.

    Примеры:
    '1 234,56' → Decimal('1234.56')
    '-500,00'  → Decimal('-500.00')
    """
    v = value.replace("−", "-").replace(" ", "")
    if "." in v and "," in v:
        v = v.replace(",", "")
    else:
        v = v.replace(",", ".")
    v = re.sub(r"[^0-9\.\-]", "", v)
    return Decimal(v or "0")
