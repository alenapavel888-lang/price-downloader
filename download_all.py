import os
import requests
import yadisk
from datetime import datetime
from playwright.sync_api import sync_playwright
from openpyxl import Workbook   # 👈 ДОБАВЛЕНО

# ================== SECRETS ==================

YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]

RP_LOGIN = os.environ["RP_LOGIN"]
RP_PASSWORD = os.environ["RP_PASSWORD"]

BIO_LOGIN = os.environ["BIO_LOGIN"]
BIO_PASSWORD = os.environ["BIO_PASSWORD"]

TD_API_TOKEN = os.environ["TD_API_TOKEN"]

# ================== PATHS ==================

BASE_DIR = os.getcwd()

# ================== URLS ==================

EQUIP_PRICE_URL = (
    "https://prices.equip.me/direct/v1/"
    "d269df604f27bffdb630eab3d46595d8/"
    "2543039075/1/msk/1/in_stock/ru/metric/price__.xlsx"
)

SMIRNOV_PRICE_URL = "https://files.smirnov.ooo/Prays-list%20po%20ostatkam%20XLSX.xlsx"

TD_API_URL = (
    "https://api.t-d.ru/api/ka-nomenclature/"
    "download-excel/with-filters/ka_nomenclature_td?extension=xlsx"
)

BIO_API_URL = "http://api.bioshop.ru:8030/products"

# ================== HELPERS ==================

def today():
    return datetime.now().strftime("%Y-%m-%d")

def upload_to_yandex(local_path, remote_path):
    y = yadisk.YaDisk(token=YANDEX_TOKEN)
    remote_dir = os.path.dirname(remote_path)
    if not y.exists(remote_dir):
        y.mkdir(remote_dir)
    y.upload(local_path, remote_path, overwrite=True)

# ================== EQUIP ==================

def download_equip_price():
    print("⬇️ Equip")
    r = requests.get(EQUIP_PRICE_URL, timeout=120)
    r.raise_for_status()
    local = os.path.join(BASE_DIR, "equip.xlsx")
    with open(local, "wb") as f:
        f.write(r.content)
    upload_to_yandex(local, f"/prices/equip/equip_{today()}.xlsx")
    print("✅ Equip готов")

# ================== ROSHOLOD ==================

def download_rosholod_price():
    print("⬇️ Росхолод")
    local = os.path.join(BASE_DIR, "rosholod.xls")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(accept_downloads=True).new_page()
        page.goto("https://rosholod.org/downloads/price-lists/")
        with page.expect_download() as d:
            page.locator("text=Остатки (xls)").first.click()
        d.value.save_as(local)
        browser.close()
    upload_to_yandex(local, f"/prices/rosholod/rosholod_{today()}.xls")
    print("✅ Росхолод готов")

# ================== RP ==================

def download_rp_price():
    print("⬇️ RP")
    local = os.path.join(BASE_DIR, "rp.xls")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(accept_downloads=True).new_page()
        page.goto("https://dc.rp.ru/")
        page.locator("input[type='text']").first.fill(RP_LOGIN)
        page.locator("input[type='password']").first.fill(RP_PASSWORD)
        page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle")
        page.hover("text=Прайс")
        with page.expect_download() as d:
            page.locator("text=Прайс лист в формате xls").click()
        d.value.save_as(local)
        browser.close()
    upload_to_yandex(local, f"/prices/rp/rp_{today()}.xls")
    print("✅ RP готов")

# ================== SMIRNOV ==================

def download_smirnov_price():
    print("⬇️ Смирнов")
    r = requests.get(SMIRNOV_PRICE_URL, timeout=120)
    r.raise_for_status()
    local = os.path.join(BASE_DIR, "smirnov.xlsx")
    with open(local, "wb") as f:
        f.write(r.content)
    upload_to_yandex(local, f"/prices/smirnov/smirnov_{today()}.xlsx")
    print("✅ Смирнов готов")

# ================== TRADE DESIGN ==================

def download_td_price():
    print("⬇️ Торговый дизайн (API)")
    headers = {
        "Authorization": f"Bearer {TD_API_TOKEN}",
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    r = requests.get(
        TD_API_URL,
        headers=headers,
        stream=True,
        timeout=(30, 600),
    )
    r.raise_for_status()

    local = os.path.join(BASE_DIR, "trade_design.xlsx")
    with open(local, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    upload_to_yandex(local, f"/prices/trade_design/td_{today()}.xlsx")
    print("✅ Торговый дизайн готов")

# ================== BIO (API → XLSX, ПРАВИЛЬНО) ==================

def download_bio_price():
    print("⬇️ BIO (API → XLSX, основной прайс)")

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json"
    }

    # 1. Получаем категории (Оборудование)
    r = requests.post(
        "http://api.bioshop.ru:8030/categories",
        json={
            "login": BIO_LOGIN,
            "password": BIO_PASSWORD,
            "folderCode": "165729"  # оборудование
        },
        headers=headers,
        timeout=60
    )
    r.raise_for_status()
    categories = r.json()

    all_products = []

    # 2. Для каждой категории — получаем товары
    for cat in categories:
        category_id = cat.get("id")
        if not category_id:
            continue

        r = requests.post(
            "http://api.bioshop.ru:8030/products",
            json={
                "login": BIO_LOGIN,
                "password": BIO_PASSWORD,
                "categoryId": category_id
            },
            headers=headers,
            timeout=120
        )
        r.raise_for_status()
        products = r.json()

        if isinstance(products, list):
            all_products.extend(products)

    if not all_products:
        raise Exception("BIO API: товары не получены")

    # 3. XLSX
    wb = Workbook()
    ws = wb.active
    ws.title = "BIO price"

    columns = list(all_products[0].keys())
    ws.append(columns)

    for item in all_products:
        ws.append([item.get(col) for col in columns])

    local = os.path.join(BASE_DIR, "bio.xlsx")
    wb.save(local)

    upload_to_yandex(local, "/prices/bio/bio.xlsx")
    print("✅ BIO готов (основной прайс)")

# ================== MAIN ==================

def main():
    download_equip_price()
    download_rosholod_price()
    download_rp_price()
    download_smirnov_price()
    download_td_price()
    download_bio_price()

if __name__ == "__main__":
    main()
