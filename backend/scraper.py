import httpx
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Tuple
import re


MAX_PAGES = 30
REQUEST_TIMEOUT = 15
MAX_CONTENT_LENGTH = 3000  # chars per page


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    # Remove fragment and trailing slash
    normalized = parsed._replace(fragment="").geturl()
    return normalized.rstrip("/")


def is_same_domain(base_url: str, url: str) -> bool:
    base_domain = urlparse(base_url).netloc.lower()
    url_domain = urlparse(url).netloc.lower()
    # Allow www variants
    base_domain = base_domain.removeprefix("www.")
    url_domain = url_domain.removeprefix("www.")
    return base_domain == url_domain


def extract_text(html: str) -> Tuple[str, str]:
    """Returns (title, clean_text)"""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "noscript", "iframe", "svg", "form", "button",
                     "[aria-hidden]"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""

    # Focus on main content areas if present
    main = (
        soup.find("main") or
        soup.find(id=re.compile(r"main|content|body", re.I)) or
        soup.find(class_=re.compile(r"main|content|body", re.I)) or
        soup.body or
        soup
    )

    lines = []
    for element in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "span", "div"]):
        # Only direct text, skip nested divs content re-processing
        text = element.get_text(separator=" ", strip=True)
        if len(text) > 20:
            lines.append(text)

    # Deduplicate while preserving order
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    full_text = "\n".join(unique_lines)
    return title, full_text[:MAX_CONTENT_LENGTH]


def extract_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        full_url = urljoin(base_url, href)
        full_url = normalize_url(full_url)
        if is_same_domain(base_url, full_url):
            links.append(full_url)
    return links


async def scrape_website(base_url: str) -> List[dict]:
    """
    Crawl website starting from base_url.
    Returns list of {url, title, content} dicts.
    """
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    visited = set()
    to_visit = [normalize_url(base_url)]
    results = []

    headers = {
        "User-Agent": "HotelAI-Bot/1.0 (hotel AI assistant crawler)",
        "Accept": "text/html,application/xhtml+xml",
    }

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers=headers,
    ) as client:
        while to_visit and len(visited) < MAX_PAGES:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                response = await client.get(url)
                if response.status_code != 200:
                    continue
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue

                html = response.text
                title, text = extract_text(html)

                if text.strip():
                    results.append({
                        "url": url,
                        "title": title,
                        "content": text,
                    })

                # Discover new links
                new_links = extract_links(html, url)
                for link in new_links:
                    if link not in visited and link not in to_visit:
                        to_visit.append(link)

                # Small delay to be polite
                await asyncio.sleep(0.3)

            except Exception:
                # Skip unreachable pages silently
                continue

    return results
