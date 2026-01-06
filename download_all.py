import os
import requests
import yadisk
from datetime import datetime
from playwright.sync_api import sync_playwright

# ================== НАСТРОЙКИ ==================

YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]

RP_LOGIN = os.environ["RP_LOGIN"]
RP_PASSWORD = os.environ["RP_PASSWORD"]

EQUIP_PRICE_URL = "https://prices.equip.me/direct/v1/d269df604f27bffdb630eab3d46595d8/2543039075/1/msk/1/in_stock/ru/metric/price__.xlsx"

ROSHOLOD_PRICE_URL = "https://rosholod.org/upload/ostatki.xls"  # <-- если ссылка изменится, заменишь тут

# ================== YANDEX ==================

y = yadisk.YaDisk(token=YANDEX_TOKEN)

def ensure_dir(path):
    if not y.exists(path):
        y.mkdir(path)

def today():
    return datetime.now().strftime("%Y-%m-%d")

# ================== EQUIP ==================

def download_equip_price():
    print("⬇️ Equip: скачиваем по прямой ссылке")
    ensure_dir("/prices/equip")

    r = requests.get(EQUIP_PRICE_URL, timeout=120)
    r.raise_for_status()

    local = "equip.xlsx"
    with open(local, "wb") as f:
        f.write(r.content)

    remote = f"/prices/equip/equip_{today()}.xlsx"
    y.upload(local, remote, overwrite=True)

    print("✅ Equip готов:", remote)

# ================== ROSHOLOD ==================

def download_rosholod_price():
    print("⬇️ Росхолод: скачиваем остатки (xls)")
    ensure_dir("/prices/rosholod")

    r = requests.get(ROSHOLOD_PRICE_URL, timeout=120)
    r.raise_for_status()

    local = "rosholod.xls"
    with open(local, "wb") as f:
        f.write(r.content)

    remote = f"/prices/rosholod/rosholod_{today()}.xls"
    y.upload(local, remote, overwrite=True)

    print("✅ Росхолод готов:", remote)

# ================== RP ==================

def download_rp_price():
    print("⬇️ RP: авторизация и скачивание XLS")
    ensure_dir("/prices/rp")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto("https://dc.rp.ru/", timeout=60000)

        page.fill("input[name='login']", RP_LOGIN)
        page.fill("input[name='password']", RP_PASSWORD)
        page.click("input[type='submit']")

        page.wait_for_load_state("networkidle")

        page.hover("text=Прайс")

        with page.expect_download() as d:
            page.click("text=XLS")

        download = d.value
        local = "rp.xls"
        download.save_as(local)

        browser.close()

    remote = f"/prices/rp/rp_{today()}.xls"
    y.upload(local, remote, overwrite=True)

    print("✅ RP готов:", remote)

# ================== MAIN ==================

def main():
    download_equip_price()
    download_rosholod_price()
    download_rp_price()

if __name__ == "__main__":
    main()
