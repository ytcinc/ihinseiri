from pathlib import Path
import json
import pandas as pd

path = Path(r"C:\Users\yamau\Downloads\きょういｔｐ.xlsx")
book = pd.ExcelFile(path)
out = []
for sheet in book.sheet_names:
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    rows = []
    for _, row in df.iterrows():
        vals = []
        for v in row.tolist():
            if pd.isna(v):
                vals.append("")
            else:
                vals.append(str(v))
        if any(x.strip() for x in vals):
            rows.append(vals)
    out.append({"sheet": sheet, "rows": rows[:200]})

print(json.dumps(out, ensure_ascii=False, indent=2))
