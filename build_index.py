import os
import re
import sqlite3
import tempfile
import subprocess
from pathlib import Path

import pandas as pd
import yadisk

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

# ================== TEXT HELPERS ==================

def normalize(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_numbers(text: str):
    if not text:
        return []
    result = []
    for m in re.findall(
        r"(\d+(?:[.,]\d+)?)\s*(кг|kg|л|l|мм|см|cm|м|kw|квт)?",
        str(text).lower(),
    ):
        value = float(m[0].replace(",", "."))
        unit = m[1] or ""
        result.append((value, unit))
    return result

# ================== DB ==================

def init_db():
    if os.path.exists(INDEX_DB):
        os.remove(INDEX_DB)

    conn = sqlite3.connect(INDEX_DB)
    cur = conn.cursor()

    cur.executescript("""
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

# ================== XLS → XLSX (FOR RP ONLY) ==================

def convert_xls_to_xlsx(xls_path: Path) -> Path:
    xlsx_path = xls_path.with_suffix(".xlsx")

    subprocess.run(
        [
            "libreoffice",
            "--headless",
            "--convert-to",
            "xlsx",
            "--outdir",
            str(xls_path.parent),
            str(xls_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return xlsx_path

# ================== MAIN INDEX BUILDER ==================

def build_index():
    print("🧠 Строим поисковый индекс")

    y = yadisk.YaDisk(token=YANDEX_TOKEN)
    conn = init_db()
    cur = conn.cursor()

    for source, remote_path in PRICES.items():
        print(f"\n📦 Источник: {source}")

        if not y.exists(remote_path):
            print(f"⚠️ Файл не найден на Яндекс.Диске: {remote_path}")
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / Path(remote_path).name
            y.download(remote_path, str(local_path))

            # ---------- ЧТЕНИЕ ФАЙЛА ----------
            try:
                if source == "rp":
                    print("🔥 RP: конвертация через LibreOffice")
                    xlsx_path = convert_xls_to_xlsx(local_path)
                    df = pd.read_excel(xlsx_path, engine="openpyxl")

                elif local_path.suffix.lower() == ".xls":
                    try:
                        df = pd.read_excel(local_path, engine="xlrd")
                    except Exception as e:
                        print(f"❌ {source}: битый XLS, пропускаем ({e})")
                        continue

                else:
                    df = pd.read_excel(local_path, engine="openpyxl")

            except Exception as e:
                print(f"❌ Ошибка чтения {source}: {e}")
                continue

            print(f"✅ Прочитано строк: {len(df)}")

            # ---------- ОБРАБОТКА ----------
            for _, row in df.iterrows():
                name = (
                    row.get("Наименование")
                    or row.get("Название")
                    or row.get("ТОВАР")
                    or row.get("name")
                    or ""
                )

                article = (
                    row.get("Артикул")
                    or row.get("Код")
                    or row.get("article")
                    or ""
                )

                name = str(name).strip()
                article = str(article).strip()

                if not name:
                    continue

                name_norm = normalize(name)

                cur.execute(
                    """
                    INSERT INTO items (source, article, name_raw, name_norm)
                    VALUES (?, ?, ?, ?)
                    """,
                    (source, article, name, name_norm),
                )

                item_id = cur.lastrowid

                for token in name_norm.split():
                    cur.execute(
                        "INSERT INTO tokens (item_id, token) VALUES (?, ?)",
                        (item_id, token),
                    )

                for value, unit in extract_numbers(name):
                    cur.execute(
                        "INSERT INTO numbers (item_id, value, unit) VALUES (?, ?, ?)",
                        (item_id, value, unit),
                    )

            conn.commit()
            print(f"🎯 {source}: индексирован")

    conn.close()
    print("\n🎉 index.db успешно создан")

# ================== ENTRY ==================

if __name__ == "__main__":
    build_index()
