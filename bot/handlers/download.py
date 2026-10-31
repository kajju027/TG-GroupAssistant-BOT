from __future__ import annotations

import os
import secrets
import shutil
import time

from dataclasses import dataclass
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.core import database as db
from bot.core.config import MAX_DL_MB, OWNER_ID, PROVIDERS
from bot.utils import downloader as dl
from bot.utils.filters import AllowedFilter
from bot.utils.ui import bold, box, btn, italic, kb, mono, quote, row, sc

router = Router()

_PRIVATE = F.chat.type == 'private'
_CALLBACK_TTL_SECONDS = 10 * 60


@dataclass(frozen=True)
class _PendingDownload:
    owner_id: int
    expires_at: float
    provider: str
    payload: str


_pending_downloads: dict[str, _PendingDownload] = {}


DL_HELP = box('Downloader ⬇️', [
    f"🎧 <b>/play</b> {sc('song or YouTube link')}",
    f"🎬 <b>/video</b> {sc('video title or link')}",
    f"𝕏 <b>/tw</b> {sc('tweet link')}",
    f"📸 <b>/ig</b> {sc('instagram link')}",
    f"📘 <b>/fb</b> {sc('facebook link')}",
    f"📦 <b>/tb</b> {sc('terabox link')}",
    f"📌 <b>/pinterest</b> {sc('pin link')}",
    '',
    quote(sc('Paste any supported link right here — the platform is detected automatically.')),
])


def _prov(key: str) -> dict:
    return PROVIDERS[key]


def _create_pending(owner_id: int, provider: str, payload: str) -> str:
    now = time.monotonic()
    expired = [key for key, item in _pending_downloads.items() if item.expires_at <= now]
    for key in expired:
        _pending_downloads.pop(key, None)
    token = secrets.token_urlsafe(8)
    _pending_downloads[token] = _PendingDownload(owner_id=owner_id, expires_at=now + _CALLBACK_TTL_SECONDS, provider=provider, payload=payload)
    return token


def _take_pending(token: str, user_id: int) -> _PendingDownload | None:
    item = _pending_downloads.pop(token, None)
    if item is None or item.expires_at <= time.monotonic() or item.owner_id != user_id:
        return None
    return item


def _yt_kb(query: str, owner_id: int):
    audio = _create_pending(owner_id, 'youtube_audio', query)
    video = _create_pending(owner_id, 'youtube_video', query)
    return kb(
        [btn('🎧 Audio', f'dl:a:{audio}'), btn('🎬 Video', f'dl:v:{video}')],
        [btn('❌ Cancel', 'dl_cancel')],
    )


def _provider_kb(provider: str, url: str, owner_id: int):
    token = _create_pending(owner_id, provider, url)
    label = {
        'twitter': '𝕏 Download', 'instagram': '📸 Download', 'facebook': '📘 Download',
        'terabox': '📦 Download', 'pinterest': '📌 Download',
    }.get(provider, '⬇️ Download')
    return kb([btn(label, f'dl:r:{token}')], [btn('❌ Cancel', 'dl_cancel')])


def _safe_html(value: object, limit: int = 60) -> str:
    text = str(value or '')
    if len(text) > limit:
        text = text[:limit] + '…'
    return escape(text)


def _safe_filename(value: object, suffix: str) -> str:
    raw = ''.join((char if char.isalnum() or char in ' ._-' else '_' for char in str(value)))
    stem = raw.strip(' ._')[:80] or 'media'
    return stem + suffix


def _safe_url(url: str) -> str:
    return escape(url, quote=True)


async def _run_download(target: Message, bot: Bot, provider_key: str, query_or_url: str, status_msg: Message | None = None):
    prov = _prov(provider_key)
    emoji = prov['emoji']
    label = prov['label']
    endpoint = prov['endpoint']
    param = prov['param']
    is_audio = provider_key == 'youtube_audio'

    async def _edit(text: str):
        if status_msg:
            try:
                await status_msg.edit_text(text, parse_mode=ParseMode.HTML)
            except Exception:
                pass

    await _edit(box(f'{emoji} {label}', [
        row('Query' if param == 'query' else 'URL', bold(_safe_html(query_or_url, 60))),
        f"  ⏳ {italic(sc('Fetching info...'))}",
    ]))
    data = await dl.call_api(endpoint, {param: query_or_url})
    if not data:
        await _edit(box(f'{emoji} {label}', [
            f"  ❌ {sc('The downloader service did not answer.')}",
            quote(sc('Try again later or use a different link.')),
        ]))
        return
    dl_url = dl.extract_url(data)
    meta = dl.extract_meta(data)
    title = str(meta['title'] or query_or_url[:50])
    dur = meta['duration']
    if not dl_url:
        await _edit(box(f'{emoji} {label}', [
            f"  ❌ {sc('No download URL in the response.')}",
            quote(sc('The media may be unavailable or region-locked.')),
        ]))
        return
    await _edit(box(f'{emoji} {label}', [
        row('Title', bold(_safe_html(title, 55))),
        row('Duration', bold(str(dur or '—'))),
        f"  ⬇️ {italic(sc('Downloading...'))}",
    ]))
    suffix = '.mp3' if is_audio else dl.guess_suffix(dl_url, title)
    path, size = await dl.fetch_file(dl_url, suffix)
    if size == -1:
        await _edit(box(f'{emoji} {label}', [
            f"  ⚠️ {sc(f'File exceeds the {MAX_DL_MB} MB limit')}",
            quote(sc('Sending the direct link instead.')),
            f"  <a href='{_safe_url(dl_url)}'>🔗 {bold(sc('Direct Download'))}</a>",
        ]))
        return
    if not path:
        await _edit(box(f'{emoji} {label}', [
            f"  ❌ {sc('Download failed')}",
            f"  <a href='{_safe_url(dl_url)}'>🔗 {bold(sc('Try manually'))}</a>",
        ]))
        return
    from bot.utils.ui import fmt_dur, fmt_size

    db.inc_stat('downloads')
    await _edit(box(f'{emoji} {label}', [
        row('Title', bold(_safe_html(title, 55))),
        row('Size', bold(fmt_size(size))),
        f"  📤 {italic(sc('Uploading...'))}",
    ]))
    caption = box(f'{emoji} {label}', [
        row('Title', bold(_safe_html(title, 55))),
        row('Duration', bold(fmt_dur(dur))),
        row('Size', bold(fmt_size(size))),
    ])
    try:
        f = FSInputFile(path, filename=_safe_filename(title, suffix))
        kwargs = dict(caption=caption, parse_mode=ParseMode.HTML)
        if is_audio:
            await target.answer_audio(audio=f, title=title[:64], **kwargs)
        elif suffix in ('.mp4', '.mkv', '.mov', '.webm'):
            await target.answer_video(video=f, **kwargs)
        else:
            await target.answer_document(document=f, **kwargs)
        if status_msg:
            await status_msg.delete()
    except Exception as e:
        await _edit(box(f'{emoji} Upload Failed ❌', [
            f'  {mono(str(e)[:120])}',
            f"  <a href='{_safe_url(dl_url)}'>🔗 {bold(sc('Direct link'))}</a>",
        ]))
    finally:
        try:
            parent = os.path.dirname(path)
            if os.path.isdir(parent):
                shutil.rmtree(parent, ignore_errors=True)
        except Exception:
            pass


async def _send_status(message: Message, label: str, query: str) -> Message:
    return await message.reply(box(label, [
        row('Query' if len(query) < 80 else 'URL', bold(_safe_html(query, 60))),
        f"  ⏳ {italic(sc('Please wait...'))}",
    ]))


# --------------------------------------------------------------- commands --
@router.message(Command('play', 'ytaudio'), AllowedFilter())
async def cmd_play(message: Message, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(DL_HELP)
        return
    query = parts[1].strip()
    status = await _send_status(message, 'YouTube Audio 🎧', query)
    await _run_download(message, bot, 'youtube_audio', query, status)


@router.message(Command('video', 'ytvideo', 'ytv'), AllowedFilter())
async def cmd_video(message: Message, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(DL_HELP)
        return
    query = parts[1].strip()
    status = await _send_status(message, 'YouTube Video 🎬', query)
    await _run_download(message, bot, 'youtube_video', query, status)


@router.message(Command('twitter', 'tw', 'x'), AllowedFilter())
async def cmd_twitter(message: Message, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(DL_HELP)
        return
    url = parts[1].strip()
    status = await _send_status(message, 'X / Twitter 𝕏', url)
    await _run_download(message, bot, 'twitter', url, status)


@router.message(Command('instagram', 'ig', 'insta'), AllowedFilter())
async def cmd_instagram(message: Message, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(DL_HELP)
        return
    url = parts[1].strip()
    status = await _send_status(message, 'Instagram 📸', url)
    await _run_download(message, bot, 'instagram', url, status)


@router.message(Command('facebook', 'fb'), AllowedFilter())
async def cmd_facebook(message: Message, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(DL_HELP)
        return
    url = parts[1].strip()
    status = await _send_status(message, 'Facebook 📘', url)
    await _run_download(message, bot, 'facebook', url, status)


@router.message(Command('terabox', 'tb', 'tera'), AllowedFilter())
async def cmd_terabox(message: Message, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(DL_HELP)
        return
    url = parts[1].strip()
    status = await _send_status(message, 'TeraBox 📦', url)
    await _run_download(message, bot, 'terabox', url, status)


@router.message(Command('pinterest', 'pt'), AllowedFilter())
async def cmd_pinterest(message: Message, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(DL_HELP)
        return
    url = parts[1].strip()
    status = await _send_status(message, 'Pinterest 📌', url)
    await _run_download(message, bot, 'pinterest', url, status)


@router.message(Command('dl', 'download'), AllowedFilter())
async def cmd_dl(message: Message, bot: Bot):
    db.inc_stat('commands')
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.reply(DL_HELP)
        return
    text = parts[1].strip()
    provider, url = dl.detect_provider(text)
    if not provider or not url:
        await message.reply(box('Unsupported Link ❌', [
            quote(sc('Could not detect the platform. Supported: YouTube, Twitter, Instagram, Facebook, TeraBox, Pinterest.')),
        ]))
        return
    if provider == 'youtube':
        await message.reply(box('YouTube ▶️', [quote(_safe_html(url, 80))]), reply_markup=_yt_kb(url, message.from_user.id))
        return
    p = _prov(provider) if provider in PROVIDERS else None
    label = f"{p['emoji']} {p['label']}" if p else provider.title()
    await message.reply(box(label, [quote(_safe_html(url, 80))]), reply_markup=_provider_kb(provider, url, message.from_user.id))


@router.message(_PRIVATE, AllowedFilter(), F.text.regexp('https?://'))
async def auto_detect_url(message: Message, bot: Bot):
    text = message.text or ''
    provider, url = dl.detect_provider(text)
    if not provider or not url:
        return
    if provider == 'youtube':
        await message.reply(box('YouTube ▶️', [quote(_safe_html(url, 80))]), reply_markup=_yt_kb(url, message.from_user.id))
        return
    p = _prov(provider) if provider in PROVIDERS else None
    label = f"{p['emoji']} {p['label']}" if p else provider.title()
    await message.reply(box(label, [quote(_safe_html(url, 80))]), reply_markup=_provider_kb(provider, url, message.from_user.id))


# -------------------------------------------------------------- callbacks --
async def _callback_download(callback: CallbackQuery, bot: Bot, expected_mode: str) -> None:
    if callback.from_user is None:
        await callback.answer('This download request is invalid.', show_alert=True)
        return
    if callback.from_user.id != OWNER_ID and not db.is_allowed(callback.from_user.id):
        await callback.answer('You do not have access to the downloader.', show_alert=True)
        return
    try:
        _, mode, token = callback.data.split(':')
    except (AttributeError, ValueError):
        await callback.answer('This download button is invalid.', show_alert=True)
        return
    if mode != expected_mode:
        await callback.answer('This download button is invalid.', show_alert=True)
        return
    pending = _take_pending(token, callback.from_user.id)
    if pending is None:
        await callback.answer('This button expired. Send the link again.', show_alert=True)
        return
    if mode == 'a' and pending.provider != 'youtube_audio':
        await callback.answer('This download button is invalid.', show_alert=True)
        return
    if mode == 'v' and pending.provider != 'youtube_video':
        await callback.answer('This download button is invalid.', show_alert=True)
        return
    if mode == 'r' and pending.provider not in PROVIDERS:
        await callback.answer('This download button is invalid.', show_alert=True)
        return
    if not isinstance(callback.message, Message):
        await callback.answer('The source message is unavailable.', show_alert=True)
        return
    await callback.answer('⬇️')
    prov = _prov(pending.provider)
    status = await callback.message.reply(box(f"{prov['emoji']} {prov['label']}", [
        row('Query' if prov['param'] == 'query' else 'URL', bold(_safe_html(pending.payload, 60))),
        f"  ⏳ {italic(sc('Starting...'))}",
    ]))
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _run_download(callback.message, bot, pending.provider, pending.payload, status)


@router.callback_query(lambda query: query.data and query.data.startswith('dl:a:'))
async def cb_yt_audio(callback: CallbackQuery, bot: Bot):
    await _callback_download(callback, bot, 'a')


@router.callback_query(lambda query: query.data and query.data.startswith('dl:v:'))
async def cb_yt_video(callback: CallbackQuery, bot: Bot):
    await _callback_download(callback, bot, 'v')


@router.callback_query(lambda query: query.data and query.data.startswith('dl:r:'))
async def cb_dl_run(callback: CallbackQuery, bot: Bot):
    await _callback_download(callback, bot, 'r')


@router.callback_query(lambda query: query.data == 'dl_cancel')
async def cb_cancel(callback: CallbackQuery):
    await callback.answer('Cancelled.')
    if isinstance(callback.message, Message):
        try:
            await callback.message.delete()
        except Exception:
            pass
