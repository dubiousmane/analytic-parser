from freedom_parser import parse_freedom_pdf
from kaspi_parser import parse_kaspi_pdf

from analytics import (
    classify_transfers,
    filter_self_transfers,
    categorize_transactions,
    print_report,
    print_saving_scenarios,
    print_adaptive_limits,
    print_small_expenses_insight,
    print_recurring_payments,
)


def main():
    # --------------------------------------------------
    # 1. Парсинг PDF
    # --------------------------------------------------
    transactions = []

    transactions.extend(parse_freedom_pdf("freedom_statement.pdf"))
    transactions.extend(parse_kaspi_pdf("kaspi_statement.pdf"))

    print(f"\nВсего операций (сырых): {len(transactions)}\n")

    # --------------------------------------------------
    # 2. Классификация переводов
    # --------------------------------------------------
    classify_transfers(transactions)

    # --------------------------------------------------
    # 3. Фильтрация self-transfer
    # --------------------------------------------------
    transactions = filter_self_transfers(transactions)

    # --------------------------------------------------
    # 4. Категоризация расходов
    # --------------------------------------------------
    transactions = categorize_transactions(transactions)

    print(f"Всего операций (после фильтрации): {len(transactions)}")

    # --------------------------------------------------
    # 5. БАЗОВЫЙ ОТЧЁТ
    # --------------------------------------------------
    print_report(transactions)

    # --------------------------------------------------
    # 6. СЦЕНАРИИ ЭКОНОМИИ
    # --------------------------------------------------
    print_saving_scenarios(transactions, percents=[10, 20])

    # --------------------------------------------------
    # 7. АДАПТИВНЫЕ ЛИМИТЫ
    # --------------------------------------------------
    print_adaptive_limits(transactions, cut_percent=10)

    # --------------------------------------------------
    # 8. МЕЛКИЕ ТРАТЫ
    # --------------------------------------------------
    print_small_expenses_insight(transactions, threshold=2000)

    # --------------------------------------------------
    # 9. ПОВТОРЯЮЩИЕСЯ ПЛАТЕЖИ
    # --------------------------------------------------
    print_recurring_payments(transactions, min_count=2)


if __name__ == "__main__":
    main()
