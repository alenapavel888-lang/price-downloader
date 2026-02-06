from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(
    title="Price Orchestrator API",
    description="API для подбора оборудования и расчёта КП",
    version="1.0"
)

# =========================
# STATIC FILES
# =========================
app.mount("/static", StaticFiles(directory="static"), name="static")


# =========================
# WEB UI (МЕНЕДЖЕР)
# =========================
@app.get("/", response_class=HTMLResponse)
def manager_ui():
    """
    Главная страница менеджера
    """
    with open("static/web.html", "r", encoding="utf-8") as f:
        return f.read()


# =========================
# AGENT SEARCH API
# =========================
@app.post("/api/search", response_class=PlainTextResponse)
async def search(
    query: str = Form(""),
    file: UploadFile | None = File(None)
):
    """
    Точка входа агента
    """

    rows = []
    rows.append(
        "№\tИсточник\tЗапрос\tАртикул\tНаименование\tНужно\tНа складе\tЦена розничная"
    )
    rows.append(
        f"1\tTEST\t{query.replace(chr(10), ' | ')}\t-\t-\t-\t-\t-"
    )
    rows.append("")
    rows.append("ИТОГО\t\t\t\t\t\t\t")

    return "\n".join(rows)
