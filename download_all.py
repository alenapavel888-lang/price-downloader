import os
import time
import yadisk
from playwright.sync_api import sync_playwright

YANDEX_TOKEN = os.environ.get("YANDEX_TOKEN")
EQUIP_LOGIN = os.environ.get("EQUIP_LOGIN")
EQUIP_PASSWORD = os.environ.get("EQUIP_PASSWORD")

YANDEX_ROOT = "/PRICE_SYSTEM"


def ensure_folders(y):
    folders = [
        YANDEX_ROOT,
        f"{YANDEX_ROOT}/raw",
        f"{YANDEX_ROOT}/raw/equip",
    ]

    for f in folders:
        if not y.exists(f):
            print(f"📁 Создаём папку {f}")
            y.mkdir(f)


def download_equip():
    print("🔐 Открываем сайт Equip")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://equip.me/login", timeout=60000)
        page.wait_for_load_state("networkidle")

        # 📸 диагностический скрин
        page.screenshot(path="equip_login.png", full_page=True)

        print("✍️ Ищем поле логина")

        if page.locator('input[type="email"]').count() > 0:
            page.fill('input[type="email"]', EQUIP_LOGIN)
        elif page.locator('input[name="login"]').count() > 0:
            page.fill('input[name="login"]', EQUIP_LOGIN)
        elif page.locator('input[name="username"]').count() > 0:
            page.fill('input[name="username"]', EQUIP_LOGIN)
        elif page.locator('input').count() > 0:
            page.locator('input').first.fill(EQUIP_LOGIN)
        else:
            raise Exception("❌ Поле логина не найдено")

        time.sleep(1)

        print("🔑 Ищем поле пароля")

        if page.locator('input[type="password"]').count() > 0:
            page.fill('input[type="password"]', EQUIP_PASSWORD)
        else:
            raise Exception("❌ Поле пароля не найдено")

        time.sleep(1)

        print("➡️ Нажимаем кнопку входа")

        page.locator("button").first.click()
        page.wait_for_timeout(8000)

        # 📸 скрин после логина
        page.screenshot(path="equip_after_login.png", full_page=True)

        print("✅ Попытка авторизации выполнена")

        browser.close()


def main():
    if not YANDEX_TOKEN:
        raise Exception("YANDEX_TOKEN не задан")

    y = yadisk.YaDisk(token=YANDEX_TOKEN)

    if not y.check_token():
        raise Exception("YANDEX_TOKEN невалиден")

    ensure_folders(y)

    download_equip()


if __name__ == "__main__":
    main()
