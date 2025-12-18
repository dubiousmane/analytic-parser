"""
analytics.py

Слой аналитики.
Работает с уже распарсенными транзакциями (Kaspi + Freedom).

Функции:
- классификация переводов
- фильтрация self-transfer
- категоризация расходов
- расчёт доходов / расходов
- сценарии экономии
- адаптивные лимиты
- анализ мелких трат
- поиск повторяющихся платежей
"""

from collections import defaultdict, Counter
from decimal import Decimal
from typing import List, Dict
import re

from config import (
    SELF_KEYWORDS,
    FAMILY_KEYWORDS,
    CATEGORIES,
)

# ============================================================
# ВСПОМОГАТЕЛЬНОЕ
# ============================================================

def _contains_any(text: str, keywords: list[str]) -> bool:
    low = (text or "").lower()
    return any(k.lower() in low for k in keywords)


# ============================================================
# КЛАССИФИКАЦИЯ ПЕРЕВОДОВ
# ============================================================

def classify_transfers(transactions: List[Dict]) -> List[Dict]:
    """
    Определяет тип перевода:
    self / family / other
    """
    for tx in transactions:
        if tx.get("operation") != "Перевод":
            continue

        desc = tx.get("description", "")

        if _contains_any(desc, SELF_KEYWORDS):
            tx["transfer_type"] = "self"
        elif _contains_any(desc, FAMILY_KEYWORDS):
            tx["transfer_type"] = "family"
        else:
            tx["transfer_type"] = "other"

    return transactions


def filter_self_transfers(transactions: List[Dict]) -> List[Dict]:
    """
    Убирает переводы самому себе
    """
    return [
        tx for tx in transactions
        if tx.get("transfer_type") != "self"
    ]


# ============================================================
# КАТЕГОРИЗАЦИЯ
# ============================================================

def categorize_transactions(transactions: List[Dict]) -> List[Dict]:
    """
    Назначает категорию каждой операции
    """
    for tx in transactions:
        desc = (tx.get("description") or "").upper()
        category = "Прочее"

        for cat_name, patterns in CATEGORIES:
            for pattern in patterns:
                if re.search(pattern, desc):
                    category = cat_name
                    break
            if category != "Прочее":
                break

        tx["category"] = category

    return transactions


# ============================================================
# СУММЫ
# ============================================================

def calculate_totals(transactions: List[Dict]) -> Dict[str, Decimal]:
    income = Decimal("0")
    expense = Decimal("0")

    for tx in transactions:
        if tx["direction"] == "income":
            income += tx["amount"]
        elif tx["direction"] == "expense":
            expense += abs(tx["amount"])

    return {
        "income": income,
        "expense": expense,
        "net": income - expense,
    }


def expenses_by_category(transactions: List[Dict]) -> Dict[str, Decimal]:
    result = defaultdict(Decimal)

    for tx in transactions:
        if tx["direction"] != "expense":
            continue

        result[tx.get("category", "Прочее")] += abs(tx["amount"])

    return dict(result)


# ============================================================
# АДАПТИВНЫЕ ЛИМИТЫ
# ============================================================

def adaptive_category_limits(
    transactions: List[Dict],
    cut_percent: int = 10
) -> Dict[str, Dict]:

    expenses = expenses_by_category(transactions)
    result = {}

    for category, spent in expenses.items():
        limit = (spent * (Decimal(100 - cut_percent) / 100)).quantize(
            Decimal("1")
        )

        if spent >= limit:
            status = "exceeded"
        elif spent >= limit * Decimal("0.8"):
            status = "warning"
        else:
            status = "ok"

        result[category] = {
            "spent": spent,
            "limit": limit,
            "remaining": limit - spent,
            "status": status,
        }

    return result


def print_adaptive_limits(transactions: List[Dict], cut_percent: int = 10) -> None:
    limits = adaptive_category_limits(transactions, cut_percent)

    print("\n====== АДАПТИВНЫЕ ЛИМИТЫ ======\n")

    for category, info in sorted(
        limits.items(),
        key=lambda x: x[1]["spent"],
        reverse=True
    ):
        icon = {
            "ok": "✅",
            "warning": "⚠️",
            "exceeded": "❌",
        }[info["status"]]

        print(
            f'{icon} {category:<30} '
            f'{info["spent"]:.0f} / {info["limit"]:.0f}'
        )

    print("\n==============================\n")


# ============================================================
# СЦЕНАРИИ ЭКОНОМИИ
# ============================================================

def saving_scenarios(
    transactions: List[Dict],
    percents: list[int] = [10, 20]
) -> Dict[str, Dict[int, Decimal]]:

    expenses = expenses_by_category(transactions)
    scenarios = {}

    for category, amount in expenses.items():
        scenarios[category] = {}
        for p in percents:
            scenarios[category][p] = (
                amount * Decimal(p) / Decimal(100)
            ).quantize(Decimal("1"))

    return scenarios


def print_saving_scenarios(
    transactions: List[Dict],
    percents: list[int] = [10]
) -> None:

    scenarios = saving_scenarios(transactions, percents)

    print("\n====== СЦЕНАРИИ ЭКОНОМИИ ======\n")

    for category, values in scenarios.items():
        for p, saved in values.items():
            if saved > 0:
                print(
                    f'Если сократить "{category}" на {p}% → '
                    f'можно отложить {saved:.0f}'
                )

    print("\n==============================\n")


# ============================================================
# МЕЛКИЕ ТРАТЫ
# ============================================================

def small_expenses_insight(
    transactions: List[Dict],
    threshold: int = 2000
) -> Dict[str, Decimal]:
    """
    Ищет мелкие траты, которые незаметно съедают бюджет
    """
    result = defaultdict(Decimal)

    for tx in transactions:
        if tx["direction"] != "expense":
            continue

        if abs(tx["amount"]) <= threshold:
            result[tx.get("category", "Прочее")] += abs(tx["amount"])

    return dict(result)


def print_small_expenses_insight(
    transactions: List[Dict],
    threshold: int = 2000
) -> None:

    data = small_expenses_insight(transactions, threshold)

    print("\n====== МЕЛКИЕ ТРАТЫ ======\n")

    for cat, amount in sorted(
        data.items(),
        key=lambda x: x[1],
        reverse=True
    ):
        print(f"{cat:<30} {amount:.0f}")

    print("\n==========================\n")


# ============================================================
# ПОВТОРЯЮЩИЕСЯ ПЛАТЕЖИ
# ============================================================

def recurring_payments(
    transactions: List[Dict],
    min_count: int = 2
) -> Dict[str, int]:
    """
    Находит повторяющиеся траты по описанию
    """
    counter = Counter()

    for tx in transactions:
        if tx["direction"] != "expense":
            continue

        key = tx.get("description", "").upper()
        counter[key] += 1

    return {
        desc: count
        for desc, count in counter.items()
        if count >= min_count
    }


def print_recurring_payments(
    transactions: List[Dict],
    min_count: int = 2
) -> None:

    data = recurring_payments(transactions, min_count)

    print("\n====== ПОВТОРЯЮЩИЕСЯ ПЛАТЕЖИ ======\n")

    for desc, count in sorted(
        data.items(),
        key=lambda x: x[1],
        reverse=True
    ):
        print(f"{desc[:40]:<42} × {count}")

    print("\n=================================\n")


# ============================================================
# ОТЧЁТ
# ============================================================

def print_report(transactions: List[Dict]) -> None:
    totals = calculate_totals(transactions)
    by_category = expenses_by_category(transactions)

    print("\n========== ФИНАНСОВЫЙ ОТЧЁТ ==========\n")

    print(f"Доходы:   {totals['income']:.2f}")
    print(f"Расходы:  {totals['expense']:.2f}")
    print(f"Баланс:   {totals['net']:.2f}\n")

    print("Расходы по категориям:")
    for cat, amount in sorted(
        by_category.items(),
        key=lambda x: x[1],
        reverse=True
    ):
        print(f"  {cat:<30} {amount:.2f}")

    print("\n=====================================\n")
