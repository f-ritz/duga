"""Data gathering layer.

Responsibilities:
- Keyword web search
- Full website scraping (clean main content)
- Social handles (public data + recent posts)
- Media URL collection (for optional vision)

All functions are intentionally tolerant and return best-effort results.
They are designed to be easy to swap (e.g. replace DuckDuckGo with Tavily).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS  # preferred new package name
except ImportError:
    from duckduckgo_search import DDGS  # legacy fallback

from .config import get_env

# Polite scraping defaults
DEFAULT_HEADERS = {
    "User-Agent": "duga-briefing-bot/1.0 (+https://github.com/yourname/duga)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
REQUEST_TIMEOUT = 25
MAX_PAGES_PER_SITE = 1  # start conservative; can expand later
SLEEP_BETWEEN_REQUESTS = 0.8


@dataclass
class CollectedData:
    """Structured bucket of everything we found today."""
    keywords: list[str] = field(default_factory=list)
    web_results: list[dict[str, Any]] = field(default_factory=list)   # {title, href, body}
    websites: list[dict[str, Any]] = field(default_factory=list)      # {url, title, text}
    social: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # platform -> posts/profiles
    media_urls: list[str] = field(default_factory=list)               # images to consider for vision
    errors: list[str] = field(default_factory=list)


def _safe_get(url: str, **kwargs) -> requests.Response | None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:
        return None


def search_web(keywords: list[str], max_results: int = 15) -> list[dict[str, Any]]:
    """Search the web for the given keywords using DuckDuckGo (free, no key)."""
    if not keywords:
        return []

    results: list[dict[str, Any]] = []
    query = " OR ".join(f'"{k}"' if " " in k else k for k in keywords[:10])

    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title"),
                    "href": r.get("href"),
                    "body": r.get("body"),
                })
    except Exception as e:
        # Swallow search errors — we still want to continue
        print(f"[gather] web search error: {e}")

    # Dedup by href
    seen = set()
    unique = []
    for r in results:
        href = r.get("href")
        if href and href not in seen:
            seen.add(href)
            unique.append(r)
    return unique[:max_results]


def fetch_and_extract(url: str) -> dict[str, Any] | None:
    """Fetch a page and return clean main text using trafilatura (best effort)."""
    resp = _safe_get(url)
    if not resp:
        return None

    # Trafilatura is excellent for article/main-content extraction
    text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
    if not text or len(text) < 80:
        # Fallback to basic BS4
        soup = BeautifulSoup(resp.text, "lxml")
        # Remove script/style
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

    title = None
    if resp.text:
        soup = BeautifulSoup(resp.text, "lxml")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

    return {
        "url": url,
        "title": title or urlparse(url).netloc,
        "text": (text or "")[:12000],  # cap per page to control tokens
    }


def scrape_websites(urls: list[str], max_sites: int = 20) -> list[dict[str, Any]]:
    """Scrape a list of websites. Returns list of {url, title, text}."""
    results = []
    for i, url in enumerate(urls[:max_sites]):
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        extracted = fetch_and_extract(url)
        if extracted:
            results.append(extracted)
        time.sleep(SLEEP_BETWEEN_REQUESTS)
    return results


def _scrape_x_profile_basic(handle: str) -> dict[str, Any]:
    """Very lightweight public X profile + recent posts via profile page + search fallback.

    This is intentionally basic and fragile.
    For reliable production use, install twscrape and implement a better fetcher.
    """
    profile_url = f"https://x.com/{handle}"
    resp = _safe_get(profile_url)
    profile: dict[str, Any] = {"handle": handle, "url": profile_url, "bio": None, "posts": []}

    if resp and resp.text:
        soup = BeautifulSoup(resp.text, "lxml")
        # Best effort: grab meta description and some visible text
        desc = soup.find("meta", attrs={"name": "description"})
        if desc:
            profile["bio"] = desc.get("content")

        # Very rough post text scraping (X is heavily JS; this often gets limited content)
        tweets = []
        for t in soup.find_all("div", {"data-testid": "tweetText"})[:8]:
            tweets.append({"text": t.get_text(" ", strip=True)[:600]})
        if tweets:
            profile["posts"] = tweets

    # Supplement with web search for recent posts from this user (very useful fallback)
    try:
        with DDGS() as ddgs:
            q = f"from:{handle} OR site:x.com/{handle}"
            for r in ddgs.text(q, max_results=6):
                profile["posts"].append({
                    "text": (r.get("title") or "") + " — " + (r.get("body") or ""),
                    "source": r.get("href"),
                })
    except Exception:
        pass

    # Dedup
    seen = set()
    deduped = []
    for p in profile["posts"]:
        key = p.get("text", "")[:80]
        if key and key not in seen:
            seen.add(key)
            deduped.append(p)
    profile["posts"] = deduped[:10]
    return profile


def scrape_social(social: dict[str, list[str]]) -> dict[str, list[dict[str, Any]]]:
    """Scrape configured social platforms.

    Strongest support: "x" (Twitter).
    linkedin, facebook, threads, instagram and others fall back to web search
    (site: specific queries where possible). Public data only; many platforms
    require login for full access.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    platform_site_hints = {
        "linkedin": "site:linkedin.com",
        "facebook": "site:facebook.com",
        "threads": "site:threads.net",
        "instagram": "site:instagram.com",
    }

    for platform, handles in social.items():
        out[platform] = []
        for h in handles:
            if not h:
                continue
            if platform.lower() in ("x", "twitter"):
                prof = _scrape_x_profile_basic(h)
                out[platform].append(prof)
                time.sleep(0.6)
            else:
                # Generic + site-restricted search for better relevance
                try:
                    hint = platform_site_hints.get(platform.lower(), "")
                    query = f"{h} {hint}" if hint else f"{platform} {h}"
                    with DDGS() as ddgs:
                        for r in ddgs.text(query, max_results=5):
                            out[platform].append({
                                "handle": h,
                                "platform": platform,
                                "title": r.get("title"),
                                "body": r.get("body"),
                                "href": r.get("href"),
                            })
                except Exception:
                    pass
    return out


def collect_media_from_results(web: list[dict], sites: list[dict], social: dict) -> list[str]:
    """Extract image URLs found while gathering (very rough, for vision step)."""
    images: list[str] = []
    # From social posts (we don't have real media yet in basic scraper)
    # Future: parse actual <img> or API media fields
    # For now we just return empty or can extend fetchers later.
    return images[: int(get_env("MAX_IMAGES_TO_ANALYZE", "5") or 5)]


def gather_all(targets: Any) -> CollectedData:
    """Main entry point: run the full gather pipeline."""
    data = CollectedData(
        keywords=list(targets.keywords),
    )

    max_search = int(get_env("MAX_SEARCH_RESULTS", "15") or 15)
    max_sites = int(get_env("MAX_WEBSITES", "20") or 20)

    print(f"[gather] Searching web for {len(targets.keywords)} keywords...")
    data.web_results = search_web(targets.keywords, max_results=max_search)

    print(f"[gather] Scraping {len(targets.websites)} websites...")
    data.websites = scrape_websites(targets.websites, max_sites=max_sites)

    print(f"[gather] Fetching social profiles...")
    data.social = scrape_social(targets.social)

    data.media_urls = collect_media_from_results(
        data.web_results, data.websites, data.social
    )

    print(f"[gather] Done. web={len(data.web_results)} sites={len(data.websites)} social_platforms={len(data.social)}")
    return data


def format_for_llm(data: CollectedData, max_chars_per_section: int = 3500) -> str:
    """Turn collected data into a compact text block suitable for the LLM prompt."""
    lines: list[str] = []

    if data.keywords:
        lines.append("TRACKED KEYWORDS: " + ", ".join(data.keywords))
        lines.append("")

    if data.web_results:
        lines.append("## WEB SEARCH RESULTS")
        for r in data.web_results:
            lines.append(f"- {r.get('title') or 'Untitled'}")
            if r.get("href"):
                lines.append(f"  URL: {r['href']}")
            if r.get("body"):
                lines.append(f"  {r['body'][:400]}")
        lines.append("")

    if data.websites:
        lines.append("## WEBSITE CONTENT")
        for w in data.websites:
            lines.append(f"### {w.get('title') or w.get('url')}")
            lines.append(f"URL: {w.get('url')}")
            text = (w.get("text") or "")[:max_chars_per_section]
            lines.append(text)
            lines.append("")
        lines.append("")

    if data.social:
        lines.append("## SOCIAL PROFILES & POSTS")
        for platform, items in data.social.items():
            lines.append(f"### Platform: {platform}")
            for item in items:
                if platform in ("x", "twitter"):
                    lines.append(f"@{item.get('handle')}")
                    if item.get("bio"):
                        lines.append(f"Bio: {item['bio'][:300]}")
                    for p in item.get("posts", [])[:6]:
                        txt = p.get("text") or p.get("body") or ""
                        if txt:
                            lines.append(f"  • {txt[:280]}")
                else:
                    for entry in items[:5]:
                        lines.append(f"  {entry}")
            lines.append("")
        lines.append("")

    # Media note (textual for now)
    if data.media_urls:
        lines.append("## MEDIA DETECTED (consider for vision analysis)")
        for m in data.media_urls[:6]:
            lines.append(f"- {m}")
        lines.append("")

    full = "\n".join(lines)
    return full[:45000]  # generous safety cap before LLM call
