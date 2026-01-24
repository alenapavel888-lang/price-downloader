import os
import sys
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from statistics import mean
from urllib.parse import urlparse

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
# БАЗА
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
        "kw": r"(\d+(?:[.,]\d+)?)\s*квт",
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
# ШАГ 8 — ССЫЛКИ
# =========================

def extract_links(text):
    return re.findall(r"https?://[^\s]+", text)

def fetch_page_facts(url):
    try:
        r = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0"
        })
        if r.status_code != 200:
            return {"error": f"{r.status_code}"}

        soup = BeautifulSoup(r.text, "lxml")

        texts = []

        if soup.title:
            texts.append(soup.title.text)

        h1 = soup.find("h1")
        if h1:
            texts.append(h1.text)

        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            texts.append(meta["content"])

        body_text = soup.get_text(" ", strip=True)
        texts.append(body_text)

        full_text = normalize(" ".join(texts))

        return {
            "text": full_text,
            "numbers": extract_numbers(full_text),
            "url": url
        }

    except Exception as e:
        return {"error": str(e)}

# =========================
# ЗАПРОС МЕНЕДЖЕРА
# =========================

def read_query():
    q = os.getenv("MANAGER_QUERY")
    if not q:
        fail("MANAGER_QUERY не задан")
    return q.strip()

def parse_query(q):
    links = extract_links(q)

    if links:
        print("🔗 Обнаружены ссылки — обрабатываем ПЕРВЫМИ")
        facts = []
        for link in links:
            data = fetch_page_facts(link)
            if "error" in data:
                print(f"❌ Ссылка {link} не обработана: {data['error']}")
            else:
                facts.append(data)

        if facts:
            combined_text = " ".join(f["text"] for f in facts)
            combined_numbers = {}
            for f in facts:
                combined_numbers.update(f["numbers"])

            return {
                "raw": q,
                "type": combined_text.split()[0],
                "numbers": combined_numbers,
                "qty": None,
                "allow_analogs": "аналог" in normalize(q),
                "source_link": facts[0]["url"]
            }

    # если ссылок нет
    n = normalize(q)
    return {
        "raw": q,
        "type": n.split()[0],
        "numbers": extract_numbers(n),
        "qty": int(re.search(r"(\d+)\s*шт", n).group(1)) if re.search(r"\d+\s*шт", n) else None,
        "allow_analogs": "аналог" in n,
        "source_link": ""
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

    print(f"✅ Найдено позиций: {len(chosen)}")
    print("ℹ️ Переходим к следующему шагу (Entero / таблица)")

    print("\n✅ ШАГ 8 УСПЕШНО ЗАВЕРШЁН")

if __name__ == "__main__":
    main()
