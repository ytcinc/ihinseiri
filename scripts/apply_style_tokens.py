#!/usr/bin/env python3
"""Apply the B-2 visual style tokens to regional pages.

This script intentionally edits only existing CSS values in HTML style blocks,
hero inline background values, and the shared osaka-city-page.css baseline.
It classifies pages from directory depth and current CSS links.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path


PREF_SLUGS = {
    "hokkaido",
    "aomori",
    "iwate",
    "miyagi",
    "akita",
    "yamagata",
    "fukushima",
    "ibaraki",
    "tochigi",
    "gunma",
    "saitama",
    "chiba",
    "tokyo",
    "kanagawa",
    "niigata",
    "toyama",
    "ishikawa",
    "fukui",
    "yamanashi",
    "nagano",
    "gifu",
    "shizuoka",
    "aichi",
    "mie",
    "shiga",
    "kyoto",
    "osaka",
    "hyogo",
    "nara",
    "wakayama",
    "tottori",
    "shimane",
    "okayama",
    "hiroshima",
    "yamaguchi",
    "tokushima",
    "kagawa",
    "ehime",
    "kochi",
    "fukuoka",
    "saga",
    "nagasaki",
    "kumamoto",
    "oita",
    "miyazaki",
    "kagoshima",
    "okinawa",
}

B2_PAGE_SKIP = {
    "tokyo/index.html",
    "hiroshima/index.html",
    "hokkaido/index.html",
    "kumamoto/yatsushiro/index.html",
    "hokkaido/ebetsu/index.html",
}

FONT = '"BIZ UDPGothic","Zen Kaku Gothic New","Hiragino Kaku Gothic ProN","Hiragino Sans",Meiryo,sans-serif'
BODY_COLOR = "#2B2B2B"
HEADING_COLOR = "#25211D"
PREF_H1 = "clamp(34px,4.6vw,58px)"
CITY_H1 = "clamp(34px,5vw,58px)"
PREF_GRAD = "linear-gradient(90deg,rgba(18,24,26,.82) 0%,rgba(18,24,26,.58) 46%,rgba(18,24,26,.18) 74%,rgba(18,24,26,0) 100%)"
CITY_GRAD = "linear-gradient(90deg,rgba(14,20,22,.9) 0%,rgba(14,20,22,.78) 42%,rgba(14,20,22,.42) 70%,rgba(14,20,22,.18) 100%)"

STYLE_RE = re.compile(r'(<style\b[^>]*>)(.*?)(</style>)', re.S | re.I)


@dataclass
class Page:
    path: Path
    rel: str
    is_prefecture: bool
    css_kind: str
    group: str


@dataclass
class Result:
    changed: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    notes: dict[str, list[str]] = field(default_factory=dict)

    def add_note(self, rel: str, note: str) -> None:
        self.notes.setdefault(rel, []).append(note)


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def classify(root: Path) -> list[Page]:
    pages: list[Page] = []
    for path in sorted(root.rglob("index.html")):
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/")
        if not parts or parts[0] not in PREF_SLUGS:
            continue
        text = read_text(path)
        if "site-mobile.css" in text:
            css_kind = "site-mobile"
        elif "osaka-city-page.css" in text:
            css_kind = "osaka-city"
        else:
            css_kind = "none"
        is_prefecture = len(parts) == 2
        if is_prefecture:
            group = {
                "site-mobile": "G2",
                "osaka-city": "G3",
                "none": "G4",
            }.get(css_kind, "SKIP")
        else:
            group = "CITY"
        pages.append(Page(path, rel, is_prefecture, css_kind, group))
    return pages


def css_set_decl(rule_body: str, prop: str, value: str) -> str:
    pattern = re.compile(rf"(?<![-\w]){re.escape(prop)}\s*:\s*[^;{{}}]+;?", re.I)
    replacement = f"{prop}:{value};"
    if pattern.search(rule_body):
        return pattern.sub(replacement, rule_body, count=1)
    stripped = rule_body.rstrip()
    sep = "" if not stripped or stripped.endswith(";") else ";"
    return f"{stripped}{sep}{replacement}"


def set_rule_decls(block: str, selector_pattern: str, decls: list[tuple[str, str]]) -> tuple[str, bool]:
    pattern = re.compile(rf"({selector_pattern}\s*\{{)(.*?)(\}})", re.S)
    changed = False

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        body = match.group(2)
        new_body = body
        for prop, value in decls:
            new_body = css_set_decl(new_body, prop, value)
        if new_body != body:
            changed = True
        return match.group(1) + new_body + match.group(3)

    return pattern.sub(repl, block, count=1), changed


def update_style_blocks(text: str, predicate, updater) -> tuple[str, list[str]]:
    notes: list[str] = []

    def repl(match: re.Match[str]) -> str:
        open_tag, body, close_tag = match.groups()
        style_id_match = re.search(r'id="([^"]+)"', open_tag, re.I)
        style_id = style_id_match.group(1) if style_id_match else ""
        if not predicate(style_id, open_tag, body):
            return match.group(0)
        new_body, style_notes = updater(style_id, body)
        if new_body != body:
            notes.extend(style_notes or [style_id or "inline-style"])
        return open_tag + new_body + close_tag

    return STYLE_RE.sub(repl, text), notes


def update_global_readable(text: str) -> tuple[str, list[str]]:
    def pred(style_id: str, _open: str, _body: str) -> bool:
        return style_id == "global-readable-palette-reset-v1"

    def upd(style_id: str, body: str) -> tuple[str, list[str]]:
        new_body, changed = set_rule_decls(
            body,
            r"html\s+body",
            [
                ("color", BODY_COLOR + "!important"),
                ("font-family", FONT + "!important"),
                ("font-size", "18px!important"),
                ("line-height", "1.78!important"),
            ],
        )
        return new_body, [style_id] if changed else []

    return update_style_blocks(text, pred, upd)


def update_pref_region_font(text: str) -> tuple[str, list[str]]:
    def pred(style_id: str, _open: str, _body: str) -> bool:
        return style_id == "pref-region-card-uniform-v1"

    def upd(style_id: str, body: str) -> tuple[str, list[str]]:
        new_body, changed = set_rule_decls(body, r"body", [("font-family", FONT + "!important")])
        return new_body, [style_id] if changed else []

    return update_style_blocks(text, pred, upd)


def replace_first_hero_gradient(block: str, gradient: str) -> str:
    return re.sub(
        r"linear-gradient\(90deg,.*?\)\s*,\s*(url\([^)]+\))",
        gradient + r",\1",
        block,
        count=1,
        flags=re.S,
    )


def update_prefecture_hero_match(text: str) -> tuple[str, list[str]]:
    def pred(style_id: str, _open: str, _body: str) -> bool:
        return style_id == "prefecture-top-hero-match"

    def upd(style_id: str, body: str) -> tuple[str, list[str]]:
        new = replace_first_hero_gradient(body, PREF_GRAD)
        new = re.sub(r"background-size:cover,auto\s+[^;!]+!important;", "background-size:cover!important;", new)
        new = re.sub(r"background-position:center,[^;!]+!important;", "background-position:center!important;", new)
        new = re.sub(r"font-size:clamp\([^;{}]+?\)!important;", f"font-size:{PREF_H1}!important;", new, count=1)
        new = re.sub(r"line-height:1\.(?:14|17|22|24|28)!important;", "line-height:1.18!important;", new, count=1)
        new = new.replace("font-size:19px!important;", "font-size:18px!important;")
        new = new.replace("line-height:1.9!important;", "line-height:1.85!important;")
        new = new.replace("font-size:31px!important;", "font-size:34px!important;")
        new = new.replace("line-height:1.34!important;", "line-height:1.28!important;")
        return new, [style_id] if new != body else []

    return update_style_blocks(text, pred, upd)


def update_local_top_hero(text: str) -> tuple[str, list[str]]:
    def pred(style_id: str, _open: str, _body: str) -> bool:
        return style_id == "local-top-hero-match"

    def upd(style_id: str, body: str) -> tuple[str, list[str]]:
        new = replace_first_hero_gradient(body, CITY_GRAD)
        new = re.sub(r"background-size:cover,auto\s+[^;!]+!important;", "background-size:cover!important;", new)
        new = re.sub(r"background-position:center,[^;!]+!important;", "background-position:center!important;", new)
        new = re.sub(r"min-height:\s*560px!important;", "min-height:520px!important;", new, count=1)
        new = re.sub(r"font-size:clamp\([^;{}]+?\)!important;", f"font-size:{CITY_H1}!important;", new, count=1)
        new = re.sub(r"line-height:1\.(?:14|17|22|24|28)!important;", "line-height:1.18!important;", new, count=1)
        new = new.replace("font-size:19px!important;", "font-size:18px!important;")
        new = new.replace("line-height:1.9!important;", "line-height:1.82!important;")
        return new, [style_id] if new != body else []

    return update_style_blocks(text, pred, upd)


def update_west_tokai_city(text: str) -> tuple[str, list[str]]:
    def pred(style_id: str, _open: str, _body: str) -> bool:
        return style_id == "west-tokai-city-kita-quality-hand-v1"

    def upd(style_id: str, body: str) -> tuple[str, list[str]]:
        new, _ = set_rule_decls(
            body,
            r"body\.west-tokai-city-quality",
            [
                ("font-family", FONT + "!important"),
                ("color", BODY_COLOR + "!important"),
                ("font-size", "18px!important"),
                ("line-height", "1.78!important"),
            ],
        )
        new = re.sub(
            r"body\.west-tokai-city-quality p,body\.west-tokai-city-quality li\{([^{}]*)\}",
            lambda m: "body.west-tokai-city-quality p,body.west-tokai-city-quality li{"
            + css_set_decl(css_set_decl(m.group(1), "font-size", "18px!important"), "line-height", "1.78!important")
            + "}",
            new,
            count=1,
        )
        new = re.sub(
            r"body\.west-tokai-city-quality \.hero\{background:.*?url\(([^)]+)\)\s*[^!;]*!important;color:#fff!important;padding:[^;]+!important\}",
            rf"body.west-tokai-city-quality .hero{{background:{CITY_GRAD},url(\1) center center/cover no-repeat!important;color:#fff!important;padding:64px 0 72px!important}}",
            new,
            count=1,
        )
        new = re.sub(
            r"(body\.west-tokai-city-quality \.hero-inner\{[^{}]*?)gap:\s*[^;]+;",
            r"\1gap:34px;",
            new,
            count=1,
        )
        if "body.west-tokai-city-quality .hero-inner" in new and "min-height:520px!important" not in new:
            new = re.sub(
                r"(body\.west-tokai-city-quality \.hero-inner\{[^{}]*?width:[^;]+;)",
                r"\1min-height:520px!important;",
                new,
                count=1,
            )
        new = re.sub(r"body\.west-tokai-city-quality \.hero h1\{[^{}]*\}", _west_h1_repl, new, count=1)
        new = re.sub(
            r"body\.west-tokai-city-quality \.hero \.hero-lead,body\.west-tokai-city-quality \.hero p\{[^{}]*\}",
            _west_lead_repl,
            new,
            count=1,
        )
        return new, [style_id] if new != body else []

    return update_style_blocks(text, pred, upd)


def _west_h1_repl(match: re.Match[str]) -> str:
    body = match.group(0)
    inner = body[body.find("{") + 1 : -1]
    inner = css_set_decl(inner, "font-size", CITY_H1 + "!important")
    inner = css_set_decl(inner, "line-height", "1.18!important")
    inner = css_set_decl(inner, "color", "#fff!important")
    return "body.west-tokai-city-quality .hero h1{" + inner + "}"


def _west_lead_repl(match: re.Match[str]) -> str:
    body = match.group(0)
    inner = body[body.find("{") + 1 : -1]
    inner = css_set_decl(inner, "font-size", "18px!important")
    inner = css_set_decl(inner, "line-height", "1.82!important")
    inner = css_set_decl(inner, "color", "rgba(255,255,255,.95)!important")
    return "body.west-tokai-city-quality .hero .hero-lead,body.west-tokai-city-quality .hero p{" + inner + "}"


def update_hero_readable(text: str, is_prefecture: bool) -> tuple[str, list[str]]:
    h1_size = PREF_H1 if is_prefecture else CITY_H1
    lead_line = "1.85!important" if is_prefecture else "1.82!important"
    min_height = "560px!important" if is_prefecture else "520px!important"
    gradient = PREF_GRAD if is_prefecture else CITY_GRAD

    def pred(style_id: str, _open: str, _body: str) -> bool:
        return "hero-readable" in style_id or "hero-readability" in style_id

    def upd(style_id: str, body: str) -> tuple[str, list[str]]:
        new = body.replace("color: #FFF8EF !important;", "color: #fff !important;")
        new = new.replace("color: #FFF1DF !important;", "color: #fff !important;")
        new, _ = set_rule_decls(
            new,
            r"html\s+body\s+\.hero\s+h1",
            [
                ("color", "#fff!important"),
                ("font-size", h1_size + "!important"),
                ("line-height", "1.18!important"),
            ],
        )
        new, _ = set_rule_decls(
            new,
            r"html\s+body\s+\.hero\s+\.hero-lead(?:,\s*html\s+body\s+\.hero\s+p\.hero-lead)?",
            [
                ("color", "#fff!important"),
                ("font-size", "18px!important"),
                ("line-height", lead_line),
            ],
        )
        if "html body .hero {" in new:
            new, _ = set_rule_decls(
                new,
                r"html\s+body\s+\.hero",
                [
                    ("background-image", gradient + ',url("/assets/cv-hero-staff-photo.png?v=1")!important'),
                    ("background-position", "center center!important"),
                    ("background-size", "cover!important"),
                ],
            )
        if "html body .hero .hero-inner" in new:
            new, _ = set_rule_decls(new, r"html\s+body\s+\.hero\s+\.hero-inner", [("min-height", min_height)])
        return new, [style_id] if new != body else []

    return update_style_blocks(text, pred, upd)


def update_inline_hero_background(text: str, is_prefecture: bool) -> tuple[str, list[str]]:
    gradient = PREF_GRAD if is_prefecture else CITY_GRAD
    changed = False

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        changed = True
        return match.group(1) + gradient + "," + match.group(2)

    new = re.sub(
        r'(<section\b[^>]*class="hero"[^>]*style="background-image:)linear-gradient\(90deg,.*?\),(url\([^)]+\)")',
        repl,
        text,
        count=1,
        flags=re.S,
    )
    return new, ["hero inline background"] if changed else []


def update_embedded_hero_backgrounds(text: str, is_prefecture: bool) -> tuple[str, list[str]]:
    gradient = PREF_GRAD if is_prefecture else CITY_GRAD
    changed = False

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        changed = True
        return gradient + "," + match.group(1)

    new = re.sub(
        r"linear-gradient\(90deg,rgba\([^;{}]+?\)\s*,\s*(url\([\"']?/assets/cv-hero-staff-photo\.png[^)]*\))",
        repl,
        text,
        flags=re.S,
    )
    return new, ["hero background gradient"] if changed else []


def update_independent_pref(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    new = text
    new2, n = update_global_readable(new)
    if n:
        notes.extend(n)
    new = new2
    before = new
    new = re.sub(
        r"font-family:\s*(?:-apple-system,[^;]+|\"[^\"]+\"(?:,\s*[^;]+)+);",
        "font-family: " + FONT + ";",
        new,
        count=1,
    )
    new = re.sub(
        r"body\s*\{([^{}]*)\}",
        lambda m: "body {" + css_set_decl(
            css_set_decl(css_set_decl(css_set_decl(m.group(1), "color", BODY_COLOR), "font-size", "18px"), "line-height", "1.78"),
            "font-family",
            FONT,
        ) + "}",
        new,
        count=1,
    )
    new, n = update_embedded_hero_backgrounds(new, True)
    notes.extend(n)
    new = re.sub(r"font-size:clamp\([^;{}]+?\);\s*line-height:1\.(?:14|17|22|24|28);", f"font-size:{PREF_H1}; line-height:1.18;", new, count=1)
    new = re.sub(r"color:#fff1df;", "color:#fff;", new, count=1)
    new = re.sub(r"line-height:2;", "line-height:1.85;", new, count=1)
    new = re.sub(r"font-size:clamp\(26px,3vw,38px\);\s*line-height:1\.35;", "font-size:clamp(24px,3vw,34px); line-height:1.38;", new, count=1)
    new = new.replace("h1{font-size:31px;line-height:1.34}", "h1{font-size:34px;line-height:1.28}")
    if new != before:
        notes.append("independent-pref-style")
    return new, notes


def update_osaka_city_css(root: Path) -> tuple[bool, list[str]]:
    path = root / "assets" / "osaka-city-page.css"
    text = read_text(path)
    new = text
    new = new.replace(
        'font-family: "Zen Kaku Gothic New", "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif;',
        f"font-family: {FONT};",
    )
    new = re.sub(r"body\s*\{(.*?)\}", lambda m: "body {" + css_set_decl(css_set_decl(css_set_decl(m.group(1), "color", BODY_COLOR), "font-size", "18px"), "line-height", "1.78") + "}", new, count=1, flags=re.S)
    new = new.replace(
        'background:linear-gradient(90deg,rgba(18,24,26,.78) 0%,rgba(18,24,26,.50) 34%,rgba(18,24,26,.16) 58%,rgba(18,24,26,0) 100%),var(--hero-image, url("/assets/cv-hero-staff-photo.png?v=1"));',
        'background:' + CITY_GRAD + ',var(--hero-image, url("/assets/cv-hero-staff-photo.png?v=1"));',
    )
    new = re.sub(r"font-size:\s*clamp\(32px,\s*5vw,\s*52px\);", f"font-size: {CITY_H1};", new, count=1)
    new = re.sub(r"line-height:\s*1\.24;", "line-height: 1.18;", new, count=1)
    new = re.sub(r"(\.hero-lead\s*\{[^{}]*?)font-size:\s*19px;", r"\1font-size: 18px;", new, count=1, flags=re.S)
    if ".hero-lead" in new:
        new = re.sub(r"(\.hero-lead\s*\{[^{}]*?font-size:\s*18px;)", r"\1\n      line-height: 1.82;", new, count=1, flags=re.S)
    if new != text:
        write_text(path, new)
        return True, ["assets/osaka-city-page.css"]
    return False, []


def apply_to_page(page: Page, include_b2: bool = False) -> tuple[bool, list[str], str | None]:
    if page.rel in B2_PAGE_SKIP and not include_b2:
        return False, [], "B-2 applied page skipped"

    text = read_text(page.path)
    original = text
    notes: list[str] = []

    if page.group in {"G2", "G3"}:
        for func in (update_global_readable, update_pref_region_font, update_prefecture_hero_match):
            text, n = func(text)
            notes.extend(n)
        text, n = update_inline_hero_background(text, True)
        notes.extend(n)
        text, n = update_hero_readable(text, True)
        notes.extend(n)
    elif page.group == "G4":
        text, n = update_independent_pref(text)
        notes.extend(n)
    elif page.group == "CITY":
        for func in (update_global_readable, update_pref_region_font, update_local_top_hero, update_west_tokai_city):
            text, n = func(text)
            notes.extend(n)
        text, n = update_inline_hero_background(text, False)
        notes.extend(n)
        text, n = update_hero_readable(text, False)
        notes.extend(n)
        text, n = update_embedded_hero_backgrounds(text, False)
        notes.extend(n)
    else:
        return False, [], "unknown group"

    if text != original:
        write_text(page.path, text)
        return True, sorted(set(notes)), None
    if page.group == "CITY" and not any(
        token in original
        for token in (
            "global-readable-palette-reset-v1",
            "local-top-hero-match",
            "west-tokai-city-kita-quality-hand-v1",
            "hero-readable",
            "hero-readability",
        )
    ):
        return False, [], "no existing style hook for city tokens"
    if page.group in {"G2", "G3"} and "prefecture-top-hero-match" not in original and "global-readable-palette-reset-v1" not in original:
        return False, [], "no existing style hook for prefecture tokens"
    if page.group == "G4" and page.rel in B2_PAGE_SKIP:
        return False, [], "B-2 applied page skipped"
    return False, [], None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=["G2", "G3", "G4", "CITY", "ALL", "REPORT"], default="REPORT")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--include-b2", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    pages = classify(root)
    result = Result()

    selected = [p for p in pages if args.group in {"ALL", "REPORT"} or p.group == args.group]
    if args.group == "REPORT":
        counts: dict[str, int] = {}
        css_counts: dict[str, int] = {}
        for page in pages:
            counts[page.group] = counts.get(page.group, 0) + 1
            css_counts[page.css_kind] = css_counts.get(page.css_kind, 0) + 1
        print("group_counts", counts)
        print("css_counts", css_counts)
        print("b2_skip", sorted(B2_PAGE_SKIP))
        return 0

    if not args.apply:
        print("dry_run", args.group, "pages", len(selected))
        for page in selected[:20]:
            print(page.group, page.css_kind, page.rel)
        if len(selected) > 20:
            print("...", len(selected) - 20, "more")
        return 0

    if args.group == "G3":
        changed, notes = update_osaka_city_css(root)
        if changed:
            result.changed.extend(notes)
            result.notes[notes[0]] = ["common osaka-city baseline"]

    for page in selected:
        changed, notes, skip_reason = apply_to_page(page, include_b2=args.include_b2)
        if changed:
            result.changed.append(page.rel)
            result.notes[page.rel] = notes
        elif skip_reason:
            result.skipped.append((page.rel, skip_reason))

    print("group", args.group)
    print("changed_count", len(result.changed))
    for rel in result.changed:
        print("changed", rel, ";".join(result.notes.get(rel, [])))
    print("skipped_count", len(result.skipped))
    for rel, reason in result.skipped:
        print("skipped", rel, reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
