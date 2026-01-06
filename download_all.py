import os
import requests
import yadisk
from datetime import datetime
from playwright.sync_api import sync_playwright

# ================== SECRETS ==================

YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]
RP_LOGIN = os.environ["RP_LOGIN"]
RP_PASSWORD = os.environ["RP_PASSWORD"]

# ================== PATHS ==================

BASE_DIR = os.getcwd()

# ================== EQUIP ==================

EQUIP_PRICE_URL = "https://prices.equip.me/direct/v1/d269df604f27bffdb630eab3d46595d8/2543039075/1/msk/1/in_stock/ru/metric/price__.xlsx"

# ================== COMMON ==================

def upload_to_yandex(local_path, remote_path):
    y = yadisk.YaDisk(token=YANDEX_TOKEN)
    remote_dir = os.path.dirname(remote_path)

    if not y.exists(remote_dir):
        y.mkdir(remote_dir)

    y.upload(local_path, remote_path, overwrite=True)

# ================== EQUIP ==================

def download_equip_price():
    print("⬇️ Equip: скачиваем по прямой ссылке")

    r = requests.get(EQUIP_PRICE_URL, timeout=120)
    r.raise_for_status()

    local_file = os.path.join(BASE_DIR, "equip_price.xlsx")
    with open(local_file, "wb") as f:
        f.write(r.content)

    today = datetime.now().strftime("%Y-%m-%d")
    remote = f"/prices/equip/equip_{today}.xlsx"

    upload_to_yandex(local_file, remote)
    print(f"✅ Equip готов: {remote}")

# ================== ROSHOLOD ==================

def download_rosholod_price():
    print("⬇️ Росхолод: остатки (xls)")

    local_file = os.path.join(BASE_DIR, "rosholod_ostatki.xls")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto("https://rosholod.org/downloads/price-lists/", timeout=60000)

        with page.expect_download() as d:
            page.locator("text=Остатки (xls)").first.click()

        d.value.save_as(local_file)
        browser.close()

    today = datetime.now().strftime("%Y-%m-%d")
    remote = f"/prices/rosholod/rosholod_{today}.xls"

    upload_to_yandex(local_file, remote)
    print(f"✅ Росхолод готов: {remote}")

# ================== RP ==================

def download_rp_price():
    print("⬇️ RP: логинимся и скачиваем прайс")

    local_file = os.path.join(BASE_DIR, "rp_price.xlsx")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto("https://dc.rp.ru/", timeout=60000)

        page.fill("input[name='login']", RP_LOGIN)
        page.fill("input[name='password']", RP_PASSWORD)
        page.click("text=Авторизоваться")

        page.wait_for_timeout(3000)

        page.hover("text=Прайс")

        with page.expect_download() as d:
            page.click("text=Excel")

        d.value.save_as(local_file)
        browser.close()

    today = datetime.now().strftime("%Y-%m-%d")
    remote = f"/prices/rp/rp_{today}.xlsx"

    upload_to_yandex(local_file, remote)
    print(f"✅ RP готов: {remote}")

# ================== MAIN ==================

def main():
    download_equip_price()
    download_rosholod_price()
    download_rp_price()

if __name__ == "__main__":
    main()
