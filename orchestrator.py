import os
import sys
import sqlite3

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
    "td.xlsx",        # trade_design (как у тебя на Яндекс Диске)
]

# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================

def fail(message: str):
    print(f"❌ ОШИБКА: {message}")
    sys.exit(1)


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


def read_user_query():
    print("📥 Получение запроса менеджера из переменной окружения ...")

    query = os.getenv("MANAGER_QUERY")

    if not query or not query.strip():
        fail(
            "Переменная окружения MANAGER_QUERY не задана.\n"
            "Передай запрос через GitHub Actions (env: MANAGER_QUERY)"
        )

    query = query.strip()
    print(f"✅ Запрос принят: «{query}»")
    return query


# =========================
# ТОЧКА ВХОДА
# =========================

def main():
    print("🚀 Старт orchestrator.py")
    print("=" * 60)

    check_data_directory()
    check_price_files()
    check_index_db()

    query = read_user_query()

    print("\n🧠 Агент готов к дальнейшей обработке запроса")
    print("ℹ️ Поиск и расчёты будут добавлены на следующих шагах")

    print("\n✅ ШАГ 1 УСПЕШНО ЗАВЕРШЁН")


if __name__ == "__main__":
    main()
