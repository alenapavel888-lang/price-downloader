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

# =========================
# ЗАПРОС МЕНЕДЖЕРА
# =========================

def parse_query():
    q = os.getenv("MANAGER_QUERY")
    if not q:
        fail("MANAGER_QUERY не задан")

    qn = normalize(q)
    allow_analogs = any(w in qn for w in ["аналог", "аналоги", "можно аналог"])

    nums = {}
    for k, p in {
        "kg": r"(\d+(?:[.,]\d+)?)\s*кг",
        "liters": r"(\d+(?:[.,]\d+)?)\s*л",
        "levels": r"(\d+)\s*уров",
        "kw": r"(\d+(?:[.,]\d+)?)\s*квт",
    }.items():
        m = re.search(p, qn)
        if m:
            nums[k] = float(m.group(1).replace(",", "."))

    return {
        "raw": q,
        "type": qn.split()[0],
        "numbers": nums,
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
# ПОИСК У ПОСТАВЩИКОВ
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

def dealer_price(it):
    r = it["row"]
    return to_float(r.get("Цена дилерская") or r.get("Дилерская цена")) or 1e12

def find_candidates(parsed, items):
    res = []
    for it in items:
        if parsed["type"] not in it["text"]:
            continue
        if not is_match(parsed["numbers"], it["numbers"], parsed["allow_analogs"]):
            continue
        res.append(it)
    return sorted(res, key=dealer_price)

def select_items(candidates, allow_analogs):
    if not candidates:
        return []

    best = candidates[0]
    if not allow_analogs:
        return [best]

    brand = normalize(best["row"].get("Наименование","")).split()[0]
    same_brand = []
    other = []

    for it in candidates[1:]:
        n = normalize(it["row"].get("Наименование",""))
        if brand and brand in n:
            same_brand.append(it)
        else:
            other.append(it)

    out = [best]
    out.extend(same_brand[:2])
    if len(out) < 3:
        out.extend(other[:3-len(out)])

    return out[:3]

# =========================
# ENTERO.RU
# =========================

def search_entero(name):
    q = "+".join(name.split())
    url = f"https://entero.ru/search/?q={q}"

    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    a = soup.select_one("a.catalog-item__name")
    if not a:
        return None

    link = "https://entero.ru" + a.get("href")
    p = requests.get(link, headers=HEADERS, timeout=20)
    if p.status_code != 200:
        return None

    s = BeautifulSoup(p.text, "html.parser")
    price_tag = s.select_one(".product-buy__price")

    price = to_float(price_tag.text) if price_tag else None
    return {"price": price, "link": link}

# =========================
# ФОРМИРОВАНИЕ ТАБЛИЦЫ
# =========================

def build_rows(items):
    rows = []
    profits = []
    totals = []

    for i, it in enumerate(items, 1):
        r = it["row"]
        dealer = to_float(r.get("Цена дилерская") or r.get("Дилерская цена"))
        retail = to_float(r.get("Цена розничная") or r.get("Розничная цена"))

        entero = search_entero(r.get("Наименование",""))
        entero_price = entero["price"] if entero else None

        diff = ((retail - entero_price) / entero_price * 100) if retail and entero_price else None
        markup = ((retail - dealer) / dealer * 100) if dealer and retail else None
        profit = (retail - dealer) if dealer and retail else None

        profits.append(profit or 0)
        totals.append(retail or 0)

        arrow = ""
        if entero_price and retail:
            arrow = "⬆" if entero_price > retail else "⬇"

        rows.append([
            i,
            it["source"],
            r.get("Артикул",""),
            r.get("Наименование",""),
            "–",
            r.get("Наличие",""),
            dealer or "",
            "RUB",
            retail or "",
            "RUB",
            f"{entero_price}{arrow}" if entero_price else "❌ Не найдено",
            f"{diff:+.0f}" if diff is not None else "",
            f"{markup:.0f}" if markup is not None else "",
            f"{profit:.0f}" if profit else "",
            f"{retail:.0f}" if retail else "",
            "",
            "",
            "",
            entero["link"] if entero else ""
        ])

    rows.append([
        "ИТОГО","","","",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        f"{sum(profits):.0f}",
        f"{sum(totals):.0f}",
        "",
        "",
        "",
        ""
    ])

    return rows

# =========================
# MAIN
# =========================

def main():
    parsed = parse_query()
    items = load_prices()
    candidates = find_candidates(parsed, items)
    selected = select_items(candidates, parsed["allow_analogs"])

    print("```")
    print("\t".join(COLUMNS))

    if not selected:
        print("ИТОГО")
        print("```")
        print("✅ Подбор оборудования готов")
        return

    for r in build_rows(selected):
        print("\t".join(map(str, r)))

    print("```")
    print("✅ Подбор оборудования готов")

if __name__ == "__main__":
    main()
