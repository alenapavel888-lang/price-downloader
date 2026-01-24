import os
import sys
import pandas as pd
import re
from statistics import mean

# =========================
# КОНФИГУРАЦИЯ
# =========================

DATA_DIR = "data"

SUPPLIERS = {
    "equip": "equip.xlsx",
    "bio": "bio.xlsx",
    "rp": "rp.xlsx",
    "rosholod": "rosholod.xlsx",
    "smirnov": "smirnov.xlsx",
    "trade_design": "td.xlsx",
}

COLUMNS = [
    "№","Источник","Артикул","Наименование","Нужно","На складе",
    "Цена дилерская","Валюта","Цена розничная","Валюта",
    "Цена Entero","Разница %","Наценка %","Валовая прибыль",
    "Сумма","Размеры (Ш×Г×В)","Вес (кг)","Объём (м³)","Ссылка"
]

# =========================
# УТИЛИТЫ
# =========================

def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def normalize(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s×x]", " ", str(t).lower())).strip()

def extract_price(val):
    try:
        return float(str(val).replace(",", "."))
    except:
        return None

# =========================
# ЗАПРОС
# =========================

def read_query():
    q = os.getenv("MANAGER_QUERY")
    if not q:
        fail("MANAGER_QUERY не задан")
    return q.strip()

# =========================
# ЗАГРУЗКА ПРАЙСОВ
# =========================

def load_prices():
    rows = []
    for src, file in SUPPLIERS.items():
        path = os.path.join(DATA_DIR, file)
        df = pd.read_excel(path, dtype=str).fillna("")
        for _, r in df.iterrows():
            rows.append({
                "source": src,
                "row": r.to_dict(),
                "text": normalize(" ".join(map(str, r.values)))
            })
    return rows

# =========================
# ПОИСК (УЖЕ ОТФИЛЬТРОВАННЫЙ РАНЕЕ)
# =========================

def simple_match(query, items):
    q = normalize(query)
    matches = []
    for it in items:
        if q.split()[0] in it["text"]:
            matches.append(it)
    return matches

# =========================
# ТАБЛИЦА КП
# =========================

def build_table(matches, need_qty):
    table = []
    profits = []
    sums = []

    for i, it in enumerate(matches, start=1):
        r = it["row"]

        dealer = extract_price(r.get("Цена дилерская") or r.get("Дилерская цена"))
        retail = extract_price(r.get("Цена розничная") or r.get("Розничная цена"))

        markup = ((retail - dealer) / dealer * 100) if dealer and retail else None
        profit = (retail - dealer) if dealer and retail else None
        total = (retail * need_qty) if retail and need_qty else None

        if profit is not None:
            profits.append(profit)
        if total is not None:
            sums.append(total)

        table.append([
            i,
            it["source"],
            r.get("Артикул",""),
            r.get("Наименование",""),
            need_qty if need_qty else "–",
            r.get("Наличие",""),
            dealer or "",
            "RUB" if dealer else "",
            retail or "",
            "RUB" if retail else "",
            "",
            "",
            f"{markup:.0f}" if markup else "",
            f"{profit:.0f}" if profit else "",
            f"{total:.0f}" if total else "",
            "",
            "",
            "",
            ""
        ])

    # ИТОГО
    table.append([
        "ИТОГО","","","",
        need_qty if need_qty else "",
        "",
        "","","","",
        "",
        "",
        f"{mean([float(x[11]) for x in table if x[11]]) :.0f}" if any(x[11] for x in table) else "",
        f"{sum(profits):.0f}" if profits else "",
        f"{sum(sums):.0f}" if sums else "",
        "","","",""
    ])

    return table

# =========================
# ВЫВОД
# =========================

def print_table(table):
    print("```")
    print("\t".join(COLUMNS))
    for row in table:
        print("\t".join(map(str, row)))
    print("```")
    print("✅ Подбор оборудования готов")

# =========================
# MAIN
# =========================

def main():
    query = read_query()
    items = load_prices()

    matches = simple_match(query, items)

    if not matches:
        print("❌ Не найдено ни у одного поставщика")
        print("```")
        print("\t".join(COLUMNS))
        print("ИТОГО")
        print("```")
        print("✅ Подбор оборудования готов")
        return

    table = build_table(matches[:1], None)
    print_table(table)

if __name__ == "__main__":
    main()
