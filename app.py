import streamlit as st
from decimal import Decimal

from analytics import (
    classify_transfers,
    filter_self_transfers,
    categorize_transactions,
    print_report,
    adaptive_category_limits,
    saving_scenarios,
)

from kaspi_parser import parse_kaspi_pdf
from freedom_parser import parse_freedom_pdf


# ============================================================
# НАСТРОЙКИ СТРАНИЦЫ
# ============================================================

st.set_page_config(
    page_title="Финансовый анализ",
    layout="wide"
)

st.title("💰 Финансовый анализ расходов")
st.caption("Kaspi + Freedom • Аналитика • Лимиты • Экономия")


# ============================================================
# ЗАГРУЗКА ФАЙЛОВ
# ============================================================

st.header("📂 Загрузка выписок")

uploaded_files = st.file_uploader(
    "Загрузите PDF-выписки (Kaspi / Freedom)",
    type=["pdf"],
    accept_multiple_files=True
)

transactions = []

if uploaded_files:
    for file in uploaded_files:
        name = file.name.lower()

        if "kaspi" in name:
            txs = parse_kaspi_pdf(file)
        else:
            txs = parse_freedom_pdf(file)

        transactions.extend(txs)

    # аналитический пайплайн
    transactions = classify_transfers(transactions)
    transactions = filter_self_transfers(transactions)
    transactions = categorize_transactions(transactions)

    st.success(f"Загружено операций: {len(transactions)}")


# ============================================================
# ОТЧЁТ
# ============================================================

if transactions:
    st.header("📊 Общий отчёт")

    income = sum(
        tx["amount"] for tx in transactions
        if tx["direction"] == "income"
    )
    expense = sum(
        abs(tx["amount"]) for tx in transactions
        if tx["direction"] == "expense"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Доходы", f"{income:,.0f} ₸")
    col2.metric("Расходы", f"{expense:,.0f} ₸")
    col3.metric("Баланс", f"{income - expense:,.0f} ₸")


# ============================================================
# АДАПТИВНЫЕ ЛИМИТЫ
# ============================================================

if transactions:
    st.header("🚦 Адаптивные лимиты")

    cut = st.slider(
        "Насколько сократить привычные траты (%)",
        min_value=5,
        max_value=30,
        value=10,
        step=5
    )

    limits = adaptive_category_limits(transactions, cut)

    for cat, info in limits.items():
        st.progress(
            min(float(info["spent"] / info["limit"]), 1.0),
            text=f"{cat}: {info['spent']:.0f} / {info['limit']:.0f} ₸"
        )


# ============================================================
# СЦЕНАРИИ ЭКОНОМИИ
# ============================================================

if transactions:
    st.header("💡 Если сократить → можно отложить")

    scenarios = saving_scenarios(transactions, percents=[10, 20])

    for cat, values in scenarios.items():
        for p, saved in values.items():
            if saved > 0:
                st.write(
                    f"Если сократить **{cat}** на **{p}%** → "
                    f"можно отложить **{saved:,.0f} ₸**"
                )


# ============================================================
# ТАБЛИЦА ОПЕРАЦИЙ
# ============================================================

if transactions:
    st.header("📄 Все операции")

    st.dataframe(
        [
            {
                "Дата": tx["date"].date(),
                "Сумма": tx["amount"],
                "Категория": tx.get("category"),
                "Описание": tx.get("description"),
                "Источник": tx.get("source"),
            }
            for tx in transactions
        ],
        use_container_width=True
    )
