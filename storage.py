"""
Простое локальное хранилище статистики по NFT:
- сколько раз запрашивали конкретный подарок ("интересовались")
- история смены владельца, которую бот отследил сам

Хранится в SQLite-файле nft_stats.db рядом со скриптом.
ВАЖНО: на бесплатном плане Render диск не постоянный — при каждом
передеплое/перезапуске файл базы обнуляется. Для настоящей истории
на проде нужен постоянный диск (платный Render Disk) или внешняя БД.
"""

import sqlite3
from datetime import datetime, timezone
from typing import List, Tuple

DB_PATH = "nft_stats.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS views (
            slug TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ownership_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL,
            owner TEXT NOT NULL,
            changed_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def register_view(slug: str) -> int:
    """Увеличивает счётчик интереса к подарку и возвращает новое значение."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count FROM views WHERE slug = ?", (slug,))
    row = cur.fetchone()
    if row:
        new_count = row[0] + 1
        cur.execute("UPDATE views SET count = ? WHERE slug = ?", (new_count, slug))
    else:
        new_count = 1
        cur.execute("INSERT INTO views (slug, count) VALUES (?, ?)", (slug, new_count))
    conn.commit()
    conn.close()
    return new_count


def register_owner_if_changed(slug: str, owner: str) -> None:
    """Если владелец отличается от последнего сохранённого — добавляет запись в историю."""
    if not owner:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT owner FROM ownership_history WHERE slug = ? ORDER BY id DESC LIMIT 1",
        (slug,),
    )
    row = cur.fetchone()
    last_owner = row[0] if row else None

    if last_owner != owner:
        now = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
        cur.execute(
            "INSERT INTO ownership_history (slug, owner, changed_at) VALUES (?, ?, ?)",
            (slug, owner, now),
        )
        conn.commit()
    conn.close()


def get_ownership_history(slug: str) -> List[Tuple[str, str]]:
    """Возвращает список (владелец, дата) от старых к новым."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT owner, changed_at FROM ownership_history WHERE slug = ? ORDER BY id ASC",
        (slug,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_view_count(slug: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count FROM views WHERE slug = ?", (slug,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0
