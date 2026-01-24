import os
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Price Orchestrator API",
    description="API для подбора оборудования и расчёта КП",
    version="1.0"
)

# =========================
# МОДЕЛЬ ЗАПРОСА
# =========================

class SearchRequest(BaseModel):
    query: str


# =========================
# ENDPOINT
# =========================

@app.post("/search")
def search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Пустой запрос")

    env = os.environ.copy()
    env["MANAGER_QUERY"] = req.query.strip()

    try:
        result = subprocess.run(
            ["python", "orchestrator.py"],
            capture_output=True,
            text=True,
            env=env,
            timeout=120
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "query": req.query,
        "output": result.stdout,
        "errors": result.stderr
    }


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Price Orchestrator API работает"
    }
