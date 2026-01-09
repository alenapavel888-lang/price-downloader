import os
import sqlite3
import yadisk
import pandas as pd
import re
import tempfile
import subprocess

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

# ================== HELPERS ==================

def normalize(text):
    if not text:
        return ""
    text = str(text).lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_numbers(text):
    if not text:
        return []
    out = []
    for m in re.findall(
        r"(\d+(?:[.,]\d+)?)\s*(кг|kg|л|l|мм|см|cm|м|kw|квт)?",
        str(text).lower()
    ):
        out.append((float(m[0].replace(",", ".")), m[1] or ""))
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
    """)

    conn.commit()
    return conn

# ================== XLS → XLSX (LibreOffice) ==================

def convert_xls_to_xlsx(xls_path: str) -> str:
    xlsx_path = xls_path + ".xlsx"

    subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "xlsx",
            xls_path,
            "--outdir",
            os.path.dirname(xls_path),
        ],
        check=True,
    )

    return xlsx_path

# ================== BUILD INDEX ==================

def build_index():
    print("🧠 Строим индекс")
    y = yadisk.YaDisk(token=YANDEX_TOKEN)

    conn = init_db()
    cur = conn.cursor()

    for source, remote_path in PRICES.items():
        print(f"\n📦 {source}")

        if not y.exists(remote_path):
            print(f"⚠️ Файл не найден: {remote_path}")
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, os.path.basename(remote_path))
            y.download(remote_path, local_path)

            try:
                if local_path.lower().endswith(".xls"):
                    xlsx_path = convert_xls_to_xlsx(local_path)
                else:
                    xlsx_path = local_path

                df = pd.read_excel(xlsx_path, engine="openpyxl")

            except Exception as e:
                print(f"❌ Ошибка чтения {source}: {e}")
                continue

        print(f"строк: {len(df)}")

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
                "INSERT INTO items (source, article, name_raw, name_norm) VALUES (?,?,?,?)",
                (source, article, name, name_norm),
            )
            item_id = cur.lastrowid

            for token in name_norm.split():
                cur.execute(
                    "INSERT INTO tokens (item_id, token) VALUES (?,?)",
                    (item_id, token),
                )

            for value, unit in extract_numbers(name):
                cur.execute(
                    "INSERT INTO numbers (item_id, value, unit) VALUES (?,?,?)",
                    (item_id, value, unit),
                )

        conn.commit()
        print(f"✅ {source} готов")

    conn.close()
    print("\n🎉 Индекс index.db успешно создан")

# ================== ENTRY ==================

if __name__ == "__main__":
    build_index()
