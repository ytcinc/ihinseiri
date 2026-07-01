#!/usr/bin/env python3
"""Normalize title and meta descriptions for regional pages.

Only metadata in <head> is changed:
- <title>
- <meta name="description">
- existing og:title / og:description
- <meta name="keywords"> removal
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


PREFECTURES = {
    "hokkaido": "北海道",
    "aomori": "青森県",
    "iwate": "岩手県",
    "miyagi": "宮城県",
    "akita": "秋田県",
    "yamagata": "山形県",
    "fukushima": "福島県",
    "ibaraki": "茨城県",
    "tochigi": "栃木県",
    "gunma": "群馬県",
    "saitama": "埼玉県",
    "chiba": "千葉県",
    "tokyo": "東京都",
    "kanagawa": "神奈川県",
    "niigata": "新潟県",
    "toyama": "富山県",
    "ishikawa": "石川県",
    "fukui": "福井県",
    "yamanashi": "山梨県",
    "nagano": "長野県",
    "gifu": "岐阜県",
    "shizuoka": "静岡県",
    "aichi": "愛知県",
    "mie": "三重県",
    "shiga": "滋賀県",
    "kyoto": "京都府",
    "osaka": "大阪府",
    "hyogo": "兵庫県",
    "nara": "奈良県",
    "wakayama": "和歌山県",
    "tottori": "鳥取県",
    "shimane": "島根県",
    "okayama": "岡山県",
    "hiroshima": "広島県",
    "yamaguchi": "山口県",
    "tokushima": "徳島県",
    "kagawa": "香川県",
    "ehime": "愛媛県",
    "kochi": "高知県",
    "fukuoka": "福岡県",
    "saga": "佐賀県",
    "nagasaki": "長崎県",
    "kumamoto": "熊本県",
    "oita": "大分県",
    "miyazaki": "宮崎県",
    "kagoshima": "鹿児島県",
    "okinawa": "沖縄県",
}

PREF_TITLE = "{name}の遺品整理情報局｜費用相場と失敗しない業者の選び方｜遺品整理・生前整理.jp"
PREF_DESCRIPTION = (
    "{name}で遺品整理・生前整理を依頼する前に、料金相場、追加費用が出る条件、"
    "優良業者の見分け方、{name}の地域事情を確認できます。"
    "立会い不要や買取相殺にも対応した確認点を整理。"
)
CITY_TITLE = "{name}の遺品整理情報局｜費用相場・業者の選び方｜遺品整理・生前整理.jp"
CITY_DESCRIPTION = (
    "{name}で遺品整理を依頼する前に確認したい料金相場、追加費用の条件、"
    "悪質業者の見分け方、粗大ごみ・行政窓口など{name}の地域情報を整理しています。"
)

HEAD_RE = re.compile(r"(?is)<head\b[^>]*>.*?</head>")
HEAD_OPEN_RE = re.compile(r"(?is)<head\b[^>]*>")
TITLE_RE = re.compile(r"(?is)(<title\b[^>]*>)(.*?)(</title>)")
META_RE = re.compile(r"(?is)<meta\b[^>]*>")
CONTENT_RE = re.compile(r"(?is)(\bcontent\s*=\s*)([\"'])(.*?)\2")
H1_RE = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
BREADCRUMB_RE = re.compile(
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


def strip_tags(value: str) -> str:
    value = re.sub(r"(?is)<script\b.*?</script>", " ", value)
    value = re.sub(r"(?is)<style\b.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def classify(root: Path, path: Path) -> str | None:
    parts = path.relative_to(root).parts
    if len(parts) == 2 and parts[1] == "index.html" and parts[0] in PREFECTURES:
        return "prefecture"
    if len(parts) >= 3 and parts[-1] == "index.html" and parts[0] in PREFECTURES:
        return "municipal"
    return None


def breadcrumb_items(source: str) -> list[str]:
    items: list[str] = []
    for match in BREADCRUMB_RE.finditer(source):
        text = strip_tags(match.group(0))
        for item in re.split(r"\s*(?:›|>|/|｜|\|)\s*", text):
            item = clean_name(item)
            if item:
                items.append(item)
    return items


def h1_texts(source: str) -> list[str]:
    return [strip_tags(match.group(1)) for match in H1_RE.finditer(source)]


def clean_name(value: str) -> str:
    value = re.sub(r"\s+", "", html.unescape(value))
    return value.strip("「」『』[]（）()")


def valid_prefecture_name(value: str) -> bool:
    return value in PREFECTURES.values()


def valid_municipal_name(value: str) -> bool:
    if not value or len(value) > 40:
        return False
    if value in PREFECTURES.values() or value in {"TOP", "トップ"}:
        return False
    if not value.endswith(("市", "区", "町", "村")):
        return False
    if any(token in value for token in ("遺品整理", "生前整理", "料金", "業者", "情報局", "一覧")):
        return False
    return bool(re.search(r"[一-龥ぁ-んァ-ヶ]", value))


def municipal_from_text(text: str) -> str | None:
    text = clean_name(text)
    if valid_municipal_name(text):
        return text

    patterns = [
        r"^(.{1,30}(?:市.+区|市|区|町|村))で",
        r"^(.{1,30}(?:市.+区|市|区|町|村))の",
        r"^(.{1,30}(?:市.+区|市|区|町|村))に",
    ]
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            candidate = clean_name(match.group(1))
            if valid_municipal_name(candidate):
                return candidate
    return None


def extract_prefecture_name(source: str) -> str | None:
    texts = breadcrumb_items(source) + h1_texts(source)
    for text in texts:
        item = clean_name(text)
        if valid_prefecture_name(item):
            return item
        for pref_name in PREFECTURES.values():
            if pref_name in item:
                return pref_name
    return None


def extract_municipal_name(source: str) -> str | None:
    for text in reversed(breadcrumb_items(source)):
        name = municipal_from_text(text)
        if name:
            return name
    for text in h1_texts(source):
        name = municipal_from_text(text)
        if name:
            return name
    return None


def shorten_prefecture(name: str) -> str:
    if name == "北海道":
        return name
    if name.endswith(("都", "府", "県")):
        return name[:-1]
    return name


def meta_has_attr(tag: str, attr: str, value: str) -> bool:
    return re.search(rf"(?is)\b{attr}\s*=\s*([\"']){re.escape(value)}\1", tag) is not None


def set_content(tag: str, value: str) -> tuple[str, bool]:
    escaped = html.escape(value, quote=True)
    if CONTENT_RE.search(tag):
        updated = CONTENT_RE.sub(
            lambda match: f"{match.group(1)}{match.group(2)}{escaped}{match.group(2)}",
            tag,
            count=1,
        )
        return updated, updated != tag
    updated = re.sub(r"\s*/?>\s*$", f' content="{escaped}">', tag)
    return updated, updated != tag


def set_title(head: str, title: str) -> tuple[str, bool]:
    escaped = html.escape(title, quote=False)
    if TITLE_RE.search(head):
        updated = TITLE_RE.sub(lambda m: f"{m.group(1)}{escaped}{m.group(3)}", head, count=1)
        return updated, updated != head
    updated = HEAD_OPEN_RE.sub(lambda m: f"{m.group(0)}\n  <title>{escaped}</title>", head, count=1)
    return updated, updated != head


def set_meta_name(head: str, name: str, value: str) -> tuple[str, bool]:
    changed = False
    found = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed, found
        tag = match.group(0)
        if not meta_has_attr(tag, "name", name):
            return tag
        found += 1
        if found > 1:
            changed = True
            return ""
        updated, tag_changed = set_content(tag, value)
        changed = changed or tag_changed
        return updated

    updated = META_RE.sub(replace, head)
    if found:
        cleaned = re.sub(r"(?m)^[ \t]+\r?$", "", updated)
        if cleaned != updated:
            changed = True
            updated = cleaned
        return updated, changed

    line = f'  <meta name="{name}" content="{html.escape(value, quote=True)}">'
    inserted = TITLE_RE.sub(lambda m: f"{m.group(0)}\n{line}", head, count=1)
    if inserted != head:
        return inserted, True
    inserted = HEAD_OPEN_RE.sub(lambda m: f"{m.group(0)}\n{line}", head, count=1)
    return inserted, inserted != head


def set_existing_og(head: str, prop: str, value: str) -> tuple[str, int]:
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        tag = match.group(0)
        if not meta_has_attr(tag, "property", prop):
            return tag
        updated, changed = set_content(tag, value)
        if changed:
            count += 1
        return updated

    return META_RE.sub(replace, head), count


def remove_keywords(head: str) -> tuple[str, int]:
    pattern = re.compile(
        r"(?im)^[ \t]*<meta\b(?=[^>]*\bname\s*=\s*([\"'])keywords\1)[^>]*>[ \t]*(?:\r?\n)?"
    )
    return pattern.subn("", head)


def process_page(root: Path, path: Path, dry_run: bool) -> tuple[PageResult | None, SkipResult | None]:
    rel = path.relative_to(root).as_posix()
    kind = classify(root, path)
    if kind is None:
        return None, None

    with path.open("r", encoding="utf-8", newline="") as handle:
        source = handle.read()
    head_match = HEAD_RE.search(source)
    if not head_match:
        return None, SkipResult(rel, "<head> が見つかりません")

    if kind == "prefecture":
        official_name = extract_prefecture_name(source)
        if not official_name:
            return None, SkipResult(rel, "H1/パンくずから都道府県名を解決できません")
        display_name = shorten_prefecture(official_name)
        title = PREF_TITLE.format(name=display_name)
        description = PREF_DESCRIPTION.format(name=display_name)
    else:
        official_name = extract_municipal_name(source)
        if not official_name:
            return None, SkipResult(rel, "H1/パンくずから市区町村名を解決できません")
        display_name = official_name
        title = CITY_TITLE.format(name=display_name)
        description = CITY_DESCRIPTION.format(name=display_name)

    old_head = head_match.group(0)
    new_head, _ = set_title(old_head, title)
    new_head, _ = set_meta_name(new_head, "description", description)
    new_head, keywords_removed = remove_keywords(new_head)
    new_head, og_title_updated = set_existing_og(new_head, "og:title", title)
    new_head, og_description_updated = set_existing_og(new_head, "og:description", description)
    changed = new_head != old_head

    if changed and not dry_run:
        updated = source[: head_match.start()] + new_head + source[head_match.end() :]
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(updated)

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
    return sorted(root.rglob("index.html"), key=lambda path: path.relative_to(root).as_posix())


def summarize(results: list[PageResult], skips: list[SkipResult]) -> dict[str, object]:
    return {
        "target_prefecture_pages": sum(1 for item in results if item.kind == "prefecture"),
        "target_municipal_pages": sum(1 for item in results if item.kind == "municipal"),
        "changed_prefecture_pages": sum(1 for item in results if item.kind == "prefecture" and item.changed),
        "changed_municipal_pages": sum(1 for item in results if item.kind == "municipal" and item.changed),
        "keywords_deleted_pages": sum(1 for item in results if item.keywords_removed > 0),
        "changed_pages": [asdict(item) for item in results if item.changed],
        "skipped_pages": [asdict(item) for item in skips],
        "all_pages": [asdict(item) for item in results],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize regional page metadata.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--paths", nargs="*", help="Paths relative to root")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files")
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
