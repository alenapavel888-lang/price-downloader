import sqlite3
import re
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

DB_PATH = "index.db"

app = FastAPI(title="Equipment Selector API")

# =========================
# UTILITIES
# =========================

def normalize(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_numbers(text: str):
    nums = []
    for m in re.findall(r"(\d+(?:[.,]\d+)?)\s*(кг|kg|л|l|мм|см|cm|м)?", text.lower()):
        nums.append((float(m[0].replace(",", ".")), m[1] or ""))
    return nums

# =========================
# INPUT SCHEMA
# =========================

class SearchRequest(BaseModel):
    query: str
    quantity: int | None = None
    allow_analogs: bool = False

# =========================
# CORE SEARCH
# =========================

def search_items(query: str, allow_analogs: bool):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    q_norm = normalize(query)
    tokens = q_norm.split()
    numbers = extract_numbers(query)

    sql = """
    SELECT items.item_id, items.source, items.article, items.name_raw
    FROM items
    JOIN tokens ON tokens.item_id = items.item_id
    WHERE tokens.token IN ({})
    GROUP BY items.item_id
    ORDER BY COUNT(tokens.token) DESC
    LIMIT {}
    """.format(
        ",".join("?" * len(tokens)),
        3 if allow_analogs else 1
    )

    rows = cur.execute(sql, tokens).fetchall()
    conn.close()
    return rows

# =========================
# TABLE BUILDER
# =========================

COLUMNS = [
    "№","Источник","Запрос","Артикул","Наименование","Нужно","На складе",
    "Цена дилерская","Валюта","Цена розничная","Валюта",
    "Цена Entero","Разница %","Наценка %","Валовая прибыль",
    "Сумма","Размеры (Ш×Г×В)","Вес (кг)","Объём (м³)","Ссылка"
]

def build_table(items, query, qty):
    rows = []
    total_qty = 0
    total_sum = 0
    total_profit = 0

    for i, it in enumerate(items, 1):
        retail = 0
        dealer = 0

        profit = retail - dealer
        summa = retail * (qty or 1)

        total_qty += qty or 1
        total_sum += summa
        total_profit += profit

        rows.append([
            i,
            it["source"],
            query,
            it["article"],
            it["name_raw"],
            qty or "–",
            "–",
            dealer or "",
            "RUB",
            retail or "",
            "RUB",
            "❌ Не найдено",
            "",
            "",
            profit or "",
            summa or "",
            "",
            "",
            "",
            ""
        ])

    output = []
    output.append("\t".join(COLUMNS))
    for r in rows:
        output.append("\t".join(map(str, r)))

    output.append("\t".join([
        "ИТОГО","","","",
        "",
        total_qty,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        total_profit,
        total_sum,
        "",
        "",
        "",
        ""
    ]))

    return "```\n" + "\n".join(output) + "\n```"

# =========================
# API ENDPOINT
# =========================

@app.post("/search")
def search(req: SearchRequest):
    items = search_items(req.query, req.allow_analogs)

    if not items:
        return {
            "result": "```\n❌ Ничего не найдено\n```"
        }

    table = build_table(items, req.query, req.quantity)
    return {"result": table}
