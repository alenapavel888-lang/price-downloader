import os
import sqlite3
import pandas as pd
import re

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

def normalize(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s×x]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

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

print("🗑 Удаляем старый index.db (если есть)")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("📦 Создаём таблицу items")

cur.execute("""
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier TEXT,
    name TEXT,
    text TEXT,
    brand TEXT,
    kg REAL,
    liters REAL,
    levels REAL,
    kw REAL,
    dealer_price REAL,
    retail_price REAL,
    availability TEXT,
    article TEXT
)
""")

total = 0

for supplier, file in SUPPLIERS.items():
    path = os.path.join(DATA_DIR, file)
    print(f"📄 Читаем {supplier}: {file}")

    df = pd.read_excel(path, dtype=str).fillna("")

    for _, row in df.iterrows():
        combined = normalize(" ".join(map(str, row.values)))
        nums = extract_numbers(combined)

        def num(k): return nums.get(k)

        def price(v):
            try:
                return float(str(v).replace(",", "."))
            except:
                return None

        name = row.get("Наименование","")
        brand = normalize(name).split()[0] if name else ""

        cur.execute("""
        INSERT INTO items (
            supplier, name, text, brand,
            kg, liters, levels, kw,
            dealer_price, retail_price,
            availability, article
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            supplier,
            name,
            combined,
            brand,
            num("kg"),
            num("liters"),
            num("levels"),
            num("kw"),
            price(row.get("Цена дилерская") or row.get("Дилерская цена")),
            price(row.get("Цена розничная") or row.get("Розничная цена")),
            row.get("Наличие",""),
            row.get("Артикул","")
        ))

        total += 1

conn.commit()
conn.close()

print(f"✅ index.db собран, записей: {total}")
