import os
import sys
import sqlite3
import re
import requests
from bs4 import BeautifulSoup

# =========================
# КОНФИГУРАЦИЯ
# =========================

DATA_DIR = "data"
INDEX_DB_PATH = "index.db"

REQUIRED_PRICE_FILES = [
    "equip.xlsx",
    "bio.xlsx",
    "rp.xlsx",
    "rosholod.xlsx",
    "smirnov.xlsx",
    "td.xlsx",  # trade_design (как у тебя на Яндекс Диске)
]

# =========================
# БАЗОВЫЕ УТИЛИТЫ
# =========================

def fail(message: str):
    print(f"❌ ОШИБКА: {message}")
    sys.exit(1)

# =========================
# ПРОВЕРКИ СРЕДЫ
# =========================

def check_data_directory():
    print("🔍 Проверка папки data/ ...")
    if not os.path.isdir(DATA_DIR):
        fail("Папка data/ не найдена")
    print("✅ Папка data/ найдена")


def check_price_files():
    print("🔍 Проверка прайсов поставщиков ...")
    missing = []
    for filename in REQUIRED_PRICE_FILES:
        path = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(path):
            missing.append(filename)

    if missing:
        fail(f"Отсутствуют прайсы: {', '.join(missing)}")

    print("✅ Все прайсы поставщиков найдены")


def check_index_db():
    print("🔍 Проверка index.db ...")
    if not os.path.isfile(INDEX_DB_PATH):
        fail("Файл index.db не найден")

    try:
        conn = sqlite3.connect(INDEX_DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        fail(f"index.db повреждён или не читается: {e}")

    print("✅ index.db доступен и читается")

# =========================
# INPUT LAYER — ЗАПРОС МЕНЕДЖЕРА
# =========================

def extract_links(text: str) -> list:
    return re.findall(r"https?://[^\s]+", text)


def fetch_data_from_link(url: str) -> dict:
    """
    Переход по ссылке поставщика.
    НИЧЕГО НЕ ДОДУМЫВАЕМ.
    """
    print(f"🔗 Переход по ссылке: {url}")

    try:
        resp = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"}
        )
    except Exception as e:
        return {
            "source_url": url,
            "error": f"Не удалось открыть ссылку: {e}"
        }

    if resp.status_code != 200:
        return {
            "source_url": url,
            "error": f"Страница недоступна (HTTP {resp.status_code})"
        }

    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.title.string.strip() if soup.title else ""
    page_text = soup.get_text(" ", strip=True).lower()

    characteristics = {}

    # ФАКТИЧЕСКОЕ извлечение чисел
    kg_match = re.search(r"(\d+(?:[.,]\d+)?)\s*кг", page_text)
    if kg_match:
        characteristics["performance_kg"] = float(kg_match.group(1).replace(",", "."))

    l_match = re.search(r"(\d+(?:[.,]\d+)?)\s*л", page_text)
    if l_match:
        characteristics["volume_l"] = float(l_match.group(1).replace(",", "."))

    levels_match = re.search(r"(\d+)\s*уров", page_text)
    if levels_match:
        characteristics["levels"] = int(levels_match.group(1))

    return {
        "source_url": url,
        "title": title,
        "characteristics": characteristics
    }


def read_user_query():
    print("📥 Получение запроса менеджера из переменной окружения MANAGER_QUERY ...")

    query = os.getenv("MANAGER_QUERY")

    if not query or not query.strip():
        fail(
            "Переменная окружения MANAGER_QUERY не задана.\n"
            "Передай запрос через GitHub Actions (env: MANAGER_QUERY)"
        )

    query = query.strip()
    print(f"✅ Запрос принят: «{query}»")

    links = extract_links(query)

    parsed_query = {
        "raw_text": query,
        "links": links,
        "from_links": [],
        "allow_analogs": "аналог" in query.lower(),
        "characteristics": {}
    }

    # 🔥 ПРИОРИТЕТ — ССЫЛКИ
    if links:
        print("🔎 Обнаружены ссылки, начинаем с них")
        for link in links:
            data = fetch_data_from_link(link)
            parsed_query["from_links"].append(data)
        return parsed_query

    # Если ссылок нет — разбираем текст
    text = query.lower()

    kg_match = re.search(r"(\d+(?:[.,]\d+)?)\s*кг", text)
    if kg_match:
        parsed_query["characteristics"]["performance_kg"] = float(
            kg_match.group(1).replace(",", ".")
        )

    l_match = re.search(r"(\d+(?:[.,]\d+)?)\s*л", text)
    if l_match:
        parsed_query["characteristics"]["volume_l"] = float(
            l_match.group(1).replace(",", ".")
        )

    levels_match = re.search(r"(\d+)\s*уров", text)
    if levels_match:
        parsed_query["characteristics"]["levels"] = int(levels_match.group(1))

    return parsed_query

# =========================
# ТОЧКА ВХОДА
# =========================

def main():
    print("🚀 Старт orchestrator.py")
    print("=" * 60)

    check_data_directory()
    check_price_files()
    check_index_db()

    parsed_query = read_user_query()

    print("\n🧠 Результат INPUT LAYER:")
    print(parsed_query)

    print("\nℹ️ Следующий шаг: поиск по прайсам и index.db")
    print("\n✅ ШАГ 1–3 УСПЕШНО ЗАВЕРШЕНЫ")


if __name__ == "__main__":
    main()
