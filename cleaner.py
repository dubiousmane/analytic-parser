"""
cleaner.py

Отвечает ТОЛЬКО за очистку текста.
Никакого парсинга и бизнес-логики.
"""

import re
from config import FOOTER_MARKERS, NOISE_PATTERNS


def strip_footer(text: str) -> str:
    """
    Удаляет футтер, если он прилип к описанию операции.
    """
    low = text.lower()
    for marker in FOOTER_MARKERS:
        idx = low.find(marker)
        if idx != -1:
            return text[:idx]
    return text


def clean_description(text: str) -> str:
    """
    Финальная очистка description:
    - убираем футтер
    - убираем мусорные фразы
    - нормализуем пробелы
    """
    text = strip_footer(text)

    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", text).strip()
