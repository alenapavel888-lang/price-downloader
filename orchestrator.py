import os
import sys
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup

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

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# УТИЛИТЫ
# =========================

def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s×x]", " ", str(text).lower())).strip()

def to_float(v):
    try:
        return float(str(v).replace(",", "."))
    except:
        return None

# =========================
# ПАРСИНГ ЗАПРОСА
# =========================

def parse_manager_query(query):
    q = normalize(query)
    allow_analogs = any(w in q for w in ["аналог", "аналоги"])

    numbers = {}
    patterns = {
        "kg": r"(\d+(?:[.,]\d+)?)\s*кг",
        "liters": r"(\d+(?:[.,]\d+)?)\s*л",
        "levels": r"(\d+)\s*уров",
        "kw": r"(\d+(?:[.,]\d+)?)\s*квт",
    }

    for k, p in patterns.items():
        m = re.search(p, q)
        if m:
            numbers[k] = float(m.group(1).replace(",", "."))

    eq_type = q.split()[0] if q else ""

    return {
        "raw": query,
        "type": eq_type,
        "numbers": numbers,
        "allow_analogs": allow_analogs
    }

# =========================
# ЗАГРУЗКА ПРАЙСОВ
# =========================

def extract_numbers(text):
    res = {}
    for k, p in {
        "kg": r"(\d+(?:[.,]\d+)?)\s*кг",
        "liters": r"(\d+(?:[.,]\d+)?)\s*л",
        "levels": r"(\d+)\s*уров",
        "kw": r"(\d+(?:[.,]\d+)?)\s*квт",
    }.items():
        m = re.search(p, text)
        if m:
            res[k] = float(m.group(1).replace(",", "."))
    return res

def load_prices():
    items = []
    for src, file in SUPPLIERS.items():
        df = pd.read_excel(os.path.join(DATA_DIR, file), dtype=str).fillna("")
        for _, r in df.iterrows():
            text = normalize(" ".join(map(str, r.values)))
            items.append({
                "source": src,
                "row": r.to_dict(),
                "text": text,
                "numbers": extract_numbers(text)
            })
    return items

# =========================
# ПОИСК И АНАЛОГИ
# =========================

def is_match(q_nums, i_nums, allow_analogs):
    for k, qv in q_nums.items():
        iv = i_nums.get(k)
        if iv is None or iv < qv:
            return False
        if allow_analogs and iv > qv * 1.2:
            return False
        if not allow_analogs and iv != qv:
            return False
    return True

def find_matches(parsed, items):
    matches = []
    for it in items:
        if parsed["type"] not in it["text"]:
            continue
        if not is_match(parsed["numbers"], it["numbers"], parsed["allow_analogs"]):
            continue
        matches.append(it)
    return matches

def dealer_price(it):
    r = it["row"]
    return to_float(r.get("Цена дилерская") or r.get("Дилерская цена")) or 1e12

def select_best_and_analogs(matches, allow_analogs):
    matches = sorted(matches, key=dealer_price)
    if not allow_analogs:
        return matches[:1]

    best = matches[0]
    same_brand = []
    other_brand = []

    brand = normalize(best["row"].get("Наименование","")).split()[0]

    for it in matches[1:]:
        name = normalize(it["row"].get("Наименование",""))
        if brand and brand in name:
            same_brand.append(it)
        else:
            other_brand.append(it)

    result = [best]
    result.extend(same_brand[:2])

    if len(result) < 3:
        result.extend(other_brand[:3-len(result)])

    return result[:3]

# =========================
# MAIN
# =========================

def main():
    query = os.getenv("MANAGER_QUERY")
    if not query:
        fail("MANAGER_QUERY не задан")

    parsed = parse_manager_query(query)
    items = load_prices()
    matches = find_matches(parsed, items)

    if not matches:
        print("❌ Не найдено (нет подходящих позиций)")
        print("```")
        print("\t".join(COLUMNS))
        print("ИТОГО")
        print("```")
        print("✅ Подбор оборудования готов")
        return

    selected = select_best_and_analogs(matches, parsed["allow_analogs"])

    print("```")
    print("\t".join(COLUMNS))
    for i, it in enumerate(selected, 1):
        r = it["row"]
        name = r.get("Наименование","")
        if i > 1:
            name += " (АНАЛОГ)"
        print("\t".join(map(str, [
            i,
            it["source"],
            r.get("Артикул",""),
            name,
            "–",
            r.get("Наличие",""),
            r.get("Цена дилерская",""),
            "RUB",
            r.get("Цена розничная",""),
            "RUB",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            ""
        ]))
    print("```")
    print("✅ Подбор оборудования готов")

if __name__ == "__main__":
    main()
