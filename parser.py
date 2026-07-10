"""
Парсер публичных страниц NFT-подарков Telegram вида:
https://t.me/nft/HomemadeCake-59562

Реальная структура страницы (проверено на живом примере):
- есть таблица со строками: Owner, Model, Backdrop, Symbol, Quantity
- в значениях модель/фон/узор указаны как "Название 1.5%" (проценты)
- Owner содержит аватар + имя владельца
- Quantity вида "180 005/199 482 issued"
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


@dataclass
class NftInfo:
    url: str
    title: Optional[str] = None
    model: Optional[str] = None
    model_pct: Optional[str] = None
    backdrop: Optional[str] = None
    backdrop_pct: Optional[str] = None
    symbol: Optional[str] = None
    symbol_pct: Optional[str] = None
    owner: Optional[str] = None
    quantity: Optional[str] = None
    image_url: Optional[str] = None


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("http"):
        return raw
    raw = raw.replace(" ", "-").replace("#", "")
    return f"https://t.me/nft/{raw}"


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.text


def _split_name_pct(text: str):
    """
    Разбивает строку вида "Sponge Cake 1.5%" или "Carrot Juice 2%"
    на (название, процент).
    """
    text = text.strip()
    m = re.search(r'([\d.,]+)\s*%\s*$', text)
    if not m:
        return text, None
    pct = m.group(1)
    name = text[: m.start()].strip()
    return name, pct


def extract_fields(html: str, url: str) -> NftInfo:
    soup = BeautifulSoup(html, "html.parser")

    info = NftInfo(url=url)

    title_tag = soup.find("meta", attrs={"property": "og:title"})
    if title_tag:
        info.title = title_tag.get("content")

    image_tag = soup.find("meta", attrs={"property": "og:image"})
    if image_tag:
        info.image_url = image_tag.get("content")

    table = soup.find("table")
    if not table:
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
        elif "model" in label or "модель" in label:
            info.model, info.model_pct = _split_name_pct(value_text)
        elif "backdrop" in label or "фон" in label:
            info.backdrop, info.backdrop_pct = _split_name_pct(value_text)
        elif "symbol" in label or "узор" in label:
            info.symbol, info.symbol_pct = _split_name_pct(value_text)
        elif "quantity" in label or "количество" in label:
            info.quantity = value_text

    return info


def get_nft_info(user_input: str) -> NftInfo:
    url = normalize_url(user_input)
    html = fetch_html(url)
    return extract_fields(html, url)
