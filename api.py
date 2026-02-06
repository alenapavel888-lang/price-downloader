import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Price Orchestrator API",
    description="API для подбора оборудования и расчёта КП",
    version="1.0"
)

# =========================
# STATIC (WEB UI)
# =========================
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def web_ui():
    with open("static/web.html", "r", encoding="utf-8") as f:
        return f.read()

# =========================
# SEARCH ENDPOINT (AGENT)
# =========================
@app.post("/api/search", response_class=PlainTextResponse)
async def search(
    query: str = Form(""),
    file: UploadFile | None = File(None)
):
    """
    Это точка входа АГЕНТА.
    Сюда будет подключён orchestrator.py
    """

    lines = []
    lines.append(
        "№\tИсточник\tЗапрос\tАртикул\tНаименование\tНужно\tНа складе\tЦена розничная"
    )
    lines.append(
        f"1\tTEST\t{query.replace(chr(10), ' | ')}\t-\t-\t-\t-\t-"
    )
    lines.append("")
    lines.append("ИТОГО\t\t\t\t\t\t\t")

    return "\n".join(lines)
