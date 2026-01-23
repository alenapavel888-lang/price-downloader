import os
import sys
import sqlite3
import pandas as pd
import re

# =========================
# КОНФИГУРАЦИЯ
# =========================

DATA_DIR = "data"
INDEX_DB_PATH = "index.db"

SUPPLIERS = {
    "equip": "equip.xlsx",
    "bio": "bio.xlsx",
    "rp": "rp.xlsx",
    "rosholod": "rosholod.xlsx",
    "smirnov": "smirnov.xlsx",
    "trade_design": "td.xlsx",
}

# =========================
# БАЗОВЫЕ ПРОВЕРКИ
# =========================

def fail(message: str):
    print(f"❌ ОШИБКА: {message}")
    sys.exit(1)


def check_environment():
    print("🔍 Проверка окружения")

    if not os.path.isdir(DATA_DIR):
        fail("Папка data/ не найдена")

    for supplier, filename in SUPPLIERS.items():
        path = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(path):
            fail(f"Прайс {supplier} не найден: {filename}")

    if not os.path.isfile(INDEX_DB_PATH):
        fail("index.db не найден")

    print("✅ Окружение готово")


def read_manager_query():
    query = os.getenv("MANAGER_QUERY")
    if not query or not query.strip():
        fail("MANAGER_QUERY не задан")
    query = query.strip()
    print(f"📥 Запрос менеджера: «{query}»")
    return query


# =========================
# НОРМАЛИЗАЦИЯ И ПАРСИНГ
# =========================

def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s×x]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_numbers(text: str):
    """
    Извлекаем ТОЛЬКО фактические числовые характеристики
    """
    if not text:
        return {}

    result = {}

    patterns = {
        "kg": r"(\d+(?:[.,]\d+)?)\s*кг",
        "liters": r"(\d+(?:[.,]\d+)?)\s*л",
        "levels": r"(\d+)\s*уров",
        "kw": r"(\d+(?:[.,]\d+)?)\s*квт",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = match.group(1).replace(",", ".")
            result[key] = float(value)

    return result


# =========================
# ЗАГРУЗКА ПРАЙСОВ
# =========================

def load_price_file(supplier: str, filename: str):
    path = os.path.join(DATA_DIR, filename)
    print(f"📄 Загрузка прайса {supplier}: {filename}")

    try:
        df = pd.read_excel(path, dtype=str)
    except Exception as e:
        fail(f"Ошибка чтения {filename}: {e}")

    df = df.fillna("")

    items = []

    for _, row in df.iterrows():
        name = row.to_string()

        normalized_name = normalize_text(name)
        numbers = extract_numbers(normalized_name)

        item = {
            "supplier": supplier,
            "raw_row": row.to_dict(),
            "name": row.to_string(),
            "normalized_name": normalized_name,
            "numbers": numbers,
        }

        items.append(item)

    print(f"✅ {supplier}: загружено {len(items)} позиций")
    return items


def load_all_prices():
    all_items = []

    for supplier, filename in SUPPLIERS.items():
        items = load_price_file(supplier, filename)
        all_items.extend(items)

    print(f"📦 Всего позиций загружено: {len(all_items)}")
    return all_items


# =========================
# ТОЧКА ВХОДА
# =========================

def main():
    print("🚀 Старт orchestrator.py")
    print("=" * 60)

    check_environment()
    query = read_manager_query()

    print("\n📥 Загрузка прайсов поставщиков")
    all_items = load_all_prices()

    print("\n🧠 Поисковый слой подготовлен")
    print("ℹ️ Следующий шаг — умный поиск по характеристикам")

    print("\n✅ ШАГ 4 УСПЕШНО ЗАВЕРШЁН")


if __name__ == "__main__":
    main()
