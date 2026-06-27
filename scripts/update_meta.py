#!/usr/bin/env python3
"""Normalize regional page meta tags.

The script intentionally rewrites only page metadata inside <head>:
title, meta description, existing og:title / og:description, and
meta keywords removal.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


PREFECTURE_SLUGS = {
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

PREFECTURE_NAMES = (
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
)

MUNICIPAL_SUFFIXES = ("市", "区", "町", "村", "郡")

PREF_TITLE_TEMPLATE = "{name}の遺品整理情報局｜費用相場と失敗しない業者の選び方｜遺品整理・生前整理.jp"
PREF_DESCRIPTION_TEMPLATE = (
    "{name}で遺品整理・生前整理を依頼する前に、料金相場、追加費用が出る条件、"
    "優良業者の見分け方、{name}の地域事情を確認できます。立会い不要や買取相殺にも対応した確認点を整理。"
)
MUNICIPAL_TITLE_TEMPLATE = "{name}の遺品整理情報局｜費用相場・業者の選び方｜遺品整理・生前整理.jp"
MUNICIPAL_DESCRIPTION_TEMPLATE = (
    "{name}で遺品整理を依頼する前に確認したい料金相場、追加費用の条件、"
    "悪質業者の見分け方、粗大ごみ・行政窓口など{name}の地域情報を整理しています。"
)

HEAD_RE = re.compile(r"(?is)<head\b[^>]*>.*?</head>")
HEAD_OPEN_RE = re.compile(r"(?is)<head\b[^>]*>")
TITLE_RE = re.compile(r"(?is)(<title\b[^>]*>)(.*?)(</title>)")
CONTENT_ATTR_RE = re.compile(r"(?is)(\bcontent\s*=\s*)([\"'])(.*?)\2")
H1_RE = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
BREADCRUMB_BLOCK_RE = re.compile(
    r"(?is)<(?P<tag>nav|div|ol|ul)\b[^>]*(?:class|id)\s*=\s*([\"'])"
    r"[^\"']*breadcrumb[^\"']*\2[^>]*>.*?</(?P=tag)>"
)


@dataclass
class PageResult:
    path: str
    kind: str
    official_name: str
    display_name: str
    title: str
    description: str
    changed: bool
    keywords_removed: int
    og_title_updated: int
    og_description_updated: int


@dataclass
class SkipResult:
    path: str
    reason: str


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def strip_tags(value: str) -> str:
    value = re.sub(r"(?is)<script\b.*?</script>", " ", value)
    value = re.sub(r"(?is)<style\b.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return normalize_ws(value)


def meta_tag_re(attr: str, value: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?is)<meta\b(?=[^>]*\b{attr}\s*=\s*([\"']){re.escape(value)}\1)[^>]*>"
    )


def extract_h1_texts(source: str) -> list[str]:
    return [strip_tags(match.group(1)) for match in H1_RE.finditer(source)]


def extract_breadcrumb_texts(source: str) -> list[str]:
    texts: list[str] = []
    for match in BREADCRUMB_BLOCK_RE.finditer(source):
        block_text = strip_tags(match.group(0))
        parts = re.split(r"\s*(?:>|›|/|｜|\|)\s*", block_text)
        texts.extend(part.strip() for part in parts if part.strip())
    return texts


def extract_prefecture_name(source: str) -> str | None:
    search_spaces = extract_h1_texts(source) + extract_breadcrumb_texts(source)
    for text in search_spaces:
        for pref_name in PREFECTURE_NAMES:
            if pref_name in text:
                return pref_name
    return None


def clean_region_name(value: str) -> str:
    value = normalize_ws(value)
    value = value.strip("【】[]「」『』")
    value = value.replace(" ", "").replace("　", "")
    return value


def extract_municipal_name_from_text(value: str) -> str | None:
    text = clean_region_name(value)
    # Prefer a region name immediately followed by copy grammar.
    match = re.match(r"^(.{1,50}[市区町村郡])(?:（[^）]+）)?(?:の|で|における|に対応)", text)
    if match:
        return clean_region_name(match.group(1))

    # Breadcrumb items are often just the region name.
    if is_valid_municipal_name(text):
        return text
    return None


def is_valid_municipal_name(value: str) -> bool:
    if not value or len(value) > 50:
        return False
    if value in PREFECTURE_NAMES:
        return False
    if not value.endswith(MUNICIPAL_SUFFIXES):
        return False
    if any(mark in value for mark in ("ホーム", "一覧", "料金", "遺品整理", "生前整理")):
        return False
    return True


def extract_municipal_name(source: str) -> str | None:
    for text in extract_h1_texts(source):
        name = extract_municipal_name_from_text(text)
        if name:
            return name
    for text in reversed(extract_breadcrumb_texts(source)):
        name = extract_municipal_name_from_text(text)
        if name:
            return name
    return None


def classify_path(root: Path, path: Path) -> str | None:
    rel_parts = path.relative_to(root).parts
    if len(rel_parts) == 2 and rel_parts[1] == "index.html" and rel_parts[0] in PREFECTURE_SLUGS:
        return "prefecture"
    if len(rel_parts) >= 3 and rel_parts[-1] == "index.html" and rel_parts[0] in PREFECTURE_SLUGS:
        return "municipal"
    return None


def shorten_prefecture_name(official_name: str) -> str:
    if official_name == "北海道":
        return official_name
    if official_name.endswith(("都", "府", "県")):
        return official_name[:-1]
    return official_name


def set_content_attr(tag: str, value: str) -> tuple[str, bool]:
    escaped = html.escape(value, quote=True)
    if CONTENT_ATTR_RE.search(tag):
        updated = CONTENT_ATTR_RE.sub(
            lambda match: f"{match.group(1)}{match.group(2)}{escaped}{match.group(2)}",
            tag,
            count=1,
        )
        return updated, updated != tag

    insert = f' content="{escaped}"'
    if tag.rstrip().endswith("/>"):
        updated = re.sub(r"\s*/>\s*$", f"{insert}>", tag)
    else:
        updated = re.sub(r">\s*$", f"{insert}>", tag)
    return updated, updated != tag


def set_title(head: str, title: str) -> tuple[str, bool]:
    escaped = html.escape(title, quote=False)
    if TITLE_RE.search(head):
        updated = TITLE_RE.sub(lambda match: f"{match.group(1)}{escaped}{match.group(3)}", head, count=1)
        return updated, updated != head
    updated = HEAD_OPEN_RE.sub(lambda match: f"{match.group(0)}\n  <title>{escaped}</title>", head, count=1)
    return updated, updated != head


def set_meta_name(head: str, name: str, value: str) -> tuple[str, bool]:
    tag_re = meta_tag_re("name", name)
    changed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        updated_tag, tag_changed = set_content_attr(match.group(0), value)
        changed = changed or tag_changed
        return updated_tag

    updated, count = tag_re.subn(replace, head)
    if count:
        return updated, changed

    escaped = html.escape(value, quote=True)
    meta_line = f'  <meta name="{name}" content="{escaped}">'
    inserted = TITLE_RE.sub(lambda match: f"{match.group(0)}\n{meta_line}", head, count=1)
    if inserted != head:
        return inserted, True
    inserted = HEAD_OPEN_RE.sub(lambda match: f"{match.group(0)}\n{meta_line}", head, count=1)
    return inserted, inserted != head


def set_existing_og(head: str, property_name: str, value: str) -> tuple[str, int]:
    tag_re = meta_tag_re("property", property_name)
    changed_count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed_count
        updated_tag, changed = set_content_attr(match.group(0), value)
        if changed:
            changed_count += 1
        return updated_tag

    updated = tag_re.sub(replace, head)
    return updated, changed_count


def remove_keywords(head: str) -> tuple[str, int]:
    tag_re = re.compile(
        r"(?is)[ \t]*<meta\b(?=[^>]*\bname\s*=\s*([\"'])keywords\1)[^>]*>[ \t]*(?:\r?\n)?"
    )
    return tag_re.subn("", head)


def process_page(root: Path, path: Path, dry_run: bool) -> tuple[PageResult | None, SkipResult | None]:
    rel = path.relative_to(root).as_posix()
    kind = classify_path(root, path)
    if kind is None:
        return None, None

    with path.open("r", encoding="utf-8", newline="") as handle:
        source = handle.read()
    head_match = HEAD_RE.search(source)
    if not head_match:
        return None, SkipResult(rel, "headタグが見つかりません")

    if kind == "prefecture":
        official_name = extract_prefecture_name(source)
        if not official_name:
            return None, SkipResult(rel, "H1/パンくずから都道府県名を解決できません")
        display_name = shorten_prefecture_name(official_name)
        title = PREF_TITLE_TEMPLATE.format(name=display_name)
        description = PREF_DESCRIPTION_TEMPLATE.format(name=display_name)
    else:
        official_name = extract_municipal_name(source)
        if not official_name:
            return None, SkipResult(rel, "H1/パンくずから市区町村名を解決できません")
        display_name = official_name
        title = MUNICIPAL_TITLE_TEMPLATE.format(name=display_name)
        description = MUNICIPAL_DESCRIPTION_TEMPLATE.format(name=display_name)

    old_head = head_match.group(0)
    new_head, _ = set_title(old_head, title)
    new_head, _ = set_meta_name(new_head, "description", description)
    new_head, keywords_removed = remove_keywords(new_head)
    new_head, og_title_updated = set_existing_og(new_head, "og:title", title)
    new_head, og_description_updated = set_existing_og(new_head, "og:description", description)

    changed = new_head != old_head
    if changed and not dry_run:
        updated_source = source[: head_match.start()] + new_head + source[head_match.end() :]
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(updated_source)

    return (
        PageResult(
            path=rel,
            kind=kind,
            official_name=official_name,
            display_name=display_name,
            title=title,
            description=description,
            changed=changed,
            keywords_removed=keywords_removed,
            og_title_updated=og_title_updated,
            og_description_updated=og_description_updated,
        ),
        None,
    )


def iter_paths(root: Path, raw_paths: list[str] | None) -> list[Path]:
    if raw_paths:
        return [(root / raw_path).resolve() for raw_path in raw_paths]
    return sorted(root.rglob("index.html"), key=lambda item: item.relative_to(root).as_posix())


def summarize(results: list[PageResult], skips: list[SkipResult]) -> dict[str, object]:
    changed_prefecture_pages = sum(1 for item in results if item.kind == "prefecture" and item.changed)
    changed_municipal_pages = sum(1 for item in results if item.kind == "municipal" and item.changed)
    target_prefecture_pages = sum(1 for item in results if item.kind == "prefecture")
    target_municipal_pages = sum(1 for item in results if item.kind == "municipal")
    keywords_deleted_pages = sum(1 for item in results if item.keywords_removed > 0)
    return {
        "target_prefecture_pages": target_prefecture_pages,
        "target_municipal_pages": target_municipal_pages,
        "changed_prefecture_pages": changed_prefecture_pages,
        "changed_municipal_pages": changed_municipal_pages,
        "keywords_deleted_pages": keywords_deleted_pages,
        "skipped_pages": [asdict(item) for item in skips],
        "changed_pages": [asdict(item) for item in results if item.changed],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize regional page metadata.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--paths", nargs="*", help="Explicit paths relative to root")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    results: list[PageResult] = []
    skips: list[SkipResult] = []

    for path in iter_paths(root, args.paths):
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        if not path.exists():
            skips.append(SkipResult(rel, "ファイルが存在しません"))
            continue
        page_result, skip_result = process_page(root, path, args.dry_run)
        if page_result:
            results.append(page_result)
        if skip_result:
            skips.append(skip_result)

    summary = summarize(results, skips)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"target prefecture pages: {summary['target_prefecture_pages']}")
        print(f"target municipal pages: {summary['target_municipal_pages']}")
        print(f"changed prefecture pages: {summary['changed_prefecture_pages']}")
        print(f"changed municipal pages: {summary['changed_municipal_pages']}")
        print(f"keywords deleted pages: {summary['keywords_deleted_pages']}")
        if skips:
            print("skipped pages:")
            for item in skips:
                print(f"- {item.path}: {item.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
