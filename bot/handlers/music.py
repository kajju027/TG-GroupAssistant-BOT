import asyncio
import aiohttp
import aiofiles
import tempfile
import os
from pathlib import Path
from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, URLInputFile
from bot.core import database as db
from bot.core.config import API_BASE_URL
from bot.utils.filters import AllowedFilter
from bot.utils.ui import sc, box, row, sep, bold, mono

router = Router()

_TIMEOUT = aiohttp.ClientTimeout(total=120, connect=15, sock_read=90)
_HEADERS = {"User-Agent": "TGGroupAssistantBot/1.0"}


async def _call_api(endpoint: str, params: dict) -> dict | None:
    url = f"{API_BASE_URL}{endpoint}"
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT, headers=_HEADERS) as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return None
                return await resp.json(content_type=None)
    except Exception:
        return None


async def _download_file(url: str, dest: str) -> bool:
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return False
                async with aiofiles.open(dest, "wb") as f:
                    async for chunk in resp.content.iter_chunked(65536):
                        await f.write(chunk)
        return True
    except Exception:
        return False


@router.message(Command("play"), AllowedFilter())
async def play_music(message: Message, bot: Bot):
    db.inc_stat("commands")
    args = message.text.split(None, 1)
    if len(args) < 2:
        await message.reply(
            box("Music", [
                row("Usage",   "/play &lt;song name or URL&gt;",   "🎵"),
                row("Example", "/play Arijit Singh tum hi ho",      "🎧"),
                row("YouTube", "/play https://youtu.be/...",         "▶️"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return

    query = args[1].strip()
    status = await message.reply(
        box("Music", [
            f"  🔍 {sc('Searching for')} — {bold(query[:40])}",
            f"  ⏳ {sc('Please wait...')}",
        ]),
        parse_mode=ParseMode.HTML,
    )

    data = await _call_api("/play", {"query": query})

    if not data:
        await status.edit_text(
            box("Music Error", [
                f"  ❌ {sc('Could not fetch audio')}",
                sep(),
                f"  {sc('Try a different search query')}",
            ]),
            parse_mode=ParseMode.HTML,
        )
        return

    url = data.get("url") or data.get("audio_url") or data.get("download_url") or data.get("link")
    title = data.get("title") or data.get("name") or query
    duration = data.get("duration") or data.get("duration_seconds")
    thumbnail = data.get("thumbnail") or data.get("thumb")

    if not url:
        await status.edit_text(
            box("Music Error", [
                f"  ❌ {sc('No audio URL in API response')}",
                f"  {mono(str(list(data.keys())[:5]))}",
            ]),
            parse_mode=ParseMode.HTML,
        )
        return

    await status.edit_text(
        box("Music", [
            row("Title",    bold(title[:50]),                           "🎵"),
            row("Duration", f"{duration}s" if duration else sc("N/A"), "⏱️"),
            sep(),
            f"  ⬇️ {sc('Downloading...')}",
        ]),
        parse_mode=ParseMode.HTML,
    )

    db.inc_stat("music")

    with tempfile.TemporaryDirectory() as tmpdir:
        dest = os.path.join(tmpdir, "audio.mp3")
        ok = await _download_file(url, dest)
        if not ok or not os.path.exists(dest) or os.path.getsize(dest) < 1000:
            await status.edit_text(
                box("Music Error", [
                    f"  ❌ {sc('Download failed')}",
                    sep(),
                    f"  {sc('Sending link instead')}",
                    f"  <a href='{url}'>{bold(title[:40])}</a>",
                ]),
                parse_mode=ParseMode.HTML,
            )
            return

        file_size_mb = os.path.getsize(dest) / (1024 * 1024)
        if file_size_mb > 50:
            await status.edit_text(
                box("Music", [
                    row("Title", bold(title[:50]), "🎵"),
                    sep(),
                    f"  ⚠️ {sc('File too large to upload ({:.1f}MB)').format(file_size_mb)}",
                    f"  <a href='{url}'>🔗 {sc('Direct Download Link')}</a>",
                ]),
                parse_mode=ParseMode.HTML,
            )
            return

        await status.edit_text(
            box("Music", [
                row("Title", bold(title[:50]), "🎵"),
                sep(),
                f"  📤 {sc('Uploading...')}",
            ]),
            parse_mode=ParseMode.HTML,
        )

        try:
            audio_file = FSInputFile(dest, filename=f"{title[:40]}.mp3")
            await message.answer_audio(
                audio=audio_file,
                title=title[:64],
                caption=box("Now Playing", [
                    row("Track",    bold(title[:50]),               "🎵"),
                    row("Duration", f"{duration}s" if duration else sc("N/A"), "⏱️"),
                ]),
                parse_mode=ParseMode.HTML,
            )
            await status.delete()
        except Exception as e:
            await status.edit_text(
                box("Music Error", [f"  ❌ {mono(str(e)[:100])}"]),
                parse_mode=ParseMode.HTML,
            )
