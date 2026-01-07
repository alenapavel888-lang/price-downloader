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

EQUIP_PRICE_URL = (
    "https://prices.equip.me/direct/v1/"
    "d269df604f27bffdb630eab3d46595d8/"
    "2543039075/1/msk/1/in_stock/ru/metric/price__.xlsx"
)

# ================== SMIRNOV ==================

SMIRNOV_PRICE_URL = "https://files.smirnov.ooo/Prays-list%20po%20ostatkam%20XLSX.xlsx"

# ================== TRADE DESIGN ==================
# ⚠️ ВАЖНО: прямая ссылка, без логина
TD_PRICE_URL = "https://api.t-d.ru/api/ka-nomenclature/download-excel/with-filters/ka_nomenclature_td?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczpcL1wvYXBpLnQtZC5ydVwvYXBpXC9hdXRoLWZyb250XC9sb2dpbiIsImlhdCI6MTc2NzcyMTk4MywiZXhwIjoxNzY4MzI2NzgzLCJuYmYiOjE3Njc3MjE5ODMsImp0aSI6IkVLWmg4Y3dYdTJqSW5ONE4iLCJzdWIiOjQxNCwicHJ2IjoiMjNiZDVjODk0OWY2MDBhZGIzOWU3MDFjNDAwODcyZGI3YTU5NzZmNyJ9.k-JS3d7o9HF1U3R-d926ypbfTb7aigTJgfZaPd_D_tg&warehouses%5B0%5D=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0&is_on_balance=true&extension=xlsx"

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
    upload_to_yandex(local_file, f"/prices/equip/equip_{today}.xlsx")
    print("✅ Equip готов")

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
    upload_to_yandex(local_file, f"/prices/rosholod/rosholod_{today}.xls")
    print("✅ Росхолод готов")

# ================== RP ==================

def download_rp_price():
    print("⬇️ RP: логинимся и скачиваем прайс")

    local_file = os.path.join(BASE_DIR, "rp_price.xls")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto("https://dc.rp.ru/", timeout=60000)
        page.locator("input[type='text']").first.fill(RP_LOGIN)
        page.locator("input[type='password']").first.fill(RP_PASSWORD)
        page.locator("input[type='password']").press("Enter")

        page.wait_for_load_state("networkidle")
        page.hover("text=Прайс")

        with page.expect_download() as d:
            page.locator("text=Прайс лист в формате xls").click()

        d.value.save_as(local_file)
        browser.close()

    today = datetime.now().strftime("%Y-%m-%d")
    upload_to_yandex(local_file, f"/prices/rp/rp_{today}.xls")
    print("✅ RP готов")

# ================== SMIRNOV ==================

def download_smirnov_price():
    print("⬇️ Смирнов: остатки")

    r = requests.get(SMIRNOV_PRICE_URL, timeout=120)
    r.raise_for_status()

    local_file = os.path.join(BASE_DIR, "smirnov.xlsx")
    with open(local_file, "wb") as f:
        f.write(r.content)

    today = datetime.now().strftime("%Y-%m-%d")
    upload_to_yandex(local_file, f"/prices/smirnov/smirnov_{today}.xlsx")
    print("✅ Смирнов готов")

# ================== TRADE DESIGN ==================

def download_td_price():
    print("⬇️ Торговый дизайн: скачиваем по прямой ссылке")

    r = requests.get(TD_PRICE_URL, timeout=120)
    r.raise_for_status()

    local_file = os.path.join(BASE_DIR, "trade_design.xlsx")
    with open(local_file, "wb") as f:
        f.write(r.content)

    today = datetime.now().strftime("%Y-%m-%d")
    upload_to_yandex(local_file, f"/prices/trade_design/td_{today}.xlsx")
    print("✅ Торговый дизайн готов")

# ================== MAIN ==================

def main():
    download_equip_price()
    download_rosholod_price()
    download_rp_price()
    download_smirnov_price()
    download_td_price()

if __name__ == "__main__":
    main()
