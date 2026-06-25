from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path


DOMAIN = "https://www.ihinseiri-seizenseiri.jp"
PUBLISHER_NAME = "遺品整理・生前整理.jp"

LD_RE = re.compile(
    r"\s*<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>.*?</script>\s*",
    re.I | re.S,
)
CANONICAL_RE = re.compile(
    r"\s*<link\b[^>]*rel=[\"']canonical[\"'][^>]*>\s*", re.I | re.S
)
MANAGED_STYLE_RE = re.compile(
    r"\s*<style id=[\"']schema-meta-style[\"']>.*?</style>\s*", re.I | re.S
)
LAST_UPDATED_RE = re.compile(
    r"\s*<p class=[\"']last-updated[\"'][^>]*data-schema-injected=[\"']true[\"'][^>]*>.*?</p>\s*",
    re.I | re.S,
)


def run_git(repo: Path, args: list[str]) -> str:
    out = subprocess.check_output(["git", "-C", str(repo), *args], text=True)
    return out.strip()


def strip_tags(fragment: str) -> str:
    fragment = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    text = re.sub(r"(?s)<[^>]+>", "", fragment)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*", "\n", text)
    return text.strip()


def attr_value(tag: str, name: str) -> str | None:
    pattern = re.compile(rf"\b{name}\s*=\s*([\"'])(.*?)\1", re.I | re.S)
    match = pattern.search(tag)
    return html.unescape(match.group(2).strip()) if match else None


def canonical_path(repo: Path, path: Path) -> str:
    rel = path.relative_to(repo).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def canonical_url(repo: Path, path: Path) -> str:
    return DOMAIN + canonical_path(repo, path)


def extract_meta_description(text: str) -> str:
    for match in re.finditer(r"<meta\b[^>]*>", text, re.I | re.S):
        tag = match.group(0)
        if (attr_value(tag, "name") or "").lower() == "description":
            return attr_value(tag, "content") or ""
    return ""


def extract_h1(text: str) -> str:
    match = re.search(r"(?is)<h1\b[^>]*>(.*?)</h1>", text)
    return strip_tags(match.group(1)) if match else ""


class BreadcrumbParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict[str, str | None]] = []
        self.in_breadcrumb = False
        self.depth = 0
        self.in_a = False
        self.current_href: str | None = None
        self.current_text: list[str] = []
        self.loose_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): v or "" for k, v in attrs}
        if not self.in_breadcrumb:
            aria = attrs_dict.get("aria-label", "")
            klass = attrs_dict.get("class", "")
            if "パンくず" in aria or "breadcrumb" in klass:
                self.in_breadcrumb = True
                self.depth = 1
        else:
            self.depth += 1
        if self.in_breadcrumb and tag.lower() == "a":
            self.in_a = True
            self.current_href = attrs_dict.get("href")
            self.current_text = []

    def handle_endtag(self, tag: str) -> None:
        if self.in_breadcrumb and tag.lower() == "a" and self.in_a:
            label = " ".join("".join(self.current_text).split())
            if label:
                self.items.append({"name": label, "href": self.current_href})
            self.in_a = False
            self.current_href = None
            self.current_text = []
        if self.in_breadcrumb:
            self.depth -= 1
            if self.depth <= 0:
                text = " ".join("".join(self.loose_text).replace("›", " ").split())
                if text:
                    parts = [p for p in re.split(r"\s{2,}|>", text) if p.strip()]
                    if parts:
                        self.items.append({"name": parts[-1].strip(), "href": None})
                self.in_breadcrumb = False

    def handle_data(self, data: str) -> None:
        if self.in_breadcrumb and self.in_a:
            self.current_text.append(data)
        elif self.in_breadcrumb:
            cleaned = data.strip()
            if cleaned and cleaned != "›":
                self.loose_text.append(cleaned)


def make_absolute_url(href: str | None, current_url: str) -> str:
    if not href:
        return current_url
    href = href.strip()
    if href.startswith("http://") or href.startswith("https://"):
        return re.sub(r"^https://ihinseiri-seizenseiri\.jp", DOMAIN, href)
    if href.startswith("/"):
        return DOMAIN + href
    return current_url


def extract_breadcrumbs(text: str, current_url: str) -> list[dict[str, str]]:
    parser = BreadcrumbParser()
    parser.feed(text)
    items = []
    seen = set()
    for item in parser.items:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        url = make_absolute_url(item.get("href"), current_url)
        key = (name, url)
        if key in seen:
            continue
        seen.add(key)
        items.append({"name": name, "url": url})
    if items:
        if items[-1]["url"] != current_url:
            items[-1]["url"] = current_url
        return items
    return [{"name": PUBLISHER_NAME, "url": DOMAIN + "/"}]


def extract_faq(text: str) -> list[dict[str, str]]:
    match = re.search(
        r"(?is)<section\b[^>]*\bid=[\"']faq[\"'][^>]*>(.*?)</section>", text
    )
    if not match:
        return []
    section = match.group(1)
    qas = []
    detail_re = re.compile(
        r"(?is)<details\b[^>]*>\s*<summary\b[^>]*>(.*?)</summary>(.*?)</details>"
    )
    for detail in detail_re.finditer(section):
        question = strip_tags(detail.group(1))
        body = detail.group(2)
        answer_match = re.search(r"(?is)<p\b[^>]*>(.*?)</p>", body)
        answer = strip_tags(answer_match.group(1) if answer_match else body)
        if question and answer:
            qas.append({"question": question, "answer": answer})
    return qas


def git_date_for(repo: Path, path: Path) -> str:
    rel = path.relative_to(repo).as_posix()
    date = run_git(repo, ["log", "-1", "--format=%cs", "--", rel])
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise RuntimeError(f"Git commit date not found for {rel}")
    return date


def build_jsonld(
    breadcrumbs: list[dict[str, str]],
    faqs: list[dict[str, str]],
    headline: str,
    description: str,
    url: str,
    date: str,
) -> str:
    nodes: list[dict[str, object]] = [
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i,
                    "name": item["name"],
                    "item": item["url"],
                }
                for i, item in enumerate(breadcrumbs, start=1)
            ],
        }
    ]
    if faqs:
        nodes.append(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": qa["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": qa["answer"],
                        },
                    }
                    for qa in faqs
                ],
            }
        )
    nodes.append(
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": headline,
            "description": description,
            "inLanguage": "ja",
            "publisher": {"@type": "Organization", "name": PUBLISHER_NAME},
            "datePublished": date,
            "dateModified": date,
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        }
    )
    return json.dumps(nodes, ensure_ascii=False, indent=2)


def inject_one(repo: Path, path: Path, dry_run: bool = False) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if "<head" not in text.lower() or "</head>" not in text.lower():
        raise RuntimeError(f"No head found: {path}")

    url = canonical_url(repo, path)
    date = git_date_for(repo, path)
    description = extract_meta_description(text)
    headline = extract_h1(text) or description or PUBLISHER_NAME
    breadcrumbs = extract_breadcrumbs(text, url)
    faqs = extract_faq(text)
    jsonld = build_jsonld(breadcrumbs, faqs, headline, description, url, date)

    head_match = re.search(r"(?is)(<head\b[^>]*>)(.*?)(</head>)", text)
    assert head_match
    head_open, head, head_close = head_match.groups()
    head = CANONICAL_RE.sub("\n", head)
    head = LD_RE.sub("\n", head)
    head = MANAGED_STYLE_RE.sub("\n", head)
    head = head.rstrip()
    injected = (
        f'\n  <link rel="canonical" href="{html.escape(url, quote=True)}">\n'
        '  <style id="schema-meta-style">'
        ".last-updated{width:min(1160px,calc(100% - 28px));"
        "margin:28px auto;color:#6f6a62;font-size:13px;"
        "line-height:1.7;text-align:right}"
        "@media(max-width:720px){.last-updated{text-align:left}}"
        "</style>\n"
        '  <script type="application/ld+json">\n'
        f"{jsonld}\n"
        "  </script>"
    )
    new_head = f"{head_open}{head}{injected}\n{head_close}"
    updated = text[: head_match.start()] + new_head + text[head_match.end() :]
    updated = LAST_UPDATED_RE.sub("\n", updated)
    stamp = (
        f'\n  <p class="last-updated" data-schema-injected="true">'
        f"最終更新日：{date}</p>\n"
    )
    if re.search(r"(?is)</body>", updated):
        updated = re.sub(r"(?is)\s*</body>", stamp + "</body>", updated, count=1)
    else:
        updated = updated.rstrip() + stamp

    if not dry_run and updated != text:
        path.write_text(updated, encoding="utf-8", newline="")
    return {
        "path": path.relative_to(repo).as_posix(),
        "url": url,
        "date": date,
        "faq_count": len(faqs),
        "breadcrumb_count": len(breadcrumbs),
        "jsonld": jsonld,
    }


def list_pages(repo: Path) -> list[Path]:
    pages = []
    skip = {".git", "work", "scripts"}
    for path in repo.rglob("*.html"):
        if any(part in skip for part in path.relative_to(repo).parts):
            continue
        pages.append(path)
    return sorted(pages, key=lambda p: p.relative_to(repo).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("pages", nargs="*")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    if args.all:
        pages = list_pages(repo)
    elif args.sample:
        pages = [
            repo / "index.html",
            repo / "osaka" / "index.html",
            repo / "osaka" / "toyonaka" / "index.html",
        ]
    else:
        pages = [repo / p for p in args.pages]
    if not pages:
        parser.error("Specify --all, --sample, or page paths")

    results = [inject_one(repo, p, dry_run=args.dry_run) for p in pages]
    summary = {
        "page_count": len(results),
        "faq_page_count": sum(1 for result in results if result["faq_count"]),
        "faq_total_count": sum(int(result["faq_count"]) for result in results),
        "sample": results[:3],
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
