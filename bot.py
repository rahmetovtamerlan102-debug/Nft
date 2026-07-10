import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, URLInputFile

from parser import get_nft_info

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "Не найден BOT_TOKEN. Задай переменную окружения BOT_TOKEN "
        "(в Render: Dashboard -> Service -> Environment)."
    )

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

NFT_LINK_RE = re.compile(r"(https?://)?t\.me/nft/[A-Za-z0-9_\-]+", re.IGNORECASE)


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привет! Пришли мне ссылку на NFT-подарок вида:\n"
        "https://t.me/nft/HomemadeCake-59562\n\n"
        "И я покажу модель, фон, узор, владельца и тираж."
    )


@dp.message(F.text.regexp(NFT_LINK_RE))
async def nft_link_handler(message: Message):
    match = NFT_LINK_RE.search(message.text)
    link = match.group(0)
    if not link.startswith("http"):
        link = "https://" + link

    status = await message.answer("Ищу информацию...")

    try:
        info = get_nft_info(link)
    except Exception as e:
        await status.edit_text(f"Не удалось получить данные: {e}")
        return

    if not any([info.model, info.backdrop, info.symbol, info.owner]):
        await status.edit_text(
            "Страница получена, но не удалось распознать поля. "
            "Формат мог измениться — сообщи мне, поправлю парсер."
        )
        return

    lines = [f"<b>{info.title or link}</b>", ""]

    if info.model:
        pct = f" <i>{info.model_pct}%</i>" if info.model_pct else ""
        lines.append(f"<b>Модель:</b> {info.model}{pct}")
    if info.backdrop:
        pct = f" <i>{info.backdrop_pct}%</i>" if info.backdrop_pct else ""
        lines.append(f"<b>Фон:</b> {info.backdrop}{pct}")
    if info.symbol:
        pct = f" <i>{info.symbol_pct}%</i>" if info.symbol_pct else ""
        lines.append(f"<b>Узор:</b> {info.symbol}{pct}")
    if info.quantity:
        lines.append(f"<b>Тираж:</b> {info.quantity}")
    if info.owner:
        lines.append("")
        lines.append(f"<b>Владелец:</b> {info.owner}")

    text = "\n".join(lines)

    try:
        if info.image_url:
            await status.delete()
            await message.answer_photo(
                photo=URLInputFile(info.image_url),
                caption=text,
                parse_mode="HTML",
            )
        else:
            await status.edit_text(text, parse_mode="HTML")
    except Exception:
        # если картинку не удалось отправить — отправляем просто текст
        await status.edit_text(text, parse_mode="HTML")


@dp.message()
async def fallback_handler(message: Message):
    await message.answer(
        "Пришли ссылку вида https://t.me/nft/HomemadeCake-59562, "
        "чтобы я показал информацию о подарке."
    )


async def run_dummy_webserver():
    from aiohttp import web

    async def health(request):
        return web.Response(text="Bot is running")

    app = web.Application()
    app.router.add_get("/", health)

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    await asyncio.gather(
        run_dummy_webserver(),
        dp.start_polling(bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
