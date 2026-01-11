import os
import sqlite3
import pandas as pd

BASE_DIR = os.getcwd()
INDEX_DB = os.path.join(BASE_DIR, "index.db")
PRICES_DIR = os.path.join(BASE_DIR, "prices")

def check_environment():
    print("🔍 Проверка окружения\n")

    # Проверка index.db
    if not os.path.exists(INDEX_DB):
        raise Exception("❌ index.db не найден")
    print("✅ index.db найден")

    # Проверка, что база открывается
    conn = sqlite3.connect(INDEX_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM items")
    count = cur.fetchone()[0]
    conn.close()
    print(f"✅ index.db открыт, строк в items: {count}")

    # Проверка папки prices
    if not os.path.exists(PRICES_DIR):
        raise Exception("❌ папка prices не найдена")

    files = os.listdir(PRICES_DIR)
    if not files:
        raise Exception("❌ папка prices пуста")

    print("\n📦 Найдены прайсы:")
    for f in files:
        print(f" - {f}")

    # Пробуем открыть один прайс
    sample = files[0]
    path = os.path.join(PRICES_DIR, sample)

    if sample.lower().endswith(".xls"):
        df = pd.read_excel(path, engine="xlrd")
    else:
        df = pd.read_excel(path, engine="openpyxl")

    print(f"\n✅ Прайс {sample} успешно открыт, строк: {len(df)}")

def main():
    print("▶️ Старт оркестратора\n")
    check_environment()
    print("\n🎉 Инфраструктура готова. Можно двигаться дальше.")

if __name__ == "__main__":
    main()
