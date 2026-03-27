from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from .models import SourceConfig

# URL path segments that indicate a real article (not nav / footer / legal).
_ARTICLE_PATH_HINTS = [
    "/news", "/blog", "/research", "/article", "/insights", "/press",
    "/stories", "/posts", "/perspective", "/engineering", "/paper",
    "/feed/", "/updates",
]


def _is_allowed(url: str, source: SourceConfig) -> bool:
    netloc = urlparse(url).netloc.lower()
    return any(netloc == d or netloc.endswith('.' + d) for d in source.allowed_domains)


def _is_excluded(url: str, source: SourceConfig) -> bool:
    return any(pat in url for pat in source.exclude_url_patterns)


def discover_listing_urls(source: SourceConfig) -> list[str]:
    urls = [source.landing_url]
    for p in source.candidate_paths:
        urls.append(urljoin(source.landing_url, p))
    out = []
    seen = set()
    for u in urls:
        if u not in seen and _is_allowed(u, source) and not _is_excluded(u, source):
            seen.add(u)
            out.append(u)
    return out


def _extract_rss_links(xml_text: str, listing_url: str, source: SourceConfig) -> list[str]:
    """Extract article URLs from RSS/Atom XML content."""
    links = []
    seen = set()
    # Match <link>URL</link> (RSS) and <link href="URL"/> (Atom)
    for url in re.findall(r'<link[^>]*>([^<]+)</link>', xml_text):
        url = url.strip()
        if url and url.startswith("http") and url not in seen:
            if _is_allowed(url, source) and not _is_excluded(url, source):
                seen.add(url)
                links.append(url)
    for url in re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', xml_text):
        url = url.strip()
        if url and url.startswith("http") and url not in seen:
            if _is_allowed(url, source) and not _is_excluded(url, source):
                seen.add(url)
                links.append(url)
    return links


def discover_article_links(listing_html: str, listing_url: str, source: SourceConfig) -> list[str]:
    # Detect RSS/Atom feed content and use specialized parser.
    is_feed = (
        listing_html.lstrip()[:200].startswith("<?xml")
        or "<rss" in listing_html[:500]
        or "<feed" in listing_html[:500]
    )
    if is_feed:
        return _extract_rss_links(listing_html, listing_url, source)[:120]

    links = []
    seen = set()
    for href in re.findall(r'href=["\']([^"\']+)["\']', listing_html, flags=re.I):
        full = urljoin(listing_url, href.strip())
        if not full.startswith("http"):
            continue
        if not _is_allowed(full, source) or _is_excluded(full, source):
            continue
        low = full.lower()
        if not any(k in low for k in _ARTICLE_PATH_HINTS):
            continue
        if full not in seen:
            seen.add(full)
            links.append(full)
    return links[:120]
