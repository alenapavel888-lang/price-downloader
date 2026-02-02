def read_equip():
    items = []
    folder = "data/equip"

    for file in os.listdir(folder):
        if not file.endswith((".xlsx", ".xls")):
            continue

        path = os.path.join(folder, file)
        df = pd.read_excel(path).fillna("")

        for _, row in df.iterrows():
            items.append({
                "supplier": "equip",
                "article": str(row.get("Артикул", "")).strip(),
                "name": str(row.get("Наименование", "")).strip(),
                "dealer_price": to_float(row.get("Цена", "")),
                "retail_price": to_float(row.get("РРЦ", "")),
                "availability": row.get("Наличие", ""),
            })

    return items
