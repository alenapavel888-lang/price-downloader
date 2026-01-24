from fastapi import FastAPI, Body
from fastapi.responses import PlainTextResponse
import subprocess
import os

app = FastAPI(
    title="B2B Equipment Agent",
    description="Подбор оборудования и расчет КП",
    version="1.0"
)

@app.post("/search", response_class=PlainTextResponse)
def search(payload: dict = Body(...)):
    query = payload.get("query")

    if not query:
        return "❌ Ошибка: не передан запрос менеджера"

    env = os.environ.copy()
    env["MANAGER_QUERY"] = query

    result = subprocess.run(
        ["python", "orchestrator.py"],
        capture_output=True,
        text=True,
        env=env
    )

    if result.returncode != 0:
        return f"❌ Ошибка агента:\n{result.stderr}"

    return result.stdout
