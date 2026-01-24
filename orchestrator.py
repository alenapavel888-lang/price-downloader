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

def normalize(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s×x]", " ", str(t).lower())).strip()

def to_float(v):
    try:
        return float(str(v).replace(",", "."))
    except:
        return None

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

def is_url(t):
    return t.startswith("http://") or t.startswith("https://")

# =========================
# ПАРСИНГ ССЫЛКИ
# =========================

def parse_product_page(url):
    print(f"🌐 Парсинг страницы: {url}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
    except Exception as e:
        fail(f"Ошибка доступа к ссылке: {e}")

    if r.status_code != 200:
        fail(f"Страница недоступна, код {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")

    texts = []

    for tag in ["h1", "h2", "title"]:
        el = soup.find(tag)
        if el:
            texts.append(el.get_text(" ", strip=True))

    for el in soup.select("li, p, td"):
        t = el.get_text(" ", strip=True)
        if any(x in t.lower() for x in ["кг", "л", "уров", "квт", "мм", "см"]):
            texts.append(t)

    full_text = normalize(" ".join(texts))
    numbers = extract_numbers(full_text)

    print("✅ Данные извлечены из ссылки")

    return {
        "raw": url,
        "type": full_text.split()[0] if full_text else "",
        "numbers": numbers,
        "allow_analogs": False
    }

# =========================
# ПАРСИНГ ЗАПРОСА
# =========================

def split_queries(raw):
    raw = raw.replace(";", "\n")
    return [q.strip() for q in raw.splitlines() if q.strip()]

def parse_query(q):
    if is_url(q):
        return parse_product_page(q)

    qn = normalize(q)
    allow_analogs = any(w in qn for w in ["аналог", "аналоги", "можно аналог"])

    return {
        "raw": q,
        "type": qn.split()[0],
        "numbers": extract_numbers(qn),
        "allow_analogs": allow_analogs
    }

# =========================
# ПРАЙСЫ
# =========================

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
# ПОИСК
# =========================

def is_match(q_nums, i_nums, allow_analogs):
    for k, qv in q_nums.items():
        iv = i_nums.get(k)
        if iv is None:
            return False
        if allow_analogs:
            if iv < qv or iv > qv * 1.2:
                return False
        else:
            if iv != qv:
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

    if not allow_analogs:
        return [candidates[0]]

    base = candidates[0]
    brand = normalize(base["row"].get("Наименование","")).split()[0]

    same, other = [], []
    for it in candidates[1:]:
        name = normalize(it["row"].get("Наименование",""))
        if brand and brand in name:
            same.append(it)
        else:
            other.append(it)

    out = [base]
    out.extend(same[:2])
    if len(out) < 3:
        out.extend(other[:3-len(out)])

    return out[:3]

# =========================
# MAIN
# =========================

def main():
    raw = os.getenv("MANAGER_QUERY")
    if not raw:
        fail("MANAGER_QUERY не задан")

    queries = split_queries(raw)
    items = load_prices()

    rows = []
    n = 1

    for q in queries:
        parsed = parse_query(q)
        candidates = find_candidates(parsed, items)
        selected = select_items(candidates, parsed["allow_analogs"])

        if not selected:
            continue

        for it in selected:
            r = it["row"]
            rows.append([
                n,
                it["source"],
                r.get("Артикул",""),
                r.get("Наименование",""),
                "–",
                r.get("Наличие",""),
                r.get("Цена дилерская",""),
                "RUB",
                r.get("Цена розничная",""),
                "RUB",
                "❌ Не найдено",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                ""
            ])
            n += 1

    print("```")
    print("\t".join(COLUMNS))
    for r in rows:
        print("\t".join(map(str, r)))
    print("```")
    print("✅ Подбор оборудования готов")

if __name__ == "__main__":
    main()
