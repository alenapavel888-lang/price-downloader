import sqlite3
import re
from fastapi import FastAPI, Query
from typing import List

DB_PATH = "index.db"

app = FastAPI(
    title="Smart Equipment Agent",
    description="Умный подбор оборудования и цен",
    version="1.0"
)

# =========================
# УТИЛИТЫ
# =========================

def normalize(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_numbers(text: str):
    nums = {}
    patterns = {
        "kg": r"(\d+(?:[.,]\d+)?)\s*кг",
        "liters": r"(\d+(?:[.,]\d+)?)\s*л",
        "levels": r"(\d+)\s*уров",
        "kw": r"(\d+(?:[.,]\d+)?)\s*квт",
    }
    for k, p in patterns.items():
        m = re.search(p, text)
        if m:
            nums[k] = float(m.group(1).replace(",", "."))
    return nums

# =========================
# ГЛАВНАЯ СТРАНИЦА
# =========================

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Smart Equipment Agent is running",
        "endpoints": [
            "/search?q=мясорубка 70 кг",
        ]
    }

# =========================
# ПОИСК
# =========================

@app.get("/search")
def search(
    q: str = Query(..., description="Запрос менеджера"),
    limit: int = 5
):
    query_raw = q
    query_norm = normalize(q)
    tokens = query_norm.split()
    numbers = extract_numbers(query_norm)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ---- SQL поиск по токенам
    placeholders = ",".join("?" * len(tokens))

    sql = f"""
    SELECT i.item_id, i.source, i.article, i.name_raw
    FROM items i
    JOIN tokens t ON t.item_id = i.item_id
    WHERE t.token IN ({placeholders})
    GROUP BY i.item_id
    ORDER BY COUNT(*) DESC
    LIMIT ?
    """

    rows = cur.execute(sql, (*tokens, limit)).fetchall()
    conn.close()

    # ---- Формирование таблицы
    columns = [
        "№","Источник","Запрос","Артикул","Наименование",
        "Нужно","На складе",
        "Цена дилерская","Валюта",
        "Цена розничная","Валюта",
        "Цена Entero","Разница %",
        "Наценка %","Валовая прибыль",
        "Сумма",
        "Размеры (Ш×Г×В)",
        "Вес (кг)","Объём (м³)",
        "Ссылка"
    ]

    table = []
    n = 1

    for r in rows:
        table.append([
            n,
            r["source"],
            query_raw,
            r["article"],
            r["name_raw"],
            "–",
            "",
            "",
            "",
            "",
            "",
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

    # ---- Итоговая строка
    table.append([
        "ИТОГО","","","","",
        "","","","","",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        ""
    ])

    # ---- Plain text output
    lines = []
    lines.append("\t".join(columns))
    for row in table:
        lines.append("\t".join(map(str, row)))

    return {
        "query": query_raw,
        "rows_found": len(rows),
        "table": "```\\n" + "\\n".join(lines) + "\\n```"
    }
