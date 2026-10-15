import os
import shutil
from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from bot.core import database as db
from bot.core.config import PROVIDERS, HOST_MAP, FIRE_FX, CONFETTI_FX, MAX_DL_MB
from bot.utils.filters import AllowedFilter
from bot.utils.ui import sc, box, row, sep, bold, mono, italic, link, quote, fmt_size, fmt_dur, kb, btn, ubtn
from bot.utils import downloader as dl

router = Router()

_PRIVATE = F.chat.type == "private"


def _prov(key: str) -> dict:
    return PROVIDERS[key]


def _dl_box(title: str, lines: list[str]) -> str:
    return box(title, lines)


def _yt_kb(query: str) -> object:
    q = query[:200]
    return kb(
        [btn("🎧 Audio", f"yt_audio|{q}"), btn("🎬 Video", f"yt_video|{q}")],
        [btn("❌ Cancel", "dl_cancel")],
    )


def _provider_kb(provider: str, url: str) -> object:
    safe_url = url[:500]
    if provider == "youtube":
        return kb(
            [btn("🎧 YouTube Audio", f"yt_audio|{safe_url}"),
             btn("🎬 YouTube Video", f"yt_video|{safe_url}")],
            [btn("❌ Cancel", "dl_cancel")],
        )
    mapping = {
        "twitter":   ("𝕏  Download", f"dl_run|twitter|{safe_url}"),
        "instagram": ("📸 Download", f"dl_run|instagram|{safe_url}"),
        "facebook":  ("📘 Download", f"dl_run|facebook|{safe_url}"),
        "terabox":   ("📦 Download", f"dl_run|terabox|{safe_url}"),
        "pinterest": ("📌 Download", f"dl_run|pinterest|{safe_url}"),
    }
    label, data = mapping.get(provider, ("⬇️ Download", f"dl_run|{provider}|{safe_url}"))
    return kb([btn(label, data)], [btn("❌ Cancel", "dl_cancel")])


async def _run_download(
    target: Message,
    bot: Bot,
    provider_key: str,
    query_or_url: str,
    status_msg: Message | None = None,
):
    prov      = _prov(provider_key)
    emoji     = prov["emoji"]
    label     = prov["label"]
    endpoint  = prov["endpoint"]
    param     = prov["param"]
    is_audio  = provider_key == "youtube_audio"

    async def _edit(text: str):
        if status_msg:
            try:
                await status_msg.edit_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass

    await _edit(
        _dl_box(f"{emoji} {label}", [
            row("Query" if param == "query" else "URL",
                bold(query_or_url[:60] + ("…" if len(query_or_url) > 60 else "")), "🔍"),
            sep(),
            f"  ⏳ {italic(sc('Fetching info...'))}",
        ])
    )

    data = await dl.call_api(endpoint, {param: query_or_url})

    if not data:
        await _edit(
            _dl_box(f"{emoji} {label} — ❌", [
                f"  ❌ {sc('API returned no data')}",
                sep(),
                quote(sc("Try a different query or URL.")),
            ])
        )
        return

    dl_url = dl.extract_url(data)
    meta   = dl.extract_meta(data)
    title  = meta["title"] or query_or_url[:50]
    dur    = meta["duration"]
    size_h = ""

    if not dl_url:
        await _edit(
            _dl_box(f"{emoji} {label} — ❌", [
                f"  ❌ {sc('No download URL in response')}",
                sep(),
                quote(sc("The media may be unavailable or region-locked.")),
            ])
        )
        return

    await _edit(
        _dl_box(f"{emoji} {label}", [
            row("Title",    bold(title[:55] + ("…" if len(title) > 55 else "")), "🎵" if is_audio else "🎬"),
            row("Duration", bold(fmt_dur(dur)),                                  "⏱️"),
            sep(),
            f"  ⬇️ {italic(sc('Downloading...'))}",
        ])
    )

    suffix = ".mp3" if is_audio else dl.guess_suffix(dl_url, title)
    path, size = await dl.fetch_file(dl_url, suffix)

    if size == -1:
        await _edit(
            _dl_box(f"{emoji} {label} — ⚠️", [
                f"  ⚠️ {sc(f'File exceeds {MAX_DL_MB} MB limit')}",
                sep(),
                quote(sc("Sending direct link instead.")),
                f"  <a href='{dl_url}'>🔗 {bold(sc('Direct Download'))}</a>",
            ])
        )
        return

    if not path:
        await _edit(
            _dl_box(f"{emoji} {label} — ❌", [
                f"  ❌ {sc('Download failed')}",
                sep(),
                quote(sc("Could not fetch the file.")),
                f"  <a href='{dl_url}'>🔗 {bold(sc('Try manually'))}</a>",
            ])
        )
        return

    size_h = fmt_size(size)
    db.inc_stat("downloads")

    await _edit(
        _dl_box(f"{emoji} {label}", [
            row("Title",    bold(title[:55] + ("…" if len(title) > 55 else "")), "🎵" if is_audio else "🎬"),
            row("Size",     bold(size_h),                                         "💾"),
            sep(),
            f"  📤 {italic(sc('Uploading...'))}",
        ])
    )

    caption = _dl_box(
        f"{emoji} {sc(label)}",
        [
            row("Title",    bold(title[:55] + ("…" if len(title) > 55 else "")),  "🎵" if is_audio else "🎬"),
            row("Duration", bold(fmt_dur(dur)),                                    "⏱️"),
            row("Size",     bold(size_h),                                          "💾"),
            sep(),
            quote(sc("Downloaded via Group Assistant Bot")),
        ],
    )

    try:
        f      = FSInputFile(path, filename=f"{title[:40]}{suffix}")
        kwargs = dict(caption=caption, parse_mode=ParseMode.HTML)

        if is_audio:
            await target.answer_audio(audio=f, title=title[:64], **kwargs)
        elif suffix in (".mp4", ".mkv", ".mov", ".webm"):
            await target.answer_video(video=f, **kwargs)
        else:
            await target.answer_document(document=f, **kwargs)

        if status_msg:
            await status_msg.delete()

    except Exception as e:
        await _edit(
            _dl_box(f"{emoji} Upload Failed ❌", [
                f"  {mono(str(e)[:120])}",
                sep(),
                f"  <a href='{dl_url}'>🔗 {bold(sc('Direct link'))}</a>",
            ])
        )
    finally:
        try:
            parent = os.path.dirname(path)
            if os.path.isdir(parent):
                shutil.rmtree(parent, ignore_errors=True)
        except Exception:
            pass


async def _send_status(message: Message, label: str, query: str) -> Message:
    return await message.reply(
        _dl_box(label, [
            row("Query" if len(query) < 80 else "URL",
                bold(query[:60] + ("…" if len(query) > 60 else "")), "🔍"),
            sep(),
            f"  ⏳ {italic(sc('Please wait...'))}",
        ]),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command(commands=["play", "ytaudio", "music"]), AllowedFilter())
async def cmd_play(message: Message, bot: Bot):
    db.inc_stat("commands")
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            _dl_box("YouTube Audio 🎧", [
                row("Usage",   "/play &lt;song name or URL&gt;", "📖"),
                row("Example", "/play Arijit Singh tum hi ho",   "🎵"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return
    query  = parts[1].strip()
    status = await _send_status(message, "YouTube Audio 🎧", query)
    await _run_download(message, bot, "youtube_audio", query, status)


@router.message(Command(commands=["video", "ytvideo", "ytv"]), AllowedFilter())
async def cmd_video(message: Message, bot: Bot):
    db.inc_stat("commands")
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            _dl_box("YouTube Video 🎬", [
                row("Usage",   "/video &lt;title or URL&gt;", "📖"),
                row("Example", "/video Natu Natu song",       "🎬"),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return
    query  = parts[1].strip()
    status = await _send_status(message, "YouTube Video 🎬", query)
    await _run_download(message, bot, "youtube_video", query, status)


@router.message(Command(commands=["twitter", "tw", "x"]), AllowedFilter())
async def cmd_twitter(message: Message, bot: Bot):
    db.inc_stat("commands")
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            _dl_box("X / Twitter 𝕏", [row("Usage", "/tw &lt;tweet URL&gt;", "📖")]),
            parse_mode=ParseMode.HTML,
        )
        return
    url    = parts[1].strip()
    status = await _send_status(message, "X / Twitter 𝕏", url)
    await _run_download(message, bot, "twitter", url, status)


@router.message(Command(commands=["instagram", "ig", "insta"]), AllowedFilter())
async def cmd_instagram(message: Message, bot: Bot):
    db.inc_stat("commands")
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            _dl_box("Instagram 📸", [row("Usage", "/ig &lt;post/reel URL&gt;", "📖")]),
            parse_mode=ParseMode.HTML,
        )
        return
    url    = parts[1].strip()
    status = await _send_status(message, "Instagram 📸", url)
    await _run_download(message, bot, "instagram", url, status)


@router.message(Command(commands=["facebook", "fb"]), AllowedFilter())
async def cmd_facebook(message: Message, bot: Bot):
    db.inc_stat("commands")
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            _dl_box("Facebook 📘", [row("Usage", "/fb &lt;video URL&gt;", "📖")]),
            parse_mode=ParseMode.HTML,
        )
        return
    url    = parts[1].strip()
    status = await _send_status(message, "Facebook 📘", url)
    await _run_download(message, bot, "facebook", url, status)


@router.message(Command(commands=["terabox", "tb", "tera"]), AllowedFilter())
async def cmd_terabox(message: Message, bot: Bot):
    db.inc_stat("commands")
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            _dl_box("TeraBox 📦", [row("Usage", "/tb &lt;terabox URL&gt;", "📖")]),
            parse_mode=ParseMode.HTML,
        )
        return
    url    = parts[1].strip()
    status = await _send_status(message, "TeraBox 📦", url)
    await _run_download(message, bot, "terabox", url, status)


@router.message(Command(commands=["pinterest", "pin", "pt"]), AllowedFilter())
async def cmd_pinterest(message: Message, bot: Bot):
    db.inc_stat("commands")
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            _dl_box("Pinterest 📌", [row("Usage", "/pin &lt;pin URL&gt;", "📖")]),
            parse_mode=ParseMode.HTML,
        )
        return
    url    = parts[1].strip()
    status = await _send_status(message, "Pinterest 📌", url)
    await _run_download(message, bot, "pinterest", url, status)


@router.message(Command(commands=["dl", "download"]), AllowedFilter())
async def cmd_dl(message: Message, bot: Bot):
    db.inc_stat("commands")
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(
            _dl_box("Downloader ⬇️", [
                f"  {sc('Supported platforms:')}",
                sep(),
                row("YouTube",   "🎧 audio  /  🎬 video",  "▸"),
                row("X/Twitter", "𝕏  video / GIF",          "▸"),
                row("Instagram", "📸 post / reel / story",  "▸"),
                row("Facebook",  "📘 video",                "▸"),
                row("TeraBox",   "📦 file",                 "▸"),
                row("Pinterest", "📌 image / video",        "▸"),
                sep(),
                f"  💡 {italic(sc('Paste a URL to auto-detect'))}",
            ]),
            parse_mode=ParseMode.HTML,
        )
        return
    text     = parts[1].strip()
    provider, url = dl.detect_provider(text)
    if not provider or not url:
        await message.reply(
            _dl_box("Unsupported URL ❌", [
                f"  {sc('Could not detect platform from the URL.')}",
                sep(),
                quote(sc("Supported: YouTube, Twitter, Instagram, Facebook, TeraBox, Pinterest")),
            ]),
            parse_mode=ParseMode.HTML,
        )
        return
    if provider == "youtube":
        await message.reply(
            _dl_box("YouTube ▶️", [
                f"  {sc('Choose download format:')}", sep(),
                quote(url[:80] + ("…" if len(url) > 80 else "")),
            ]),
            parse_mode=ParseMode.HTML,
            reply_markup=_yt_kb(url),
        )
    else:
        prov_key = provider
        p        = _prov(prov_key) if prov_key in PROVIDERS else None
        label    = p["emoji"] + " " + p["label"] if p else sc(provider.title())
        await message.reply(
            _dl_box(label, [
                f"  {sc('Platform detected:')} {bold(sc(provider.title()))}",
                sep(),
                quote(url[:80] + ("…" if len(url) > 80 else "")),
            ]),
            parse_mode=ParseMode.HTML,
            reply_markup=_provider_kb(provider, url),
        )


@router.message(_PRIVATE, AllowedFilter(), F.text.regexp(r"https?://"))
async def auto_detect_url(message: Message, bot: Bot):
    text     = message.text or ""
    provider, url = dl.detect_provider(text)
    if not provider or not url:
        return

    if provider == "youtube":
        await message.reply(
            _dl_box("YouTube ▶️", [
                f"  {sc('YouTube link detected! Choose format:')}", sep(),
                quote(url[:80] + ("…" if len(url) > 80 else "")),
            ]),
            parse_mode=ParseMode.HTML,
            reply_markup=_yt_kb(url),
        )
    else:
        prov_key = provider
        p        = _prov(prov_key) if prov_key in PROVIDERS else None
        label    = p["emoji"] + " " + p["label"] if p else sc(provider.title())
        await message.reply(
            _dl_box(label, [
                f"  {sc('Link detected:')} {bold(sc(provider.title()))}",
                sep(),
                quote(url[:80] + ("…" if len(url) > 80 else "")),
            ]),
            parse_mode=ParseMode.HTML,
            reply_markup=_provider_kb(provider, url),
        )


@router.callback_query(lambda c: c.data and c.data.startswith("yt_audio|"))
async def cb_yt_audio(callback: CallbackQuery, bot: Bot):
    await callback.answer("🎧 Fetching audio...")
    query  = callback.data.split("|", 1)[1]
    status = await callback.message.reply(
        _dl_box("YouTube Audio 🎧", [
            row("Query", bold(query[:60] + ("…" if len(query) > 60 else "")), "🔍"),
            sep(),
            f"  ⏳ {italic(sc('Starting...'))}",
        ]),
        parse_mode=ParseMode.HTML,
    )
    await callback.message.delete()
    await _run_download(callback.message, bot, "youtube_audio", query, status)


@router.callback_query(lambda c: c.data and c.data.startswith("yt_video|"))
async def cb_yt_video(callback: CallbackQuery, bot: Bot):
    await callback.answer("🎬 Fetching video...")
    query  = callback.data.split("|", 1)[1]
    status = await callback.message.reply(
        _dl_box("YouTube Video 🎬", [
            row("Query", bold(query[:60] + ("…" if len(query) > 60 else "")), "🔍"),
            sep(),
            f"  ⏳ {italic(sc('Starting...'))}",
        ]),
        parse_mode=ParseMode.HTML,
    )
    await callback.message.delete()
    await _run_download(callback.message, bot, "youtube_video", query, status)


@router.callback_query(lambda c: c.data and c.data.startswith("dl_run|"))
async def cb_dl_run(callback: CallbackQuery, bot: Bot):
    await callback.answer("⬇️ Starting download...")
    _, provider_key, url = callback.data.split("|", 2)
    p      = _prov(provider_key) if provider_key in PROVIDERS else {}
    label  = p.get("emoji", "⬇️") + " " + p.get("label", sc(provider_key.title()))
    status = await callback.message.reply(
        _dl_box(label, [
            row("URL", bold(url[:60] + ("…" if len(url) > 60 else "")), "🔗"),
            sep(),
            f"  ⏳ {italic(sc('Starting...'))}",
        ]),
        parse_mode=ParseMode.HTML,
    )
    await callback.message.delete()
    await _run_download(callback.message, bot, provider_key, url, status)


@router.callback_query(lambda c: c.data == "dl_cancel")
async def cb_cancel(callback: CallbackQuery):
    await callback.answer("Cancelled.")
    try:
        await callback.message.delete()
    except Exception:
        pass
