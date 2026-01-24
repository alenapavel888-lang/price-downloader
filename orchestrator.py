import os
import sys
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
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

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# =========================
# УТИЛИТЫ
# =========================

def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def normalize(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s×x]", " ", str(t).lower())).strip()

def to_float(v):
    try:
        return float(str(v).replace(",", "."))
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
# ПОИСК У ПОСТАВЩИКОВ
# =========================

def find_best_match(query, items):
    q = normalize(query)
    matches = []
    for it in items:
        if q.split()[0] in it["text"]:
            matches.append(it)

    if not matches:
        return None

    # минимальная дилерская цена
    def dealer_price(it):
        r = it["row"]
        return to_float(r.get("Цена дилерская") or r.get("Дилерская цена")) or 1e12

    return min(matches, key=dealer_price)

# =========================
# ENTERO.RU (ШАГ 10)
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

    best = cards[0]
    link = "https://entero.ru" + best.get("href")

    # карточка
    page = requests.get(link, headers=HEADERS, timeout=20)
    if page.status_code != 200:
        return None

    s = BeautifulSoup(page.text, "html.parser")

    price_tag = s.select_one(".product-buy__price")
    price = to_float(price_tag.text) if price_tag else None

    return {
        "price": price,
        "link": link
    }

# =========================
# ТАБЛИЦА КП
# =========================

def build_table(item, entero, qty):
    r = item["row"]

    dealer = to_float(r.get("Цена дилерская") or r.get("Дилерская цена"))
    retail = to_float(r.get("Цена розничная") or r.get("Розничная цена"))

    markup = ((retail - dealer) / dealer * 100) if dealer and retail else None
    profit = (retail - dealer) if dealer and retail else None
    total = (retail * qty) if retail and qty else None

    diff = None
    arrow = ""
    if entero and entero["price"] and retail:
        diff = (retail - entero["price"]) / entero["price"] * 100
        arrow = "⬆" if entero["price"] > retail else "⬇"

    table = [[
        1,
        item["source"],
        r.get("Артикул",""),
        r.get("Наименование",""),
        qty or "–",
        r.get("Наличие",""),
        dealer or "",
        "RUB" if dealer else "",
        retail or "",
        "RUB" if retail else "",
        f'{entero["price"]}{arrow}' if entero and entero["price"] else "❌ Не найдено",
        f"{diff:+.0f}" if diff is not None else "",
        f"{markup:.0f}" if markup else "",
        f"{profit:.0f}" if profit else "",
        f"{total:.0f}" if total else "",
        "",
        "",
        "",
        entero["link"] if entero else ""
    ]]

    table.append([
        "ИТОГО","","","",qty or "",
        "",
        "","","","",
        "",
        "",
        "",
        f"{profit:.0f}" if profit else "",
        f"{total:.0f}" if total else "",
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

    best = find_best_match(query, items)

    if not best:
        print("❌ Не найдено ни у одного поставщика")
        print("```")
        print("\t".join(COLUMNS))
        print("ИТОГО")
        print("```")
        print("✅ Подбор оборудования готов")
        return

    entero = search_entero(best["row"].get("Наименование",""))

    table = build_table(best, entero, None)
    print_table(table)

if __name__ == "__main__":
    main()
