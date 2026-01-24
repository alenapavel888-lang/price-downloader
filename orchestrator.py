import os
import sys
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup

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
# ШАГ 12 — ПАРСИНГ ЗАПРОСА
# =========================

def parse_manager_query(query: str):
    q = normalize(query)

    allow_analogs = any(w in q for w in ["аналог", "аналоги"])

    numbers = {}
    patterns = {
        "kg": r"(\d+(?:[.,]\d+)?)\s*кг",
        "liters": r"(\d+(?:[.,]\d+)?)\s*л",
        "levels": r"(\d+)\s*уров",
        "kw": r"(\d+(?:[.,]\d+)?)\s*квт",
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, q)
        if m:
            numbers[key] = float(m.group(1).replace(",", "."))

    equipment_type = q.split()[0] if q else ""

    return {
        "raw": query,
        "type": equipment_type,
        "numbers": numbers,
        "allow_analogs": allow_analogs
    }

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

def extract_numbers_from_text(text):
    result = {}
    for key, pattern in {
        "kg": r"(\d+(?:[.,]\d+)?)\s*кг",
        "liters": r"(\d+(?:[.,]\d+)?)\s*л",
        "levels": r"(\d+)\s*уров",
        "kw": r"(\d+(?:[.,]\d+)?)\s*квт",
    }.items():
        m = re.search(pattern, text)
        if m:
            result[key] = float(m.group(1).replace(",", "."))
    return result

def load_prices():
    items = []
    for src, file in SUPPLIERS.items():
        path = os.path.join(DATA_DIR, file)
        df = pd.read_excel(path, dtype=str).fillna("")
        for _, r in df.iterrows():
            text = normalize(" ".join(map(str, r.values)))
            items.append({
                "source": src,
                "row": r.to_dict(),
                "text": text,
                "numbers": extract_numbers_from_text(text)
            })
    return items

# =========================
# ШАГ 14 — УМНЫЙ ПОИСК
# =========================

def is_match(query_nums, item_nums, allow_analogs):
    for k, qv in query_nums.items():
        iv = item_nums.get(k)
        if iv is None:
            return False
        if iv < qv:
            return False
        if allow_analogs:
            if iv > qv * 1.2:
                return False
        else:
            if iv != qv:
                return False
    return True

def find_best_match(parsed_query, items):
    candidates = []

    for it in items:
        if parsed_query["type"] not in it["text"]:
            continue
        if not is_match(parsed_query["numbers"], it["numbers"], parsed_query["allow_analogs"]):
            continue
        candidates.append(it)

    if not candidates:
        return None

    def dealer_price(it):
        r = it["row"]
        return to_float(r.get("Цена дилерская") or r.get("Дилерская цена")) or 1e12

    return min(candidates, key=dealer_price)

# =========================
# ENTERO.RU
# =========================

def search_entero(name):
    query = "+".join(name.split())
    url = f"https://entero.ru/search/?q={query}"

    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select("a.catalog-item__name")
    if not cards:
        return None

    link = "https://entero.ru" + cards[0].get("href")
    page = requests.get(link, headers=HEADERS, timeout=20)
    if page.status_code != 200:
        return None

    s = BeautifulSoup(page.text, "html.parser")
    price_tag = s.select_one(".product-buy__price")
    price = to_float(price_tag.text) if price_tag else None

    return {"price": price, "link": link}

# =========================
# MAIN
# =========================

def main():
    query = read_query()
    parsed = parse_manager_query(query)

    items = load_prices()
    best = find_best_match(parsed, items)

    if not best:
        print("❌ Не найдено (причина: нет подходящих характеристик в прайсах)")
        print("```")
        print("\t".join(COLUMNS))
        print("ИТОГО")
        print("```")
        print("✅ Подбор оборудования готов")
        return

    entero = search_entero(best["row"].get("Наименование",""))
    print("```")
    print("\t".join(COLUMNS))
    print("```")
    print("✅ Подбор оборудования готов")

if __name__ == "__main__":
    main()
