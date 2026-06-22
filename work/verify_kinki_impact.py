from pathlib import Path
import re

pages = ["mie", "shiga", "kyoto", "osaka", "hyogo", "nara", "wakayama"]
bad_patterns = ["縺", "繧", "蜩", "謨", "驕", "蛾", "髦", "譁", "鬆", "荳"]

for page in pages:
    html = Path(page, "index.html").read_text(encoding="utf-8", errors="replace")
    ids = re.findall(r'id="([^"]+)"', html)
    dup_ids = sorted({item for item in ids if ids.count(item) > 1})
    bad_hits = [pat for pat in bad_patterns if pat in html]
    print(page)
    print("  impact title:", html.count("実家片付けの大変さがわかるインパクト数字"))
    print("  impact id:", html.count(f'id="{page}-impact"'))
    print("  duplicate ids:", ", ".join(dup_ids) if dup_ids else "-")
    print("  mojibake hits:", ", ".join(bad_hits) if bad_hits else "-")
