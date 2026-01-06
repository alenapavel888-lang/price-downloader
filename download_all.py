import os
import requests
import yadisk
from datetime import datetime

# === НАСТРОЙКИ ===

YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]

EQUIP_PRICE_URL = "https://prices.equip.me/direct/v1/d269df604f27bffdb630eab3d46595d8/2543039075/1/msk/1/in_stock/ru/metric/price__.xlsx"

LOCAL_FILE = "equip_price.xlsx"
YANDEX_DIR = "/prices/equip"

# === ФУНКЦИИ ===

def upload_to_yandex(local_path, remote_path):
    y = yadisk.YaDisk(token=YANDEX_TOKEN)
    if not y.exists(YANDEX_DIR):
        y.mkdir(YANDEX_DIR)
    y.upload(local_path, remote_path, overwrite=True)

def download_equip_price():
    print("⬇️ Скачиваем прайс Equip по прямой ссылке")

    response = requests.get(EQUIP_PRICE_URL, timeout=120)
    response.raise_for_status()

    with open(LOCAL_FILE, "wb") as f:
        f.write(response.content)

    today = datetime.now().strftime("%Y-%m-%d")
    remote_path = f"{YANDEX_DIR}/equip_{today}.xlsx"

    upload_to_yandex(LOCAL_FILE, remote_path)
    print(f"✅ Прайс Equip загружен в Яндекс Диск: {remote_path}")

def main():
    download_equip_price()

if __name__ == "__main__":
    main()
