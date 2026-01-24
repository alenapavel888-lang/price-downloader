import os
import sys
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from statistics import mean
from urllib.parse import urlparse

# =========================
# КОНФИГУРАЦИЯ
# =========================

DATA_DIR = "data"
TOLERANCE = 0.20

SUPPLIERS = {
    "equip": "equip.xlsx",
    "bio": "bio.xlsx",
    "rp": "rp.xlsx",
    "rosholod": "rosholod.xlsx",
    "smirnov": "smirnov.xlsx",
    "trade_design": "td.xlsx",
}

ENTERO_BASE = "https://entero.ru"

COLUMNS = [
    "№","Источник","Артикул","Наименование","Нужно","На складе",
    "Цена дилерская","Валюта","Цена розничная","Валюта",
    "Цена Entero","Разница %","Наценка %","Валовая прибыль",
    "Сум
