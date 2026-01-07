import os
import requests
import yadisk
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from playwright.sync_api import sync_playwright
from openpyxl import Workbook

# ================== SECRETS ==================

YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]

RP_LOGIN = os.environ["RP_LOGIN"]
RP_PASSWORD = os.environ["RP_PASSWORD"]

BIO_LOGIN = os.environ["BIO_LOGIN"]
BIO_PASSWORD = os.environ["BIO_PASSWORD"]

TD_API_TOKEN = os.environ["TD_API_TOKEN"]

SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ["SMTP_PORT"])
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]

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

BIO_API_BASE = "http://api.bioshop.ru:8030"

# ================== HELPERS ==================

def upload_to_yandex(local_path, remote_path):
    y = yadisk.YaDisk(token=YANDEX_TOKEN)
    remote_dir = os.path.dirname(remote_path)
    if not y.exists(remote_dir):
        y.mkdir(remote_dir)
    y.upload(local_path, remote_path, overwrite=True)


def send_error_email(subject, message):
    try:
        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = "pavel_yushin@bk.ru"

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print("⚠️ Ошибка отправки email:", e)


def safe_run(name, func):
    print(f"▶️ {name}")
    try:
        func()
        print(f"✅ {name} завершён")
    except Exception as e:
        error_text = f"{name} упал:\n\n{str(e)}"
        print(f"❌ {error_text}")
        send_error_email(
            subject=f"Ошибка выгрузки прайса: {name}",
            message=error_text
        )

# ================== EQUIP ==================

def download_equip_price():
    r = requests.get(EQUIP_PRICE_URL, timeout=120)
    r.raise_for_status()
    local = os.path.join(BASE_DIR, "equip.xlsx")
    open(local, "wb").write(r.content)
    upload_to_yandex(local, "/prices/equip/equip.xlsx")

# ================== ROSHOLOD ==================

def download_rosholod_price():
    local = os.path.join(BASE_DIR, "rosholod.xls")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(accept_downloads=True).new_page()
        page.goto("https://rosholod.org/downloads/price-lists/")
        with page.expect_download() as d:
            page.locator("text=Остатки (xls)").first.click()
        d.value.save_as(local)
        browser.close()
    upload_to_yandex(local, "/prices/rosholod/rosholod.xls")

# ================== RP ==================

def download_rp_price():
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
    upload_to_yandex(local, "/prices/rp/rp.xls")

# ================== SMIRNOV ==================

def download_smirnov_price():
    r = requests.get(SMIRNOV_PRICE_URL, timeout=120)
    r.raise_for_status()
    local = os.path.join(BASE_DIR, "smirnov.xlsx")
    open(local, "wb").write(r.content)
    upload_to_yandex(local, "/prices/smirnov/smirnov.xlsx")

# ================== TRADE DESIGN ==================

def download_td_price():
    headers = {
        "Authorization": f"Bearer {TD_API_TOKEN}",
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    r = requests.get(TD_API_URL, headers=headers, stream=True, timeout=(30, 600))
    r.raise_for_status()
    local = os.path.join(BASE_DIR, "td.xlsx")
    with open(local, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)
    upload_to_yandex(local, "/prices/trade_design/td.xlsx")

# ================== BIO (API) ==================

def bio_post(endpoint, payload):
    r = requests.post(
        f"{BIO_API_BASE}{endpoint}",
        json=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=(30, 300),
    )
    r.raise_for_status()
    return r.json()


def download_bio_price():
    payload = {"login": BIO_LOGIN, "password": BIO_PASSWORD, "folderCode": "165729"}
    categories = bio_post("/categories", payload)

    def walk(cats, out):
        for c in cats:
            sub = c.get("categories") or []
            if sub:
                walk(sub, out)
            else:
                out.append(c["id"])

    leaf_ids = []
    walk(categories, leaf_ids)

    products = []
    for cid in leaf_ids:
        res = bio_post("/products", {
            "login": BIO_LOGIN,
            "password": BIO_PASSWORD,
            "categoryId": cid
        })
        if isinstance(res, list):
            products.extend(res)

    if not products:
        raise Exception("BIO API вернул пустой список товаров")

    wb = Workbook()
    ws = wb.active
    ws.title = "BIO price"

    columns = list(products[0].keys())
    ws.append(columns)
    for p in products:
        ws.append([p.get(c) for c in columns])

    local = os.path.join(BASE_DIR, "bio.xlsx")
    wb.save(local)
    upload_to_yandex(local, "/prices/bio/bio.xlsx")

# ================== MAIN ==================

def main():
    safe_run("Equip", download_equip_price)
    safe_run("Росхолод", download_rosholod_price)
    safe_run("RP", download_rp_price)
    safe_run("Смирнов", download_smirnov_price)
    safe_run("Торговый дизайн", download_td_price)
    safe_run("BIO", download_bio_price)

if __name__ == "__main__":
    main()
