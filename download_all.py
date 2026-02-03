# download_all.py (ИСПРАВЛЕННЫЙ)

import os
import requests
import yadisk
import smtplib
import traceback
import zipfile
import shutil
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright
from openpyxl import Workbook

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]

RP_LOGIN = os.environ["RP_LOGIN"]
RP_PASSWORD = os.environ["RP_PASSWORD"]

BIO_LOGIN = os.environ["BIO_LOGIN"]
BIO_PASSWORD = os.environ["BIO_PASSWORD"]

TD_API_TOKEN = os.environ["TD_API_TOKEN"]

EQUIP_PRICE_URL = "https://prices.equip.me/direct/v1/d269df604f27bffdb630eab3d46595d8/2543039075/1/msk/1/in_stock/ru/metric/price__.xlsx"
SMIRNOV_PRICE_URL = "https://files.smirnov.ooo/Prays-list%20po%20ostatkam%20XLSX.xlsx"
TD_API_URL = "https://api.t-d.ru/api/ka-nomenclature/download-excel/with-filters/ka_nomenclature_td?extension=xlsx"
BIO_API_BASE = "http://api.bioshop.ru:8030"

y = yadisk.YaDisk(token=YANDEX_TOKEN)

def upload(local, remote):
    if not y.exists(os.path.dirname(remote)):
        y.mkdir(os.path.dirname(remote))
    y.upload(local, remote, overwrite=True)

def download_equip():
    path = f"{DATA_DIR}/equip.xlsx"
    r = requests.get(EQUIP_PRICE_URL, timeout=120)
    r.raise_for_status()
    open(path, "wb").write(r.content)
    upload(path, "/prices/equip/equip.xlsx")

def download_smirnov():
    path = f"{DATA_DIR}/smirnov.xlsx"
    r = requests.get(SMIRNOV_PRICE_URL, timeout=120)
    r.raise_for_status()
    open(path, "wb").write(r.content)
    upload(path, "/prices/smirnov/smirnov.xlsx")

def download_rosholod():
    path = f"{DATA_DIR}/rosholod.xls"
    with sync_playwright() as p:
        page = p.chromium.launch(headless=True).new_page()
        page.goto("https://rosholod.org/downloads/price-lists/")
        with page.expect_download() as d:
            page.click("text=Остатки (xls)")
        d.value.save_as(path)
    upload(path, "/prices/rosholod/rosholod.xls")

def download_rp():
    zip_path = f"{DATA_DIR}/rp.zip"
    extract_dir = f"{DATA_DIR}/rp_tmp"
    final = f"{DATA_DIR}/rp.xls"

    with sync_playwright() as p:
        page = p.chromium.launch(headless=True).new_page()
        page.goto("https://dc.rp.ru/")
        page.fill("input[type=text]", RP_LOGIN)
        page.fill("input[type=password]", RP_PASSWORD)
        page.keyboard.press("Enter")
        page.hover("text=Прайс")
        with page.expect_download() as d:
            page.click("text=Прайс лист в формате xls")
        d.value.save_as(zip_path)

    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_dir)

    for f in os.listdir(extract_dir):
        if f.endswith(".xls"):
            shutil.move(os.path.join(extract_dir, f), final)

    upload(final, "/prices/rp/rp.xls")

def download_td():
    path = f"{DATA_DIR}/td.xlsx"
    r = requests.get(
        TD_API_URL,
        headers={"Authorization": f"Bearer {TD_API_TOKEN}"},
        stream=True,
        timeout=(30, 600)
    )
    r.raise_for_status()
    with open(path, "wb") as f:
        for c in r.iter_content(1024 * 1024):
            f.write(c)
    upload(path, "/prices/trade_design/td.xlsx")

def download_bio():
    payload = {"login": BIO_LOGIN, "password": BIO_PASSWORD, "folderCode": "165729"}
    cats = requests.post(f"{BIO_API_BASE}/categories", json=payload).json()
    ids = []

    def walk(c):
        for x in c:
            if x.get("categories"):
                walk(x["categories"])
            else:
                ids.append(x["id"])
    walk(cats)

    products = []
    for cid in ids:
        r = requests.post(f"{BIO_API_BASE}/products", json={**payload, "categoryId": cid})
        if isinstance(r.json(), list):
            products += r.json()

    wb = Workbook()
    ws = wb.active
    ws.append(products[0].keys())
    for p in products:
        ws.append(p.values())

    path = f"{DATA_DIR}/bio.xlsx"
    wb.save(path)
    upload(path, "/prices/bio/bio.xlsx")

def main():
    download_equip()
    download_rosholod()
    download_rp()
    download_smirnov()
    download_td()
    download_bio()

if __name__ == "__main__":
    main()
