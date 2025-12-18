"""
kaspi_parser.py

Kaspi Bank PDF parser (v2).

Особенности Kaspi PDF:
- Табличный PDF
- На первой странице есть заголовки
- На следующих страницах заголовки могут отсутствовать
- Есть футтеры и мусорные строки

Стратегия:
1. Пытаемся определить индексы колонок по заголовкам
2. Если заголовков нет — используем предыдущие индексы
3. Парсим строки построчно
4. Фильтруем мусор
"""

import pdfplumber
import logging
from datetime import datetime
from decimal import Decimal
import re
from typing import List, Dict, Optional

from cleaner import clean_description


# ============================================================
# ЛОГИ
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def _parse_date(value: str) -> Optional[datetime]:
    """
    Kaspi формат даты: DD.MM.YY
    """
    try:
        return datetime.strptime(value.strip(), "%d.%m.%y")
    except Exception:
        return None


def _parse_amount(value: str) -> Decimal:
    """
    Примеры:
    -2 880,00 ₸
    +3 000,00 ₸
    """
    v = value.replace("₸", "").replace(" ", "").replace(",", ".")
    v = re.sub(r"[^0-9\.\-\+]", "", v)
    return Decimal(v or "0")


def _looks_like_header(row: List[str]) -> bool:
    """
    Проверяем, похожа ли строка на заголовок таблицы
    """
    joined = " ".join(cell.lower() for cell in row if cell)
    return (
        "дата" in joined
        and "сумм" in joined
        and "операц" in joined
    )


def _looks_like_transaction_row(row: List[str]) -> bool:
    """
    Быстрая эвристика: первая колонка — дата
    """
    if not row or not row[0]:
        return False
    return bool(re.match(r"\d{2}\.\d{2}\.\d{2}", row[0].strip()))


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================
def parse_kaspi_pdf(path: str) -> List[Dict]:
    """
    Парсит PDF-выписку Kaspi Bank.
    """
    transactions: List[Dict] = []

    logger.info(f"Start parsing Kaspi PDF: {path}")

    with pdfplumber.open(path) as pdf:
        logger.info(f"Total pages: {len(pdf.pages)}")

        # индексы колонок (могут появиться только на 1 странице)
        idx_date = idx_amount = idx_operation = idx_details = None

        for page_num, page in enumerate(pdf.pages, start=1):
            table = page.extract_table()
            if not table:
                logger.info(f"Page {page_num}: no table")
                continue

            parsed_on_page = 0

            for row_num, row in enumerate(table, start=1):
                # нормализуем строку
                row = [(cell or "").strip() for cell in row]

                # --- заголовок ---
                if _looks_like_header(row):
                    logger.info(f"Page {page_num}: header detected")
                    for i, cell in enumerate(row):
                        low = cell.lower()
                        if "дата" in low:
                            idx_date = i
                        elif "сумм" in low:
                            idx_amount = i
                        elif "операц" in low:
                            idx_operation = i
                        elif "детал" in low:
                            idx_details = i
                    continue

                # если индексы ещё не определены — пропускаем
                if idx_date is None or idx_amount is None or idx_operation is None:
                    continue

                # --- строка операции ---
                if not _looks_like_transaction_row(row):
                    continue

                try:
                    date = _parse_date(row[idx_date])
                    if not date:
                        continue

                    amount = _parse_amount(row[idx_amount])
                    operation = row[idx_operation].capitalize()
                    description = (
                        row[idx_details] if idx_details is not None else ""
                    )

                    tx = {
                        "date": date,
                        "amount": amount,
                        "currency": "KZT",
                        "operation": operation,
                        "description": clean_description(description),
                        "direction": (
                            "expense" if amount < 0
                            else "income" if amount > 0
                            else "neutral"
                        ),
                        "transfer_type": None,
                        "source": "kaspi",
                    }

                    transactions.append(tx)
                    parsed_on_page += 1

                except Exception:
                    continue

            logger.info(f"Page {page_num}: parsed={parsed_on_page}")

    logger.info(f"Finished Kaspi parsing | Parsed={len(transactions)}")
    return transactions
