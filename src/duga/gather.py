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
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS  # preferred new package name
except ImportError:
    from duckduckgo_search import DDGS  # legacy fallback

from .config import get_env, Targets

import logging
log = logging.getLogger(__name__)

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
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _safe_get(url: str, **kwargs) -> requests.Response | None:
    try:
        headers = DEFAULT_HEADERS.copy()
        headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        headers["Pragma"] = "no-cache"
        headers["Expires"] = "0"
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, **kwargs)
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
    log.info(f"Web search query (first 10 kws): {query[:200]}")

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
        log.warning(f"web search error: {e}")

    # Dedup by href
    seen = set()
    unique = []
    for r in results:
        href = r.get("href")
        if href and href not in seen:
            seen.add(href)
            unique.append(r)
    log.debug(f"Web search returned {len(unique)} unique results for query")
    return unique[:max_results]


def fetch_and_extract(url: str) -> dict[str, Any] | None:
    """Fetch a page and return clean main text using trafilatura (best effort)."""
    resp = _safe_get(url)
    if not resp:
        log.warning(f"Failed to GET {url}")
        return None

    # Trafilatura is excellent for article/main-content extraction
    # Provide a config explicitly to avoid missing settings.cfg in bundled envs
    try:
        config = trafilatura.settings.use_config()
        # ensure the required option exists (in case config load was partial)
        if not config.has_option("DEFAULT", "min_extracted_size"):
            config.set("DEFAULT", "min_extracted_size", "250")
            config.set("DEFAULT", "min_extracted_comm_size", "1")
            config.set("DEFAULT", "min_output_size", "1")
            config.set("DEFAULT", "min_output_comm_size", "1")
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=False, config=config)
    except Exception:
        text = None
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

    extracted_len = len(text or "")
    log.debug(f"Extracted {extracted_len} chars from {url}")
    return {
        "url": url,
        "title": title or urlparse(url).netloc,
        "text": (text or "")[:12000],  # cap per page to control tokens
        "fetched": datetime.now(timezone.utc).isoformat(),
    }


def scrape_websites(urls: list[str], max_sites: int = 20) -> list[dict[str, Any]]:
    """Scrape a list of websites. Returns list of {url, title, text}."""
    results = []
    for i, url in enumerate(urls[:max_sites]):
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        log.debug(f"Fetching website {i+1}/{len(urls[:max_sites])}: {url}")
        extracted = fetch_and_extract(url)
        if extracted:
            text_len = len(extracted.get("text", ""))
            log.debug(f"  Extracted {text_len} chars from {url}")
            results.append(extracted)
        else:
            log.warning(f"  Failed to extract content from {url}")
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
        log.debug(f"X profile @{handle} + search: {len(profile['posts'])} post snippets")
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


def _scrape_instagram_profile_basic(handle: str) -> dict[str, Any]:
    """Lightweight public Instagram profile scan via direct URL fetch + search fallback.

    We fetch the profile page directly (like websites and X profiles) to "scan the
    whole profile at once". Private accounts will just yield limited or no data ("oh well").
    Supplement with web search for posts/mentions.
    """
    clean = (handle or "").strip().lstrip("@")
    profile_url = f"https://www.instagram.com/{clean}/"
    resp = _safe_get(profile_url)

    profile: dict[str, Any] = {
        "handle": clean,
        "url": profile_url,
        "bio": None,
        "posts": [],
    }

    page_text = ""
    if resp and resp.text:
        soup = BeautifulSoup(resp.text, "lxml")
        desc = soup.find("meta", attrs={"name": "description"})
        if desc:
            profile["bio"] = desc.get("content")

        # Basic visible text
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        page_text = soup.get_text(separator="\n", strip=True)[:4000]

    # Full profile scan using the website extractor (trafilatura + fallback)
    extracted = fetch_and_extract(profile_url)
    if extracted:
        if extracted.get("text"):
            if not profile.get("bio"):
                profile["bio"] = extracted["text"][:600]
            page_text = extracted["text"] or page_text

    # Add page content as a "post" so the full profile scan makes it into the briefing
    if page_text:
        profile["posts"].append({
            "text": page_text[:1500],
            "source": profile_url,
        })

    # Supplement with search (like other platforms)
    try:
        with DDGS() as ddgs:
            q = f"site:instagram.com/{clean} OR \"{clean}\" instagram"
            for r in ddgs.text(q, max_results=10):
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
        key = (p.get("text") or "")[:80]
        if key and key not in seen:
            seen.add(key)
            deduped.append(p)
    profile["posts"] = deduped[:15]
    return profile


def scrape_social(social: dict[str, list[str]]) -> dict[str, list[dict[str, Any]]]:
    """Scrape configured social platforms.

    X/Twitter and Instagram get direct profile page scans (URL fetch) + search fallback.
    Other platforms use site-restricted web search.
    Private profiles may return limited data.
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
        clean_handles = [h.strip() for h in handles if h and h.strip()]
        if not clean_handles:
            continue
        if platform.lower() in ("x", "twitter"):
            for h in clean_handles:
                prof = _scrape_x_profile_basic(h)
                out[platform].append(prof)
                time.sleep(0.6)
        elif platform.lower() == "instagram":
            # Scan IG profiles by direct URL + search (no special scraper)
            # We fetch the full profile page ("whole profile at once")
            for h in clean_handles:
                prof = _scrape_instagram_profile_basic(h)
                out[platform].append(prof)
                time.sleep(0.5)
        else:
            # Generic + site-restricted search for better relevance
            for h in clean_handles:
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
                    log.debug(f"Social search for {platform}/{h} returned results")
                except Exception as e:
                    log.debug(f"Social search error for {platform}/{h}: {e}")
    return out


def collect_media_from_results(web: list[dict], sites: list[dict], social: dict) -> list[str]:
    """Extract image/video URLs found while gathering for vision/AI description step."""
    images: list[str] = []
    # Pull from IG (and other social) posts that we enhanced
    for plat_items in (social or {}).values():
        for profile in plat_items or []:
            for post in profile.get("posts", []) or []:
                for mu in post.get("mediaUrls", []) or []:
                    if mu and mu not in images:
                        images.append(mu)
    # Could extend for website images or web results here if needed (trafilatura can give images)
    # but focus on IG content as primary visual source for now.
    max_v = int(get_env("MAX_IMAGES_TO_ANALYZE", "5") or 5)
    selected = images[:max_v]
    if selected:
        log.info(f"Collected {len(selected)} media URL(s) for vision analysis")
    return selected


def gather_all(targets: Any) -> CollectedData:
    """Main entry point: run the full gather pipeline."""
    data = CollectedData(
        keywords=list(targets.keywords),
    )

    max_search = int(get_env("MAX_SEARCH_RESULTS", "15") or 15)
    max_sites = int(get_env("MAX_WEBSITES", "20") or 20)

    log.info(f"Searching web for {len(targets.keywords)} keywords...")
    data.web_results = search_web(targets.keywords, max_results=max_search)

    log.info(f"Scraping {len(targets.websites)} websites...")
    data.websites = scrape_websites(targets.websites, max_sites=max_sites)

    log.info("Fetching social profiles...")
    data.social = scrape_social(targets.social)

    data.media_urls = collect_media_from_results(
        data.web_results, data.websites, data.social
    )

    log.info(f"Done gathering. web_results={len(data.web_results)} websites={len(data.websites)} social_platforms={len(data.social)} media={len(data.media_urls)}")
    return data


def format_for_llm(data: CollectedData, max_chars_per_section: int = 3500) -> str:
    """Turn collected data into a compact text block suitable for the LLM prompt."""
    lines: list[str] = []

    lines.append(f"DATA FETCHED AT: {data.fetched_at} (all content below is live as of this time)")
    lines.append("")

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
            if w.get("fetched"):
                lines.append(f"Fetched: {w['fetched']}")
            text = (w.get("text") or "")[:max_chars_per_section]
            lines.append(text)
            lines.append("")
        lines.append("")

    if data.social:
        lines.append("## SOCIAL PROFILES & POSTS")
        for platform, items in data.social.items():
            lines.append(f"### Platform: {platform}")
            for item in items:
                if platform in ("x", "twitter", "instagram"):
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
    log.debug(f"Formatted LLM input size: {len(full)} chars")
    return full[:45000]  # generous safety cap before LLM call


def count_target_entries(targets: Targets) -> int:
    """Count total 'entries' across keywords + websites + all social handles."""
    if not targets:
        return 0
    n = len(getattr(targets, "keywords", []) or [])
    n += len(getattr(targets, "websites", []) or [])
    social = getattr(targets, "social", {}) or {}
    for handles in social.values():
        n += len(handles or [])
    return n


def chunk_targets(targets: Targets, chunk_size: int = 10) -> list[Targets]:
    """Split targets into smaller Targets objects of at most ~chunk_size entries each.

    An 'entry' is one keyword, one website URL, or one social handle.
    Each returned chunk is a valid Targets dataclass that can be passed to gather_all.
    If total entries <= chunk_size (or chunk_size <= 0), returns [targets] unchanged.
    """
    if not targets or chunk_size <= 0:
        return [targets]

    keywords = list(getattr(targets, "keywords", []) or [])
    websites = list(getattr(targets, "websites", []) or [])
    social = {k: list(v or []) for k, v in (getattr(targets, "social", {}) or {}).items()}

    entries: list = []
    for kw in keywords:
        if kw and str(kw).strip():
            entries.append(("keyword", str(kw).strip()))
    for url in websites:
        if url and str(url).strip():
            entries.append(("website", str(url).strip()))
    for plat, handles in social.items():
        for h in handles:
            if h and str(h).strip():
                entries.append(("social", plat, str(h).strip()))

    total = len(entries)
    if total <= chunk_size:
        return [targets]

    chunks: list[Targets] = []
    for i in range(0, total, chunk_size):
        group = entries[i : i + chunk_size]
        c_kw: list[str] = []
        c_web: list[str] = []
        c_soc: dict[str, list[str]] = {}
        for e in group:
            if e[0] == "keyword":
                c_kw.append(e[1])
            elif e[0] == "website":
                c_web.append(e[1])
            else:
                _, plat, h = e
                c_soc.setdefault(plat, []).append(h)
        chunks.append(Targets(keywords=c_kw, websites=c_web, social=c_soc))
    return chunks
