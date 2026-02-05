import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# =========================
# APP
# =========================

app = FastAPI(
    title="Price Orchestrator API",
    description="API для подбора оборудования и расчёта КП",
    version="1.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# =========================
# STATIC FILES
# =========================
# web.html будет доступен по /ui

app.mount(
    "/ui",
    StaticFiles(directory=STATIC_DIR, html=True),
    name="ui"
)

# =========================
# ROOT (WEB UI)
# =========================

@app.get("/", response_class=HTMLResponse)
def root():
    """
    Главная страница для менеджера
    """
    index_path = os.path.join(STATIC_DIR, "web.html")
    if not os.path.exists(index_path):
        return "<h1>web.html не найден</h1>"

    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

# =========================
# API MODELS
# =========================

class SearchRequest(BaseModel):
    query: str

# =========================
# API ENDPOINTS
# =========================

@app.post("/search", response_class=PlainTextResponse)
async def search(
    query: str = Form(""),
    file: UploadFile | None = File(None)
):
    """
    Принимает:
    - текстовый запрос
    - файл (xlsx / csv / txt)
    Возвращает:
    - plain-text таблицу (пока заглушка)
    """

    rows = []
    rows.append(
        "Источник\tЗапрос\tАртикул\tНаименование\tНужно\tНа складе\tЦена дилерская\tЦена розничная"
    )

    rows.append(
        f"TEST\t{query.replace(chr(10), ' | ')}\t-\t-\t-\t-\t-\t-"
    )

    rows.append("")
    rows.append("ИТОГО\t\t\t\t\t\t\t")

    return "\n".join(rows)

# =========================
# HEALTH CHECK
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}
