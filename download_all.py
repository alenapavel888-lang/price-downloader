from playwright.sync_api import sync_playwright
import pandas as pd
import yadisk
import os

# ====== НАСТРОЙКИ ======
YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]
EQUIP_LOGIN = os.environ["EQUIP_LOGIN"]
EQUIP_PASSWORD = os.environ["EQUIP_PASSWORD"]

EQUIP_PRICE_URL = "https://prices.equip.me/direct/v1/d269df604f27bffdb630eab3d46595d8/2543039075/1/msk/1/in_stock/ru/metric/price__.xlsx"

# ====== ЯНДЕКС ДИСК ======
y = yadisk.YaDisk(token=YANDEX_TOKEN)

def ensure_folders():
    folders = [
        "/PRICE_SYSTEM",
        "/PRICE_SYSTEM/raw",
        "/PRICE_SYSTEM/raw/equip",
        "/PRICE_SYSTEM/normalized"
    ]
    for f in folders:
        if not y.exists(f):
            y.mkdir(f)

def download_equip():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto("https://equip.me/login")
        page.fill("input[type=email]", EQUIP_LOGIN)
        page.fill("input[type=password]", EQUIP_PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_timeout(5000)

        with page.expect_download() as d:
            page.goto(EQUIP_PRICE_URL)

        d.value.save_as("equip.xlsx")
        browser.close()

def normalize_equip():
    df = pd.read_excel("equip.xlsx")
    return pd.DataFrame({
        "supplier": "equip",
        "name": df.get("Наименование"),
        "brand": df.get("Бренд"),
        "article": df.get("Артикул"),
        "price_dealer": df.get("Цена дилер"),
        "price_retail": df.get("Цена розничная"),
        "stock": df.get("Наличие")
    })

def main():
    ensure_folders()
    download_equip()
    y.upload("equip.xlsx", "/PRICE_SYSTEM/raw/equip/equip.xlsx", overwrite=True)

    products = normalize_equip()
    products.to_csv("products.csv", index=False)
    y.upload("products.csv", "/PRICE_SYSTEM/normalized/products.csv", overwrite=True)

    print("✅ Прайс Equip обновлён")

if __name__ == "__main__":
    main()


