import os
import sys
import pandas as pd
import re
from statistics import mean

# =========================
# КОНФИГУРАЦИЯ
# =========================

DATA_DIR = "data"
TOLERANCE = 0.20  # ±20%

SUPPLIERS = {
    "equip": "equip.xlsx",
    "bio": "bio.xlsx",
    "rp": "rp.xlsx",
    "rosholod": "rosholod.xlsx",
    "smirnov": "smirnov.xlsx",
    "trade_design": "td.xlsx",
}

COLUMNS_ORDER = [
    "№",
    "Источник",
    "Артикул",
    "Наименование",
    "Нужно",
    "На складе",
    "Цена дилерская",
    "Валюта",
    "Цена розничная",
    "Валюта",
    "Цена Entero",
    "Разница %",
    "Наценка %",
    "Валовая прибыль",
    "Сумма",
    "Размеры (Ш×Г×В)",
    "Вес (кг)",
    "Объём (м³)",
    "Ссылка",
]

# =========================
# ВСПОМОГАТЕЛЬНОЕ
# =========================

def fail(msg):
    print(f"❌ ОШИБКА: {msg}")
    sys.exit(1)


def normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s×x]", " ", str(text).lower())).strip()


def extract_numbers(text):
    patterns = {
        "kg": r"(\d+(?:[.,]\d+)?)\s*кг",
        "l": r"(\d+(?:[.,]\d+)?)\s*л",
        "levels": r"(\d+)\s*уров",
    }
    out = {}
    for k, p in patterns.items():
        m = re.search(p, text)
        if m:
            out[k] = float(m.group(1).replace(",", "."))
    return out


def within(v1, v2):
    return v1 * (1 - TOLERANCE) <= v2 <= v1 * (1 + TOLERANCE)


# =========================
# ЗАПРОС МЕНЕДЖЕРА
# =========================

def read_query():
    q = os.getenv("MANAGER_QUERY")
    if not q:
        fail("MANAGER_QUERY не задан")
    return q.strip()


def parse_query(q):
    norm = normalize(q)
    return {
        "raw": q,
        "type": norm.split()[0],
        "numbers": extract_numbers(norm),
        "qty": int(re.search(r"(\d+)\s*шт", norm).group(1)) if re.search(r"\d+\s*шт", norm) else None,
        "allow_analogs": "аналог" in norm,
    }


# =========================
# ЗАГРУЗКА ПРАЙСОВ
# =========================

def load_prices():
    items = []
    for src, file in SUPPLIERS.items():
        path = os.path.join(DATA_DIR, file)
        df = pd.read_excel(path, dtype=str).fillna("")
        for _, r in df.iterrows():
            text = " ".join(map(str, r.values))
            items.append({
                "source": src,
                "row": r.to_dict(),
                "text": text,
                "norm": normalize(text),
                "nums": extract_numbers(normalize(text)),
            })
    return items


# =========================
# ПОИСК
# =========================

def search(parsed, items):
    found = []
    for it in items:
        if parsed["type"] not in it["norm"]:
            continue
        ok = True
        for k, v in parsed["numbers"].items():
            if k not in it["nums"] or not within(v, it["nums"][k]):
                ok = False
                break
        if ok:
            found.append(it)
    return found


def choose(found, allow_analogs):
    if not found:
        return []
    found.sort(key=lambda x: len(x["nums"]), reverse=True)
    return found[:3] if allow_analogs else found[:1]


# =========================
# ИЗВЛЕЧЕНИЕ ФАКТОВ
# =========================

def pick(row, *keys):
    for k in keys:
        if k in row and row[k]:
            return row[k]
    return ""


# =========================
# ТАБЛИЦА КП
# =========================

def build_table(results, parsed):
    rows = []
    totals = {
        "qty": 0,
        "profit": 0,
        "sum": 0,
        "weight": 0,
        "volume": 0,
        "diff": [],
        "markup": [],
    }

    for i, r in enumerate(results, 1):
        row = r["row"]

        dealer = float(pick(row, "Цена дилерская", "Цена")) if pick(row, "Цена дилерская", "Цена") else None
        retail = float(pick(row, "Цена розничная")) if pick(row, "Цена розничная") else None
        qty = parsed["qty"]

        profit = retail - dealer if dealer and retail else None
        total = retail * qty if retail and qty else None

        diff = ((retail - None) / None * 100) if False else None
        markup = ((retail - dealer) / dealer * 100) if dealer and retail else None

        if qty:
            totals["qty"] += qty
        if profit:
            totals["profit"] += profit
        if total:
            totals["sum"] += total
        if markup is not None:
            totals["markup"].append(markup)

        rows.append([
            i,
            r["source"],
            pick(row, "Артикул", "Код"),
            pick(row, "Наименование", "Название"),
            qty if qty else "–",
            pick(row, "Остаток", "Наличие", "Под заказ"),
            dealer if dealer else "",
            "RUB" if dealer else "",
            retail if retail else "",
            "RUB" if retail else "",
            "",
            "",
            round(markup, 2) if markup is not None else "",
            profit if profit else "",
            total if total else "",
            "",
            "",
            "",
            "",
        ])

    # ИТОГО
    rows.append([
        "ИТОГО",
        "",
        "",
        "",
        totals["qty"] if totals["qty"] else "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        round(mean(totals["markup"]), 2) if totals["markup"] else "",
        totals["profit"] if totals["profit"] else "",
        totals["sum"] if totals["sum"] else "",
        "",
        "",
        "",
        "",
    ])

    return rows


# =========================
# ВЫВОД
# =========================

def print_table(rows):
    print("\n```")
    print("\t".join(COLUMNS_ORDER))
    for r in rows:
        print("\t".join(map(str, r)))
    print("```")
    print("\n✅ Подбор оборудования готов")


# =========================
# MAIN
# =========================

def main():
    query = read_query()
    parsed = parse_query(query)
    items = load_prices()
    found = search(parsed, items)
    chosen = choose(found, parsed["allow_analogs"])

    if not chosen:
        print("❌ Не найдено ни у одного поставщика")
        print("✅ Подбор оборудования готов")
        return

    table = build_table(chosen, parsed)
    print_table(table)


if __name__ == "__main__":
    main()
