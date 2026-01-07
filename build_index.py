import os
import sqlite3
import yadisk
import pandas as pd
import re
import tempfile

# ================== CONFIG ==================

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

# ================== NORMALIZATION ==================

def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_numbers(text: str):
    """
    Извлекаем числа + единицы измерения из текста
    """
    if not text:
        return []
    out = []
    for m in re.findall(
        r"(\d+(?:[.,]\d+)?)\s*(кг|kg|л|l|мм|см|cm|м|kw|квт|w)?",
        text.lower()
    ):
        value = float(m[0].replace(",", "."))
        unit = m[1] or ""
        out.append((value, unit))
    return out

# ================== DB ==================

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

    CREATE INDEX idx_items_name ON items(name_norm);
    CREATE INDEX idx_tokens_token ON tokens(token);
    CREATE INDEX idx_numbers_value ON numbers(value);
    """)

    conn.commit()
    return conn

# ================== INDEX BUILDER ==================

def read_excel_safely(path: str) -> pd.DataFrame:
    """
    Универсальное чтение xls/xlsx
    """
    try:
        return pd.read_excel(path)
    except Exception as e:
        raise RuntimeError(f"Н
