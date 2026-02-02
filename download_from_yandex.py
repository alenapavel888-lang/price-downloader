import os
import requests
from pathlib import Path

YANDEX_API = "https://cloud-api.yandex.net/v1/disk"
TOKEN = os.getenv("YANDEX_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ YANDEX_TOKEN не найден в GitHub Secrets")

HEADERS = {
    "Authorization": f"OAuth {TOKEN}"
}

# ЧЁТКО ЗАДАННЫЕ ФАЙЛЫ НА ЯНДЕКС.ДИСКЕ
FILES = {
    "equip": {
        "remote": "/prices/equip/equip.xlsx",
        "local": "data/equip.xlsx",
    },
    "bio": {
        "remote": "/prices/bio/bio.xlsx",
        "local": "data/bio.xlsx",
    },
    "rosholod": {
        "remote": "/prices/rosholod/rosholod.xls",
        "local": "data/rosholod.xls",
    },
    "rp": {
        "remote": "/prices/rp/rp.xls",
        "local": "data/rp.xls",
    },
    "smirnov": {
        "remote": "/prices/smirnov/smirnov.xlsx",
        "local": "data/smirnov.xlsx",
    },
    "trade_design": {
        "remote": "/prices/trade_design/td.xlsx",
        "local": "data/td.xlsx",
    },
}

def get_download_link(path: str) -> str:
    r = requests.get(
        f"{YANDEX_API}/resources/download",
        headers=HEADERS,
        params={"path": path},
    )
    r.raise_for_status()
    return r.json()["href"]

def download_file(remote_path: str, local_path: str):
    print(f"⬇️  Скачиваем: {remote_path}")

    url = get_download_link(remote_path)

    r = requests.get(url, stream=True)
    r.raise_for_status()

    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    with open(local_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"✅ Готово: {local_path}")

def main():
    print("🔗 Подключение к Яндекс.Диску")

    for name, cfg in FILES.items():
        print(f"\n📦 Поставщик: {name}")
        download_file(cfg["remote"], cfg["local"])

    print("\n🎉 Все прайсы успешно скачаны")

if __name__ == "__main__":
    main()
