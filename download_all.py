import os
import requests
import yadisk
from datetime import datetime

# ================== НАСТРОЙКИ ==================

YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]

# ---------- EQUIP ----------
EQUIP_PRICE_URL = "https://prices.equip.me/direct/v1/d269df604f27bffdb630eab3d46595d8/2543039075/1/msk/1/in_stock/ru/metric/price__.xlsx"
EQUIP_LOCAL_FILE = "equip_price.xlsx"
EQUIP_YANDEX_DIR = "/prices/equip"

# ---------- ROSHOLOD ----------
ROSHOLOD_PRICE_URL = "ВСТАВЬ_ССЫЛКУ_РОСХОЛОД_ОСТАТКИ_XLS"
ROSHOLOD_LOCAL_FILE = "rosholod_ostatki.xls"
ROSHOLOD_YANDEX_DIR = "/prices/rosholod"

# ================== ОБЩИЕ ФУНКЦИИ ==================

def get_yandex():
    return yadisk.YaDisk(token=YANDEX_TOKEN)

def ensure_dir(y, path):
    if not y.exists(path):
        y.mkdir(path)

def upload_to_yandex(y, local_path, remote_path):
    y.upload(local_path, remote_path, overwrite=True)

# ================== EQUIP ==================

def download_equip_price(y):
    print("⬇️ Скачиваем прайс Equip по прямой ссылке")

    response = requests.get(EQUIP_PRICE_URL, timeout=120)
    response.raise_for_status()

    with open(EQUIP_LOCAL_FILE, "wb") as f:
        f.write(response.content)

    ensure_dir(y, EQUIP_YANDEX_DIR)

    today = datetime.now().strftime("%Y-%m-%d")
    remote_path = f"{EQUIP_YANDEX_DIR}/equip_{today}.xlsx"

    upload_to_yandex(y, EQUIP_LOCAL_FILE, remote_path)
    print(f"✅ Equip загружен: {remote_path}")

# ================== ROSHOLOD ==================

def download_rosholod_price(y):
    print("⬇️ Скачиваем Остатки Росхолод")

    response = requests.get(ROSHOLOD_PRICE_URL, timeout=120)
    response.raise_for_status()

    with open(ROSHOLOD_LOCAL_FILE, "wb") as f:
        f.write(response.content)

    ensure_dir(y, ROSHOLOD_YANDEX_DIR)

    today = datetime.now().strftime("%Y-%m-%d")
    remote_path = f"{ROSHOLOD_YANDEX_DIR}/rosholod_{today}.xls"

    upload_to_yandex(y, ROSHOLOD_LOCAL_FILE, remote_path)
    print(f"✅ Росхолод загружен: {remote_path}")

# ================== MAIN ==================

def main():
    y = get_yandex()

    download_equip_price(y)
    download_rosholod_price(y)

if __name__ == "__main__":
    main()
