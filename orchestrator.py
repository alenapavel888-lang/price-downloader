import os
import sys
import sqlite3
import re
import requests
from bs4 import BeautifulSoup
from statistics import mean

# =========================
# КОНФИГУРАЦИЯ
# =========================

DB_PATH = "index.db"

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

def normalize(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s×x]", " ", str(t).lower())).strip()

def to_float(v):
    try:
        return float(str(v).replace(",", "."))
    except:
        return None

def extract_numbers(text):
    res = {}
    patterns = {
        "kg": r"(\d+(?:[.,]\d+)?)\s*кг",
        "liters": r"(\d+(?:[.,]\d+)?)\s*л",
        "levels": r"(\d+)\s*уров",
        "kw": r"(\d+(?:[.,]\d+)?)\s*квт",
    }
    for k, p in patterns.items():
        m = re.search(p, text)
        if m:
            res[k] = float(m.group(1).replace(",", "."))
    return res

# =========================
# ЗАПРОС МЕНЕДЖЕРА
# =========================

def read_query():
    q = os.getenv("MANAGER_QUERY")
    if not q:
        fail("MANAGER_QUERY не задан")
    q = q.strip()
    print(f"📥 Запрос менеджера: {q}")
    return q

# =========================
# SQL ПОИСК
# =========================

def sql_search(parsed):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    where = []
    params = []

    where.append("text LIKE ?")
    params.append(f"%{parsed['type']}%")

    for k, v in parsed["numbers"].items():
        if parsed["allow_analogs"]:
            where.append(f"{k} BETWEEN ? AND ?")
            params.extend([v * 0.8, v * 1.2])
        else:
            where.append(f"{k} = ?")
            params.append(v)

    sql = f"""
    SELECT *
    FROM items
    WHERE {' AND '.join(where)}
    ORDER BY dealer_price ASC NULLS LAST
    """

    rows = cur.execute(sql, params).fetchall()
    conn.close()
    return rows

# =========================
# ENTERO
# =========================

def search_entero(name):
    q = "+".join(name.split())
    url = f"https://entero.ru/search/?q={q}"

    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    card = soup.select_one("a.catalog-item__name")
    if not card:
        return None

    link = "https://entero.ru" + card.get("href")
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
    qn = normalize(query)

    parsed = {
        "type": qn.split()[0],
        "numbers": extract_numbers(qn),
        "allow_analogs": "аналог" in qn
    }

    items = sql_search(parsed)

    if not items:
        print("❌ Не найдено ни у одного поставщика")
        print("```")
        print("\t".join(COLUMNS))
        print("ИТОГО")
        print("```")
        return

    if not parsed["allow_analogs"]:
        items = items[:1]
    else:
        items = items[:3]

    rows = []
    totals = {"profit": [], "sum": [], "markup": [], "diff": []}
    n = 1

    for it in items:
        dealer = it["dealer_price"]
        retail = it["retail_price"]

        profit = retail - dealer if dealer and retail else None
        markup = (retail - dealer) / dealer * 100 if dealer and retail else None
        total = retail

        entero = search_entero(it["name"])
        diff = None
        if entero and entero["price"] and retail:
            diff = (retail - entero["price"]) / entero["price"] * 100

        if profit: totals["profit"].append(profit)
        if total: totals["sum"].append(total)
        if markup is not None: totals["markup"].append(markup)
        if diff is not None: totals["diff"].append(diff)

        rows.append([
            n,
            it["supplier"],
            it["article"],
            it["name"],
            "–",
            it["availability"],
            dealer or "",
            "RUB" if dealer else "",
            retail or "",
            "RUB" if retail else "",
            entero["price"] if entero else "❌ Не найдено",
            f"{diff:+.0f}" if diff is not None else "",
            f"{markup:.0f}" if markup else "",
            f"{profit:.0f}" if profit else "",
            f"{total:.0f}" if total else "",
            "",
            "",
            "",
            entero["link"] if entero else ""
        ])
        n += 1

    print("```")
    print("\t".join(COLUMNS))
    for r in rows:
        print("\t".join(map(str, r)))

    print("\t".join([
        "ИТОГО","","","",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        f"{mean(totals['diff']):+.0f}" if totals["diff"] else "",
        f"{mean(totals['markup']):.0f}" if totals["markup"] else "",
        f"{sum(totals['profit']):.0f}" if totals["profit"] else "",
        f"{sum(totals['sum']):.0f}" if totals["sum"] else "",
        "","","",""
    ]))
    print("```")
    print("✅ Подбор оборудования готов")

if __name__ == "__main__":
    main()
