"""
classifier.py

Бизнес-логика.
Определяет, ЧТО означает операция для пользователя.
"""

from config import SELF_KEYWORDS, FAMILY_KEYWORDS


def classify_transfers(transactions: list[dict]) -> None:
    """
    Классифицирует переводы:
    - self    → перевод себе
    - family  → перевод члену семьи
    - other   → перевод другому человеку
    """
    for tx in transactions:
        # Нас интересуют только переводы
        if tx["operation"] != "Перевод":
            continue

        desc = tx["description"]

        tx["direction"] = "transfer"

        if any(k in desc for k in SELF_KEYWORDS):
            tx["transfer_type"] = "self"
        elif any(k in desc for k in FAMILY_KEYWORDS):
            tx["transfer_type"] = "family"
        else:
            tx["transfer_type"] = "other"
