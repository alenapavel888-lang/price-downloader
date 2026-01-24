import os
import sqlite3
import pandas as pd
import re
import json

# =========================
# КОНФИГУРАЦИЯ
# =========================

DATA_DIR = "data"
DB_PATH = "index.db"

SUPPLIERS = {
    "equip": "equip.xlsx",
    "bio": "bio.xlsx",
    "rp": "rp.xlsx",
    "rosholod": "rosholod.xlsx",
    "smirnov": "smirnov.xlsx",
    "trade_design": "td.xlsx",
}

# =========================
# УТИЛИТЫ
# =========================

def normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s×x]", " ", str(text).lower())).strip()

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

def to_float(v):
    try:
        return float(str(v).replace(",", "."))
    except:
        return None

# =========================
# СБОРКА ИНДЕКСА
# =========================

def build_index():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier TEXT,
            article TEXT,
            name TEXT,
            normalized TEXT,
            brand TEXT,
            numbers TEXT,
            dealer_price REAL,
            retail_price REAL,
            stock TEXT,
            link TEXT
        )
    """)

    total = 0

    for supplier, file in SUPPLIERS.items():
        path = os.path.join(DATA_DIR, file)
        if not os.path.isfile(path):
            print(f"⚠️ Пропущен {file}")
            continue

        df = pd.read_excel(path, dtype=str).fillna("")
        print(f"📄 {supplier}: {len(df)} строк")

        for _, r in df.iterrows():
            text = normalize(" ".join(map(str, r.values)))
            numbers = extract_numbers(text)

            cur.execute("""
                INSERT INTO items (
                    supplier, article, name, normalized, brand,
                    numbers, dealer_price, retail_price, stock, link
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                supplier,
                r.get("Артикул", ""),
                r.get("Наименование", ""),
                text,
                text.split()[0] if text else "",
                json.dumps(numbers, ensure_ascii=False),
                to_float(r.get("Цена дилерская") or r.get("Дилерская цена")),
                to_float(r.get("Цена розничная") or r.get("Розничная цена")),
                r.get("Наличие", ""),
                r.get("Ссылка", "")
            ))

            total += 1

    conn.commit()
    conn.close()

    print(f"✅ index.db создан. Записей: {total}")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    build_index()
