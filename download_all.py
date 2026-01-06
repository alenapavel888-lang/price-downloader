import os
import time
import yadisk
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

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
    print("🔐 Переходим на страницу логина Equip")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context()
        page = context.new_page()

        # 1️⃣ ОТКРЫВАЕМ ЛОГИН-СТРАНИЦУ
        page.goto("https://equip.me/login", timeout=60000)
        page.wait_for_load_state("networkidle")

        page.screenshot(path="equip_login.png", full_page=True)

        # 2️⃣ ИЩЕМ ПОЛЕ ЛОГИНА (ТОЛЬКО ЯВНЫЕ ВАРИАНТЫ)
        if page.locator('input[type="email"]').is_visible():
            page.fill('input[type="email"]', EQUIP_LOGIN)
        elif page.locator('input[name="login"]').is_visible():
            page.fill('input[name="login"]', EQUIP_LOGIN)
        elif page.locator('input[name="username"]').is_visible():
            page.fill('input[name="username"]', EQUIP_LOGIN)
        else:
            raise Exception("❌ Не найдено поле логина на странице Equip")

        # 3️⃣ ПАРОЛЬ
        if page.locator('input[type="password"]').is_visible():
            page.fill('input[type="password"]', EQUIP_PASSWORD)
        else:
            raise Exception("❌ Не найдено поле пароля на странице Equip")

        # 4️⃣ КНОПКА ВХОДА
        page.locator("button[type=submit], button:has-text('Войти')").first.click()

        # 5️⃣ ЖДЁМ ПЕРЕХОДА В КАБИНЕТ
        try:
            page.wait_for_url("**/catalog**", timeout=15000)
            print("✅ Успешно вошли в личный кабинет Equip")
        except PlaywrightTimeout:
            page.screenshot(path="equip_login_failed.png", full_page=True)
            raise Exception("❌ Не удалось подтвердить вход в Equip")

        page.screenshot(path="equip_after_login.png", full_page=True)

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
