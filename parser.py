"""
Парсер публичных страниц NFT-подарков Telegram вида:
https://t.me/nft/HomemadeCake-59562
"""

import re
import requests
from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

NOT_FOUND_MARKERS = (
    "a new era of messaging",
    "telegram messenger",
)


@dataclass
class NftInfo:
    url: str
    not_found: bool = False
    title: Optional[str] = None
    model: Optional[str] = None
    model_pct: Optional[str] = None
    backdrop: Optional[str] = None
    backdrop_pct: Optional[str] = None
    symbol: Optional[str] = None
    symbol_pct: Optional[str] = None
    owner: Optional[str] = None
    owner_username: Optional[str] = None
    quantity: Optional[str] = None
    image_url: Optional[str] = None


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("http"):
        return raw
    raw = raw.replace(" ", "-").replace("#", "")
    return f"https://t.me/nft/{raw}"


def extract_slug(url: str) -> str:
    m = re.search(r't\.me/nft/([A-Za-z0-9_\-]+)', url)
    return m.group(1) if m else url


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _split_name_pct(text: str):
    text = text.strip()
    m = re.search(r'([\d.,]+)\s*%\s*$', text)
    if not m:
        return text, None
    pct = m.group(1)
    name = text[: m.start()].strip()
    return name, pct


def _extract_username_from_href(href: str) -> Optional[str]:
    if not href:
        return None
    m = re.search(r't\.me/([A-Za-z0-9_]{4,})', href)
    if m:
        candidate = m.group(1)
        # исключаем служебные пути типа t.me/nft/...
        if candidate.lower() not in ("nft", "share", "addstickers", "joinchat"):
            return candidate
    return None


def extract_fields(html: str, url: str) -> NftInfo:
    soup = BeautifulSoup(html, "html.parser")
    info = NftInfo(url=url)

    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True).lower() if title_tag else ""

    og_title_tag = soup.find("meta", attrs={"property": "og:title"})
    og_title = (og_title_tag.get("content") or "").lower() if og_title_tag else ""

    if any(marker in page_title for marker in NOT_FOUND_MARKERS) or any(
        marker in og_title for marker in NOT_FOUND_MARKERS
    ):
        info.not_found = True
        return info

    if og_title_tag:
        info.title = og_title_tag.get("content")

    image_tag = soup.find("meta", attrs={"property": "og:image"})
    if image_tag:
        info.image_url = image_tag.get("content")

    table = soup.find("table")
    if not table:
        info.not_found = True
        return info

    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) < 2:
            continue

        label = cells[0].get_text(strip=True).lower()
        value_cell = cells[1]
        value_text = value_cell.get_text(" ", strip=True)

        if "owner" in label or "владел" in label:
            info.owner = value_text
            link = value_cell.find("a")
            if link:
                info.owner_username = _extract_username_from_href(link.get("href", ""))
        elif "model" in label or "модель" in label:
            info.model, info.model_pct = _split_name_pct(value_text)
        elif "backdrop" in label or "фон" in label:
            info.backdrop, info.backdrop_pct = _split_name_pct(value_text)
        elif "symbol" in label or "узор" in label:
            info.symbol, info.symbol_pct = _split_name_pct(value_text)
        elif "quantity" in label or "количество" in label:
            info.quantity = value_text

    if not any([info.model, info.backdrop, info.symbol, info.owner]):
        info.not_found = True

    return info


def get_nft_info(user_input: str) -> NftInfo:
    url = normalize_url(user_input)
    html = fetch_html(url)
    return extract_fields(html, url)
