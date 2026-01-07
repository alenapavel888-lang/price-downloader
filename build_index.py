import os
import sqlite3
import yadisk
import pandas as pd
import re

YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]
INDEX_DB = "index.db"

PRICES = {
    "equip": "/prices/equip/equip.xlsx",
    "rosholod": "/prices/rosholod/rosholod.xls",
    "rp": "/prices/rp/rp.xls",
    "smirnov": "/prices/smirnov/smirnov.xlsx",
    "trade_design": "/prices/trade_design/td.xlsx",
    "bio": "/prices/bio/bio.xlsx",
}

def normalize(text):
    if not text:
        return ""
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_numbers(text):
    if not text:
        return []
    out = []
    for m in re.findall(r"(\d+(?:[.,]\d+)?)\s*(кг|kg|л|l|мм|см|cm|kw|квт)?", text.lower()):
        out.append((float(m[0].replace(",", ".")), m[1] or ""))
    return out

def init_db():
    conn = sqlite3.connect(INDEX_DB)
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS items;
    DROP TABLE IF EXISTS tokens;
    DROP TABLE IF EXISTS numbers;

    CREATE TABLE items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        article TEXT,
        name_raw TEXT,
        name_norm TEXT
    );

    CREATE TABLE tokens (
        item_id INTEGER,
        token TEXT
    );

    CREATE TABLE numbers (
        item_id INTEGER,
        value REAL,
        unit TEXT
    );
    """)
    conn.commit()
    return conn

def build_index():
    y = yadisk.YaDisk(token=YANDEX_TOKEN)
    conn = init_db()
    cur = conn.cursor()

    for source, path in PRICES.items():
        print(f"Читаем {source}")
        local = f"/tmp/{source}.xlsx"
        y.download(path, local)

        df = pd.read_excel(local)

        for _, row in df.iterrows():
            name = str(row.get("Наименование") or row.get("name") or "")
            article = str(row.get("Артикул") or row.get("article") or "")
            if not name.strip():
                continue

            name_norm = normalize(name)
            cur.execute(
                "INSERT INTO items (source, article, name_raw, name_norm) VALUES (?,?,?,?)",
                (source, article, name, name_norm),
            )
            item_id = cur.lastrowid

            for token in name_norm.split():
                cur.execute("INSERT INTO tokens VALUES (?,?)", (item_id, token))

            for val, unit in extract_numbers(name):
                cur.execute("INSERT INTO numbers VALUES (?,?,?)", (item_id, val, unit))

        conn.commit()

    conn.close()
    print("Индекс создан")

if __name__ == "__main__":
    build_index()
