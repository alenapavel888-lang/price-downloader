import os
import sys
import sqlite3

# -----------------------------
# НАСТРОЙКИ
# -----------------------------

INDEX_PATH = "index.db"

SUPPLIERS = [
    "equip",
    "bio",
    "rp",
    "rosholod",
    "trade_design",
    "smirnov",
]

DATA_DIR = "data"


# -----------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# -----------------------------

def log(msg):
    print(msg, flush=True)


def fail(msg):
    log(f"❌ {msg}")
    sys.exit(1)


# -----------------------------
# ПРОВЕРКИ ОКРУЖЕНИЯ
# -----------------------------

def check_index():
    log("🔍 Проверка index.db")
    if not os.path.isfile(INDEX_PATH):
        fail("index.db не найден. Сначала выполните build_index.py")
    log("✅ index.db найден")


def check_data_files():
    log("🔍 Проверка прайсов поставщиков")
    if not os.path.isdir(DATA_DIR):
        fail(f"Папка {DATA_DIR}/ не найдена")

    missing = []

    for supplier in SUPPLIERS:
        found = False
        for ext in (".xls", ".xlsx"):
            path = os.path.join(DATA_DIR, supplier + ext)
            if os.path.isfile(path):
                found = True
                break
        if not found:
            missing.append(supplier)

    if missing:
        fail(f"Отсутствуют прайсы поставщиков: {', '.join(missing)}")

    log("✅ Все прайсы поставщиков найдены")


def check_index_readable():
    log("🔍 Проверка чтения index.db")
    try:
        conn = sqlite3.connect(INDEX_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cur.fetchall()
        conn.close()
    except Exception as e:
        fail(f"Ошибка чтения index.db: {e}")

    if not tables:
        fail("index.db пуст — таблицы не найдены")

    log(f"✅ index.db содержит таблицы: {[t[0] for t in tables]}")


# -----------------------------
# ОСНОВНОЙ СЦЕНАРИЙ
# -----------------------------

def main():
    log("▶️ Старт orchestrator")

    check_index()
    check_data_files()
    check_index_readable()

    log("✅ Окружение готово. Можно выполнять поиск и расчёт.")
    log("✅ Orchestrator готов к работе")


if __name__ == "__main__":
    main()
