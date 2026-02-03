import os
import sqlite3
import pandas as pd
import re

DATA_DIR = "data"
INDEX_DB = "index.db"

FILES = {
    "equip": "equip.xlsx",
    "rosholod": "rosholod.xls",
    "rp": "rp.xls",
    "smirnov": "smirnov.xlsx",
    "trade_design": "td.xlsx",
    "bio": "bio.xlsx",
}

def normalize(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(t).lower())).strip()

def init_db():
    conn = sqlite3.connect(INDEX_DB)
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS items;
    CREATE TABLE items (
        id INTEGER PRIMARY KEY,
        source TEXT,
        article TEXT,
        name TEXT,
        name_norm TEXT
    );
    """)
    conn.commit()
    return conn

def main():
    conn = init_db()
    cur = conn.cursor()

    for src, fname in FILES.items():
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            print(f"⚠️ Нет файла {path}")
            continue

        df = pd.read_excel(path, engine="xlrd" if fname.endswith(".xls") else "openpyxl")
        print(f"{src}: {len(df)} строк")

        for _, r in df.iterrows():
            name = str(
                r.get("Наименование")
                or r.get("Название")
                or r.get("ТОВАР")
                or ""
            ).strip()
            if not name:
                continue

            article = str(r.get("Артикул") or "").strip()
            cur.execute(
                "INSERT INTO items (source, article, name, name_norm) VALUES (?,?,?,?)",
                (src, article, name, normalize(name))
            )

    conn.commit()
    conn.close()
    print("✅ index.db построен")

if __name__ == "__main__":
    main()
