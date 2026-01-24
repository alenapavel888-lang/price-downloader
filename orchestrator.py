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
TOLERANCE = 0.20  # ±20%

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


def parse_manager_query(query: str):
    normalized = normalize_text(query)

    allow_analogs = "аналог" in normalized

    numbers = extract_numbers(normalized)

    equipment_type = normalized.split()[0] if normalized else ""

    print("\n🔎 Разбор запроса:")
    print(f"• Тип оборудования: {equipment_type}")
    print(f"• Числовые параметры: {numbers}")
    print(f"• Аналоги разрешены: {'ДА' if allow_analogs else 'НЕТ'}")

    return {
        "raw": query,
        "type": equipment_type,
        "numbers": numbers,
        "allow_analogs": allow_analogs,
    }


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
        row_text = " ".join(map(str, row.values))
        normalized = normalize_text(row_text)
        numbers = extract_numbers(normalized)

        items.append({
            "supplier": supplier,
            "row": row.to_dict(),
            "text": row_text,
            "normalized": normalized,
            "numbers": numbers,
        })

    print(f"✅ {supplier}: загружено {len(items)} позиций")
    return items


def load_all_prices():
    all_items = []

    for supplier, filename in SUPPLIERS.items():
        all_items.extend(load_price_file(supplier, filename))

    print(f"📦 Всего позиций загружено: {len(all_items)}")
    return all_items


# =========================
# УМНЫЙ ПОИСК (ШАГ 5)
# =========================

def within_tolerance(requested, actual):
    return requested * (1 - TOLERANCE) <= actual <= requested * (1 + TOLERANCE)


def smart_search(parsed_query, items):
    matches = []

    for item in items:
        ok = True

        # Тип оборудования
        if parsed_query["type"] and parsed_query["type"] not in item["normalized"]:
            ok = False

        # Числовые характеристики
        for key, req_val in parsed_query["numbers"].items():
            actual = item["numbers"].get(key)
            if actual is None or not within_tolerance(req_val, actual):
                ok = False
                break

        if ok:
            matches.append(item)

    print(f"\n🔍 Найдено совпадений: {len(matches)}")
    return matches


def choose_results(matches, allow_analogs):
    if not matches:
        return []

    # Чем больше совпавших характеристик — тем лучше
    matches.sort(key=lambda x: len(x["numbers"]), reverse=True)

    return matches[:3] if allow_analogs else matches[:1]


# =========================
# ТОЧКА ВХОДА
# =========================

def main():
    print("🚀 Старт orchestrator.py")
    print("=" * 60)

    check_environment()
    query = read_manager_query()

    parsed_query = parse_manager_query(query)

    print("\n📥 Загрузка прайсов поставщиков")
    all_items = load_all_prices()

    print("\n🧠 Выполняется умный поиск")
    matches = smart_search(parsed_query, all_items)
    results = choose_results(matches, parsed_query["allow_analogs"])

    if not results:
        print("❌ Не найдено ни одной позиции по заданным характеристикам")
        print("✅ Подбор оборудования готов")
        return

    print("\n🎯 РЕЗУЛЬТАТ ПОДБОРА:")
    for i, item in enumerate(results, 1):
        tag = "АНАЛОГ" if parsed_query["allow_analogs"] and i > 1 else "ОСНОВНОЙ"
        print(f"\n#{i} [{tag}] Поставщик: {item['supplier']}")
        print(item["text"][:300], "...")

    print("\n✅ ШАГ 5 УСПЕШНО ЗАВЕРШЁН")
    print("✅ Подбор оборудования готов")


if __name__ == "__main__":
    main()
