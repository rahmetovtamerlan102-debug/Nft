"""
Парсер публичных страниц NFT-подарков Telegram вида:
https://t.me/nft/HomemadeCake-59562

Telegram отдаёт для таких ссылок серверный HTML с og:title / og:description,
где обычно перечислены модель, фон, узор (со знаками %) и иногда владелец.
Если реальная разметка окажется другой — правь регулярки в extract_fields().
"""

import re
import requests
from dataclasses import dataclass
from typing import Optional


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
    pattern: Optional[str] = None
    pattern_pct: Optional[str] = None
    owner: Optional[str] = None
    raw_description: Optional[str] = None


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    # Разрешаем ввод и как ссылку, и как "Название-Номер", и как "Название Номер"
    if raw.startswith("http"):
        return raw
    raw = raw.replace(" ", "-").replace("#", "")
    return f"https://t.me/nft/{raw}"


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.text


def _extract_meta(html: str, prop: str) -> Optional[str]:
    # ищем как og:title / og:description, так и twitter:*
    pattern = rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']*)["\']'
    m = re.search(pattern, html, re.IGNORECASE)
    return m.group(1) if m else None


def extract_fields(html: str, url: str) -> NftInfo:
    title = _extract_meta(html, "og:title")
    description = _extract_meta(html, "og:description")

    info = NftInfo(url=url, title=title, raw_description=description)

    if not description:
        return info

    # Примеры строк внутри description (по образцу скриншота):
    # "Модель: Sponge Cake (1.5%), Фон: Carrot Juice (2.0%), Узор: Sunflower (0.3%)"
    # Регулярки написаны с расчётом на варианты с ":" и без, скобками и без.
    def find(field_name: str):
        pat = rf'{field_name}[:\s]+([A-Za-zА-Яа-яЁё \'\-]+?)\s*[\(\s]([\d.,]+)\s*%'
        m = re.search(pat, description)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None, None

    info.model, info.model_pct = find("Модель")
    info.backdrop, info.backdrop_pct = find("Фон")
    info.pattern, info.pattern_pct = find("Узор")

    owner_match = re.search(r'(?:владел[а-я]*|owner)[:\s]+([A-Za-z0-9_ ]+)', description, re.IGNORECASE)
    if owner_match:
        info.owner = owner_match.group(1).strip()

    return info


def get_nft_info(user_input: str) -> NftInfo:
    url = normalize_url(user_input)
    html = fetch_html(url)
    return extract_fields(html, url)
