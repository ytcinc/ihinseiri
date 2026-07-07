from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
KITA_PATH = ROOT / "osaka" / "kita" / "index.html"
SPEC_PATH = ROOT / "work" / "kita-template-spec.md"
REPORT_PATH = ROOT / "work" / "kita-diff-report.md"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def attrs_to_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {k.lower(): (v or "") for k, v in attrs}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta_description = ""
        self.links: list[str] = []
        self.styles: list[str] = []
        self.sections: list[dict] = []
        self.tables: list[list[str]] = []
        self.classes: Counter[str] = Counter()
        self.ids: list[str] = []
        self.upper_labels: Counter[str] = Counter()
        self.text_chunks: list[str] = []
        self._tag_stack: list[tuple[str, dict[str, str]]] = []
        self._capture_tag: str | None = None
        self._capture_attrs: dict[str, str] = {}
        self._capture_text: list[str] = []
        self._style_text: list[str] = []
        self._in_style = False
        self._current_section: dict | None = None
        self._current_table_headers: list[str] | None = None
        self._current_th_text: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = attrs_to_dict(attrs)
        self._tag_stack.append((tag, attr))

        class_value = attr.get("class", "")
        for cls in class_value.split():
            self.classes[cls] += 1
        if "id" in attr:
            self.ids.append(attr["id"])

        if tag == "meta" and attr.get("name", "").lower() == "description":
            self.meta_description = attr.get("content", "")
        if tag == "link" and attr.get("rel", "").lower() == "stylesheet":
            self.links.append(attr.get("href", ""))
        if tag == "style":
            self._in_style = True
            self._style_text = []
        if tag == "section":
            section = {
                "id": attr.get("id", ""),
                "class": class_value,
                "h2": "",
                "h3": [],
                "cards": 0,
                "faqs": 0,
                "tables": 0,
            }
            self.sections.append(section)
            self._current_section = section
        if tag == "table":
            self._current_table_headers = []
            if self._current_section is not None:
                self._current_section["tables"] += 1
        if tag == "th":
            self._current_th_text = []

        if tag in {"title", "h1", "h2", "h3", "h4", "a", "span", "strong", "th"}:
            self._capture_tag = tag
            self._capture_attrs = attr
            self._capture_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.styles.append("".join(self._style_text))
            self._in_style = False
            self._style_text = []
        if tag == "section":
            self._current_section = None
        if tag == "table":
            self.tables.append(self._current_table_headers or [])
            self._current_table_headers = None
        if tag == "th" and self._current_th_text is not None:
            text = clean_text("".join(self._current_th_text))
            if text and self._current_table_headers is not None:
                self._current_table_headers.append(text)
            self._current_th_text = None

        if self._capture_tag == tag:
            text = clean_text("".join(self._capture_text))
            if text:
                self.text_chunks.append(text)
                if tag == "title":
                    self.title = text
                elif tag == "h2" and self._current_section is not None and not self._current_section["h2"]:
                    self._current_section["h2"] = text
                elif tag == "h3" and self._current_section is not None:
                    self._current_section["h3"].append(text)
                if re.fullmatch(r"[A-Z][A-Z0-9 &/.-]{1,24}", text):
                    self.upper_labels[text] += 1
            self._capture_tag = None
            self._capture_attrs = {}
            self._capture_text = []

        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._style_text.append(data)
        if self._capture_tag:
            self._capture_text.append(data)
        if self._current_th_text is not None:
            self._current_th_text.append(data)


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    parser.close()
    return parser


def selector_list(style_text: str) -> list[str]:
    selectors: list[str] = []
    for match in re.finditer(r"([^{}]+)\{", style_text):
        raw = match.group(1).strip()
        if not raw or raw.startswith("@"):
            continue
        for selector in raw.split(","):
            selector = clean_text(selector)
            if selector:
                selectors.append(selector)
    return selectors


def css_decl(style_text: str, selector: str, prop: str) -> str:
    pattern = re.compile(r"(?s)(^|})\s*" + re.escape(selector) + r"\s*\{([^{}]*)\}")
    matches = pattern.findall(style_text)
    if not matches:
        return ""
    body = matches[-1][1]
    prop_pattern = re.compile(re.escape(prop) + r"\s*:\s*([^;]+)")
    prop_matches = prop_pattern.findall(body)
    return clean_text(prop_matches[-1]) if prop_matches else ""


def section_signature(parser: PageParser) -> list[tuple[str, str, tuple[str, ...]]]:
    return [(s["id"], s["h2"], tuple(s["h3"])) for s in parser.sections]


def count_cards(parser: PageParser) -> int:
    return sum(count for cls, count in parser.classes.items() if "card" in cls.lower() or "box" in cls.lower())


def count_faq(parser: PageParser) -> int:
    text = "\n".join(parser.text_chunks)
    return len(re.findall(r"\bQ[.．]", text)) + sum(count for cls, count in parser.classes.items() if "faq" in cls.lower())


def stat_cards(parser: PageParser) -> list[str]:
    chunks = parser.text_chunks
    out: list[str] = []
    for i, text in enumerate(chunks):
        if re.search(r"(65歳以上|高齢化率|空き家率|自己搬入先|処理施設)", text):
            prev = chunks[i - 1] if i > 0 else ""
            out.append(f"{prev} / {text}" if prev and re.search(r"[\d,]+|%|工場|センター", prev) else text)
    return out[:8]


def table_shapes(parser: PageParser) -> list[str]:
    return [" / ".join(headers) if headers else "(thなし)" for headers in parser.tables]


def title_format(title: str) -> str:
    if " | " in title:
        return "A | B"
    if "｜" in title:
        return "A｜B"
    return "separatorなし"


def meta_format(description: str) -> str:
    if "、" in description:
        return "読点区切り"
    if "," in description:
        return "comma区切り"
    return "短文"


def class_origin_patterns(classes: Iterable[str]) -> list[str]:
    out = []
    for cls in classes:
        if re.search(r"^(minato|kita|fukushima|konohana|nishi|chuo|miyakojima|tennoji|osaka)-", cls):
            out.append(cls)
        elif re.search(r"-(minato|kita|fukushima|konohana|nishi|chuo|miyakojima|tennoji)$", cls):
            out.append(cls)
    return sorted(set(out))


def html_paths() -> list[Path]:
    skip_parts = {".git", "node_modules", ".next", "dist", "build"}
    paths = []
    for path in ROOT.rglob("*.html"):
        if any(part in skip_parts for part in path.parts):
            continue
        paths.append(path)
    return sorted(paths)


@dataclass
class DiffBucket:
    items: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add(self, key: str, path: Path, detail: str = "") -> None:
        rel = path.relative_to(ROOT).as_posix()
        self.items[key].append(f"{rel} — {detail}" if detail else rel)


def write_spec(kita: PageParser) -> None:
    all_styles = "\n".join(kita.styles)
    selectors_by_block = [selector_list(style) for style in kita.styles]
    lines: list[str] = []
    lines.append("# 北区テンプレート仕様")
    lines.append("")
    lines.append("## 事前状態")
    lines.append("- 基準ファイル: `osaka/kita/index.html`")
    lines.append("- 注意: 未コミット変更が存在する作業ツリーを解析しています。")
    lines.append("")
    lines.append("## 構造仕様")
    lines.append("### セクション順序")
    for idx, section in enumerate(kita.sections, 1):
        lines.append(f"{idx}. id=`{section['id']}` class=`{section['class']}` h2=`{section['h2']}` h3数={len(section['h3'])}")
        for h3 in section["h3"]:
            lines.append(f"   - h3: {h3}")
    lines.append("")
    lines.append(f"- section数: {len(kita.sections)}")
    lines.append(f"- card/box系class使用数: {count_cards(kita)}")
    lines.append(f"- FAQ推定数: {count_faq(kita)}")
    lines.append(f"- table数: {len(kita.tables)}")
    lines.append("### table列構成")
    for idx, shape in enumerate(table_shapes(kita), 1):
        lines.append(f"- table {idx}: {shape}")
    lines.append("### 上部統計カード候補")
    for item in stat_cards(kita):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## スタイル仕様")
    lines.append("### 外部CSS")
    if kita.links:
        for href in kita.links:
            lines.append(f"- {href}")
    else:
        lines.append("- なし")
    lines.append(f"### インラインstyleブロック数: {len(kita.styles)}")
    for idx, selectors in enumerate(selectors_by_block, 1):
        lines.append(f"- style {idx}: selector数={len(selectors)}")
        for selector in selectors[:80]:
            lines.append(f"  - `{selector}`")
        if len(selectors) > 80:
            lines.append(f"  - ...他 {len(selectors) - 80} 件")
    lines.append("### body/h1/h2/h3 推定CSS")
    for selector in ["body", "h1", "h2", "h3"]:
        values = {
            "font-family": css_decl(all_styles, selector, "font-family"),
            "font-size": css_decl(all_styles, selector, "font-size"),
            "color": css_decl(all_styles, selector, "color"),
            "line-height": css_decl(all_styles, selector, "line-height"),
        }
        lines.append(f"- `{selector}`: " + ", ".join(f"{k}=`{v or '未抽出'}`" for k, v in values.items()))
    hero_selectors = [s for s in selector_list(all_styles) if "hero" in s.lower()]
    lines.append("### hero関連セレクタ")
    for selector in hero_selectors[:80]:
        lines.append(f"- `{selector}`")
    if len(hero_selectors) > 80:
        lines.append(f"- ...他 {len(hero_selectors) - 80} 件")
    lines.append("")
    lines.append("## 表記仕様")
    full_text = "\n".join(kita.text_chunks)
    years = sorted(set(re.findall(r"令和[0-9０-９]+年(?:国勢調査|住宅・土地統計調査)?|令和[0-9０-９]+年 国勢調査", full_text)))
    lines.append("### 統計基準年候補")
    for year in years:
        lines.append(f"- {year}")
    lines.append(f"### titleフォーマット: {title_format(kita.title)}")
    lines.append(f"- title: `{kita.title}`")
    lines.append(f"### meta descriptionフォーマット: {meta_format(kita.meta_description)}")
    lines.append(f"- meta description: `{kita.meta_description}`")
    lines.append("### 英字装飾ラベル候補")
    for label, count in kita.upper_labels.most_common():
        lines.append(f"- {label}: {count}")
    lines.append("### 出自地名class候補")
    origins = class_origin_patterns(kita.classes)
    for cls in origins:
        lines.append(f"- `{cls}`")
    SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPEC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(kita: PageParser, pages: list[Path]) -> None:
    kita_sig = section_signature(kita)
    kita_ids = [s[0] for s in kita_sig]
    kita_h2 = [s[1] for s in kita_sig]
    kita_links = sorted(kita.links)
    kita_style_count = len(kita.styles)
    kita_card_count = count_cards(kita)
    kita_faq_count = count_faq(kita)
    kita_table_count = len(kita.tables)
    kita_table_shapes = table_shapes(kita)
    kita_title_format = title_format(kita.title)
    kita_meta_format = meta_format(kita.meta_description)
    kita_labels = set(kita.upper_labels)
    kita_body_style = "\n".join(kita.styles)
    kita_css_values = {
        selector: (
            css_decl(kita_body_style, selector, "font-family"),
            css_decl(kita_body_style, selector, "font-size"),
            css_decl(kita_body_style, selector, "color"),
            css_decl(kita_body_style, selector, "line-height"),
        )
        for selector in ["body", "h1", "h2", "h3"]
    }

    buckets = {
        "section_count": DiffBucket(),
        "h2_count": DiffBucket(),
        "h3_count": DiffBucket(),
        "card_count": DiffBucket(),
        "faq_count": DiffBucket(),
        "table_count": DiffBucket(),
        "table_shape": DiffBucket(),
        "section_order": DiffBucket(),
        "missing_section": DiffBucket(),
        "extra_section": DiffBucket(),
        "css_links": DiffBucket(),
        "style_blocks_more": DiffBucket(),
        "font_diff": DiffBucket(),
        "stat_year": DiffBucket(),
        "title_meta": DiffBucket(),
        "labels": DiffBucket(),
        "origin_classes": DiffBucket(),
    }

    parsed_count = 0
    errors: list[str] = []
    for path in pages:
        try:
            parser = parse_page(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.relative_to(ROOT).as_posix()}: {exc}")
            continue
        parsed_count += 1
        if path == KITA_PATH:
            continue

        sections = parser.sections
        ids = [s["id"] for s in sections]
        h2s = [s["h2"] for s in sections]
        h3_count = sum(len(s["h3"]) for s in sections)

        if len(sections) != len(kita.sections):
            buckets["section_count"].add("section数違い", path, f"{len(sections)} vs {len(kita.sections)}")
        if len(h2s) != len(kita_h2):
            buckets["h2_count"].add("h2数違い", path, f"{len(h2s)} vs {len(kita_h2)}")
        if h3_count != sum(len(s["h3"]) for s in kita.sections):
            buckets["h3_count"].add("h3数違い", path, f"{h3_count} vs {sum(len(s['h3']) for s in kita.sections)}")
        card_count = count_cards(parser)
        if card_count != kita_card_count:
            buckets["card_count"].add("card/box数違い", path, f"{card_count} vs {kita_card_count}")
        faq_count = count_faq(parser)
        if faq_count != kita_faq_count:
            buckets["faq_count"].add("FAQ推定数違い", path, f"{faq_count} vs {kita_faq_count}")
        table_count = len(parser.tables)
        if table_count != kita_table_count:
            buckets["table_count"].add("table数違い", path, f"{table_count} vs {kita_table_count}")
        elif table_shapes(parser) != kita_table_shapes:
            buckets["table_shape"].add("table列構成違い", path)

        if ids != kita_ids:
            if set(ids) == set(kita_ids):
                buckets["section_order"].add("セクション順序違い", path)
            missing = [sid for sid in kita_ids if sid not in ids]
            extra = [sid for sid in ids if sid not in kita_ids]
            if missing:
                buckets["missing_section"].add("北区セクション欠落", path, ", ".join(missing))
            if extra:
                buckets["extra_section"].add("北区に無いセクション", path, ", ".join(extra[:20]))

        if sorted(parser.links) != kita_links:
            buckets["css_links"].add("参照CSS違い", path, f"{len(parser.links)} links")
        if len(parser.styles) > kita_style_count:
            buckets["style_blocks_more"].add("styleブロック多い", path, f"{len(parser.styles)} vs {kita_style_count}")

        style_text = "\n".join(parser.styles)
        diffs = []
        for selector in ["body", "h1", "h2", "h3"]:
            values = (
                css_decl(style_text, selector, "font-family"),
                css_decl(style_text, selector, "font-size"),
                css_decl(style_text, selector, "color"),
                css_decl(style_text, selector, "line-height"),
            )
            if values != kita_css_values[selector]:
                diffs.append(selector)
        if diffs:
            buckets["font_diff"].add("font/color/line-height違い", path, ", ".join(diffs))

        full_text = "\n".join(parser.text_chunks)
        has_reiwa2 = "令和2年" in full_text or "令和2年国勢調査" in full_text
        kita_has_reiwa2 = "令和2年" in "\n".join(kita.text_chunks)
        if has_reiwa2 != kita_has_reiwa2:
            buckets["stat_year"].add("統計基準年表記違い", path, f"令和2年あり={has_reiwa2}")
        if title_format(parser.title) != kita_title_format or meta_format(parser.meta_description) != kita_meta_format:
            buckets["title_meta"].add("title/meta形式違い", path, f"title={title_format(parser.title)}, meta={meta_format(parser.meta_description)}")
        if set(parser.upper_labels) != kita_labels:
            diff = sorted((set(parser.upper_labels) ^ kita_labels))[:20]
            buckets["labels"].add("英字ラベル差分", path, ", ".join(diff))
        origins = class_origin_patterns(parser.classes)
        non_kita_origins = [cls for cls in origins if not cls.startswith("kita-")]
        if non_kita_origins:
            buckets["origin_classes"].add("出自地名class", path, ", ".join(non_kita_origins[:20]))

    lines: list[str] = []
    lines.append("# 北区テンプレート乖離レポート")
    lines.append("")
    lines.append("## サマリー")
    lines.append(f"- 解析HTML数: {parsed_count}")
    lines.append(f"- 基準: `osaka/kita/index.html`")
    lines.append("- 注意: 未コミット変更が存在する作業ツリーを解析しています。`git pull` は未コミット大量変更のため未実行です。")
    for key, bucket in buckets.items():
        count = sum(len(items) for items in bucket.items.values())
        lines.append(f"- {key}: {count}件")
    if errors:
        lines.append(f"- 解析エラー: {len(errors)}件")
    lines.append("")

    labels = {
        "section_count": "構造の乖離: section数",
        "h2_count": "構造の乖離: h2数",
        "h3_count": "構造の乖離: h3数",
        "card_count": "構造の乖離: card/box数",
        "faq_count": "構造の乖離: FAQ数",
        "table_count": "構造の乖離: table数",
        "table_shape": "構造の乖離: table列構成",
        "section_order": "構造の乖離: セクション順序",
        "missing_section": "構造の乖離: 北区にあるセクション欠落",
        "extra_section": "構造の乖離: 北区に無いセクション",
        "css_links": "スタイルの乖離: 参照CSS",
        "style_blocks_more": "スタイルの乖離: インラインstyle過多",
        "font_diff": "スタイルの乖離: font/color/line-height",
        "stat_year": "表記の乖離: 統計基準年",
        "title_meta": "表記の乖離: title/meta",
        "labels": "表記の乖離: 英字ラベル",
        "origin_classes": "表記の乖離: 出自地名class",
    }
    for key, title in labels.items():
        bucket = buckets[key]
        lines.append(f"## {title}")
        if not bucket.items:
            lines.append("- 該当なし")
            lines.append("")
            continue
        for group, items in bucket.items.items():
            lines.append(f"### {group} ({len(items)}件)")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
    if errors:
        lines.append("## 解析エラー")
        for error in errors:
            lines.append(f"- {error}")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not KITA_PATH.exists():
        raise SystemExit(f"Kita template not found: {KITA_PATH}")
    kita = parse_page(KITA_PATH)
    pages = html_paths()
    write_spec(kita)
    write_report(kita, pages)
    print(f"wrote {SPEC_PATH.relative_to(ROOT).as_posix()}")
    print(f"wrote {REPORT_PATH.relative_to(ROOT).as_posix()}")
    print(f"html pages: {len(pages)}")


if __name__ == "__main__":
    main()
