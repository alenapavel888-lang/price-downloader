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
TOLERANCE = 0.20

SUPPLIERS = {
    "equip": "equip.xlsx",
    "bio": "bio.xlsx",
    "rp": "rp.xlsx",
    "rosholod": "rosholod.xlsx",
    "smirnov": "smirnov.xlsx",
    "trade_design": "td.xlsx",
}

ENTERO_BASE = "https://entero.ru"

COLUMNS = [
    "№","Источник","Артикул","Наименование","Нужно","На складе",
    "Цена дилерская","Валюта","Цена розничная","Валюта",
    "Цена Entero","Разница %","Наценка %","Валовая прибыль",
    "Сумма","Размеры (Ш×Г×В)","Вес (кг)","Объём (м³)","Ссылка"
]

# =========================
# БАЗОВОЕ
# =========================

def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def normalize(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s×x]", " ", str(t).lower())).strip()

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

def within(a, b):
    return a * (1 - TOLERANCE) <= b <= a * (1 + TOLERANCE)

# =========================
# ЗАПРОС МЕНЕДЖЕРА
# =========================

def read_query():
    q = os.getenv("MANAGER_QUERY")
    if not q:
        fail("MANAGER_QUERY не задан")
    return q.strip()

def parse_query(q):
    n = normalize(q)
    return {
        "raw": q,
        "type": n.split()[0],
        "numbers": extract_numbers(n),
        "qty": int(re.search(r"(\d+)\s*шт", n).group(1)) if re.search(r"\d+\s*шт", n) else None,
        "allow_analogs": "аналог" in n,
    }

# =========================
# ПРАЙСЫ
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
                "norm": normalize(text),
                "nums": extract_numbers(normalize(text)),
            })
    return items

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
    found.sort(key=lambda x: len(x["nums"]), reverse=True)
    return found[:3] if allow_analogs else found[:1]

# =========================
# ENTERO.RU
# =========================

def fetch_entero(model_text):
    try:
        search_url = f"{ENTERO_BASE}/search/?q={model_text.replace(' ', '+')}"
        r = requests.get(search_url, timeout=20)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "lxml")
        card = soup.select_one("a.product-card__title")
        if not card:
            return None

        link = ENTERO_BASE + card.get("href")
        page = requests.get(link, timeout=20)
        soup = BeautifulSoup(page.text, "lxml")

        price_tag = soup.select_one(".price__current")
        price = (
            float(price_tag.text.replace(" ", "").replace("₽", ""))
            if price_tag else None
        )

        return {
            "price": price,
            "link": link
        }

    except Exception:
        return None

# =========================
# ТАБЛИЦА КП
# =========================

def build_table(results, parsed):
    rows = []
    totals = {"qty":0,"profit":0,"sum":0,"markup":[]}

    for i, r in enumerate(results, 1):
        row = r["row"]
        name = row.get("Наименование") or row.get("Название") or ""
        entero = fetch_entero(name)

        dealer = float(row.get("Цена дилерская") or 0) if row.get("Цена дилерская") else None
        retail = float(row.get("Цена розничная") or 0) if row.get("Цена розничная") else None
        qty = parsed["qty"]

        profit = retail - dealer if dealer and retail else None
        total = retail * qty if retail and qty else None
        markup = ((retail - dealer)/dealer*100) if dealer and retail else None

        if qty: totals["qty"] += qty
        if profit: totals["profit"] += profit
        if total: totals["sum"] += total
        if markup: totals["markup"].append(markup)

        rows.append([
            i, r["source"], row.get("Артикул",""), name,
            qty if qty else "–",
            row.get("Остаток",""),
            dealer or "", "RUB" if dealer else "",
            retail or "", "RUB" if retail else "",
            entero["price"] if entero else "❌ Не найдено",
            "", round(markup,2) if markup else "",
            profit or "", total or "",
            "", "", "",
            entero["link"] if entero else ""
        ])

    rows.append([
        "ИТОГО","","","",
        totals["qty"],"","","","","","",
        "", round(mean(totals["markup"]),2) if totals["markup"] else "",
        totals["profit"], totals["sum"],
        "","","",""
    ])

    return rows

def print_table(rows):
    print("\n```")
    print("\t".join(COLUMNS))
    for r in rows:
        print("\t".join(map(str,r)))
    print("```")
    print("\n✅ Подбор оборудования готов")

# =========================
# MAIN
# =========================

def main():
    q = read_query()
    parsed = parse_query(q)
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
