from pathlib import Path
import json

import pandas as pd


path = Path(r"C:\Users\yamau\Downloads\しｇ.xlsx")
book = pd.ExcelFile(path)
out = []

for sheet in book.sheet_names:
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    rows = []
    for _, row in df.iterrows():
        vals = []
        for v in row.tolist():
            vals.append("" if pd.isna(v) else str(v))
        if any(x.strip() for x in vals):
            rows.append(vals)
    out.append({"sheet": sheet, "rows": rows[:260]})

print(json.dumps(out, ensure_ascii=False, indent=2))
