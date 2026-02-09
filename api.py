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
    path = os.path.join("static", "web.html")
    if not os.path.exists(path):
        return "<h1>❌ Файл static/web.html не найден</h1>"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# =========================
# SEARCH API
# =========================
@app.post("/search", response_class=PlainTextResponse)
async def search(
    query: str = Form(""),
    file: UploadFile | None = File(None)
):
    """
    Принимает:
    - текст
    - файл (xlsx / csv / txt)
    Возвращает:
    - plain text таблицу (пока заглушка)
    """

    lines = []
    lines.append(
        "Источник\tЗапрос\tАртикул\tНаименование\tНужно\tЦена розничная"
    )

    if query:
        lines.append(f"TEST\t{query.replace(chr(10), ' | ')}\t-\t-\t-\t-")

    if file:
        lines.append(f"FILE\t{file.filename}\t-\t-\t-\t-")

    lines.append("")
    lines.append("ИТОГО\t\t\t\t\t")

    return "\n".join(lines)
