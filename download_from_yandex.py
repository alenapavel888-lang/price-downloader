import os
import requests
from pathlib import Path

YANDEX_API = "https://cloud-api.yandex.net/v1/disk"
TOKEN = os.getenv("YANDEX_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ YANDEX_TOKEN не найден в окружении")

HEADERS = {"Authorization": f"OAuth {TOKEN}"}

BASE_REMOTE_DIR = "/prices"
BASE_LOCAL_DIR = Path("data")

SUPPLIERS = [
    "equip",
    "bio",
    "rosholod",
    "rp",
    "smirnov",
    "trade_design",
]

def api_get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()

def download_file(remote_path: str, local_path: Path):
    meta = api_get(f"{YANDEX_API}/resources/download", {"path": remote_path})
    url = meta["href"]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

def download_folder(remote_folder: str, local_folder: Path):
    items = api_get(
        f"{YANDEX_API}/resources",
        {"path": remote_folder, "limit": 1000}
    )["embedded"]["items"]

    for item in items:
        if item["type"] != "file":
            continue
        name = item["name"]
        remote_path = item["path"]
        local_path = local_folder / name
        print(f"⬇️  {remote_path}")
        download_file(remote_path, local_path)

def main():
    for supplier in SUPPLIERS:
        print(f"\n📦 Поставщик: {supplier}")
        download_folder(
            f"{BASE_REMOTE_DIR}/{supplier}",
            BASE_LOCAL_DIR / supplier
        )

    print("\n✅ Все прайсы загружены из Яндекс.Диска")

if __name__ == "__main__":
    main()
