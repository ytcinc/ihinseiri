from pathlib import Path

path = Path("mie/index.html")
html = path.read_text(encoding="utf-8")

old_title = '<h2 class="section-title">三重県の実家片付けで起きやすいこと</h2>'
title_pos = html.find(old_title)
if title_pos == -1:
    raise SystemExit("old Mie impact title not found")

section_start = html.rfind("<section", 0, title_pos)
section_end = html.find("</section>", title_pos)
if section_start == -1 or section_end == -1:
    raise SystemExit("old Mie impact section boundaries not found")

section_end += len("</section>")
html = html[:section_start] + html[section_end:]
path.write_text(html, encoding="utf-8")
print("removed old mie impact section")
