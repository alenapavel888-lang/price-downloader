import os
import sys
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from statistics import mean

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

BRAND_ALIASES = {
    "electrolux professional": "electrolux",
    "electrolux pro": "electrolux",
    "electrolux": "electrolux",
    "robot coupe": "robotcoupe",
    "robot-coupe": "robotcoupe",
    "abat": "abat",
    "абат": "abat",
}

# -------------------------
# УТИЛИТЫ
# -------------------------

def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def normalize(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s×x]", " ", str(t).lower())).strip()

def normalize_brand(name):
    n = normalize(name)
    for k, v in BRAND_ALIASES.items():
        if k in n:
            return v
    return n.split()[0] if n else ""

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

def extract_qty(text):
    m = re.search(r"(\d+)\s*(шт|pcs|x)?", text)
    return int(m.group(1)) if m else None

# -------------------------
# ENTERO
# -------------------------

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

# -------------------------
# ПРАЙСЫ
# -------------------------

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
                "numbers": extract_numbers(text),
                "brand": normalize_brand(r.get("Наименование",""))
            })
    return items

# -------------------------
# ПОИСК
# -------------------------

def is_match(q_nums, i_nums, allow_analogs):
    for k, qv in q_nums.items():
        iv = i_nums.get(k)
        if iv is None:
            return False
        if allow_analogs:
            if iv < qv * 0.8 or iv > qv * 1.2:
                return False
        else:
            if iv != qv:
                return False
    return True

def dealer_price(it):
    r = it["row"]
    return to_float(r.get("Цена дилерская") or r.get("Дилерская цена")) or 1e12

# -------------------------
# MAIN
# -------------------------

def main():
    raw = os.getenv("MANAGER_QUERY")
    if not raw:
        fail("MANAGER_QUERY не задан")

    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    items = load_prices()

    rows = []
    totals_profit, totals_sum, totals_markup, totals_diff = [], [], [], []
    idx = 1

    for line in lines:
        text = normalize(line)
        allow_analogs = any(x in text for x in ["аналог", "аналоги", "можно аналог"])
        qty = extract_qty(text)
        numbers = extract_numbers(text)
        type_word = text.split()[0]

        candidates = []
        for it in items:
            if type_word not in it["text"]:
                continue
            if not is_match(numbers, it["numbers"], allow_analogs):
                continue
            candidates.append(it)

        candidates = sorted(candidates, key=dealer_price)

        if not candidates:
            rows.append([idx,"","","❌ Не найдено","–","❌ Не найдено","","","","","","","","","","","",""])
            idx += 1
            continue

        selected = candidates[:3] if allow_analogs else [candidates[0]]

        for it in selected:
            r = it["row"]
            dealer = to_float(r.get("Цена дилерская"))
            retail = to_float(r.get("Цена розничная"))
            profit = retail - dealer if dealer and retail else None
            total = retail * qty if retail and qty else None

            entero = search_entero(r.get("Наименование",""))
            diff = (retail - entero["price"]) / entero["price"] * 100 if entero and entero["price"] and retail else None
            markup = (retail - dealer) / dealer * 100 if dealer and retail else None

            if profit: totals_profit.append(profit)
            if total: totals_sum.append(total)
            if markup is not None: totals_markup.append(markup)
            if diff is not None: totals_diff.append(diff)

            rows.append([
                idx, it["source"], r.get("Артикул",""), r.get("Наименование",""),
                qty if qty else "–", r.get("Наличие",""),
                dealer or "", "RUB", retail or "", "RUB",
                entero["price"] if entero else "❌ Не найдено",
                f"{diff:+.0f}" if diff is not None else "",
                f"{markup:.0f}" if markup is not None else "",
                f"{profit:.0f}" if profit else "",
                f"{total:.0f}" if total else "",
                "", "", "", entero["link"] if entero else ""
            ])
            idx += 1

    print("```")
    print("\t".join(COLUMNS))
    for r in rows:
        print("\t".join(map(str, r)))

    print("\t".join([
        "ИТОГО","","","",
        "","","","","","",
        "",
        f"{mean(totals_diff):+.0f}" if totals_diff else "",
        f"{mean(totals_markup):.0f}" if totals_markup else "",
        f"{sum(totals_profit):.0f}" if totals_profit else "",
        f"{sum(totals_sum):.0f}" if totals_sum else "",
        "","","",""
    ]))
    print("```")
    print("✅ Подбор оборудования готов")

if __name__ == "__main__":
    main()
