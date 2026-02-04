import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(
    title="Price Orchestrator API",
    description="API для подбора оборудования и расчёта КП",
    version="1.0"
)

# =========================
# STATIC FILES (web.html)
# =========================
app.mount(
    "/",
    StaticFiles(directory="static", html=True),
    name="static"
)

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
    - plain-text таблицу (заглушка, пока без логики)
    """

    lines = []
    lines.append("Источник\tЗапрос\tАртикул\tНаименование\tНужно\tЦена розничная")
    lines.append("TEST\t" + query.replace("\n", " | ") + "\t-\t-\t-\t-")
    lines.append("")
    lines.append("ИТОГО\t\t\t\t\t")

    return "\n".join(lines)
