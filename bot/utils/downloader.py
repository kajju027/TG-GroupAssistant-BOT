from __future__ import annotations
import os
import shutil
import tempfile
import urllib.parse
import aiofiles
import aiohttp
from bot.core.config import API_BASE_URL, HOST_MAP, MAX_DL_MB
_TIMEOUT = aiohttp.ClientTimeout(total=150, connect=20, sock_read=120)
_HEADERS = {'User-Agent': 'TGGroupAssistantBot/2.0'}
_MAX_BYTES = MAX_DL_MB * 1024 * 1024

async def call_api(endpoint: str, params: dict[str, str]) -> dict | None:
    if not API_BASE_URL:
        return None
    url = f'{API_BASE_URL}{endpoint}'
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT, headers=_HEADERS) as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                payload = await response.json(content_type=None)
                return payload if isinstance(payload, dict) else None
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return None

def extract_url(data: dict) -> str | None:
    for key in ('url', 'audio_url', 'video_url', 'download_url', 'link', 'file_url', 'src'):
        value = data.get(key)
        if isinstance(value, str) and value.startswith(('https://', 'http://')):
            return value
    nested = data.get('data')
    if isinstance(nested, dict):
        return extract_url(nested)
    media_items = data.get('medias') or data.get('media') or []
    if isinstance(media_items, list) and media_items and isinstance(media_items[0], dict):
        for key in ('url', 'link', 'src'):
            value = media_items[0].get(key)
            if isinstance(value, str) and value.startswith(('https://', 'http://')):
                return value
    return None

def extract_meta(data: dict) -> dict:
    flat = data.get('data', data) if isinstance(data.get('data'), dict) else data
    return {'title': flat.get('title') or flat.get('name') or '', 'duration': flat.get('duration') or flat.get('duration_seconds'), 'thumbnail': flat.get('thumbnail') or flat.get('thumb') or flat.get('cover'), 'quality': flat.get('quality') or flat.get('format') or ''}

async def fetch_file(url: str, suffix: str='.mp4') -> tuple[str | None, int]:
    temp_dir = tempfile.mkdtemp(prefix='tg_group_assistant_')
    destination = os.path.join(temp_dir, f'media{suffix}')
    size = 0
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT, headers=_HEADERS) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status != 200:
                    raise aiohttp.ClientResponseError(response.request_info, response.history, status=response.status)
                content_length = response.content_length
                if content_length is not None and content_length > _MAX_BYTES:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return (None, -1)
                async with aiofiles.open(destination, 'wb') as file:
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        await file.write(chunk)
                        size += len(chunk)
                        if size > _MAX_BYTES:
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return (None, -1)
        if size < 512:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return (None, 0)
        return (destination, size)
    except (aiohttp.ClientError, OSError, TimeoutError):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return (None, 0)

def detect_provider(text: str) -> tuple[str | None, str | None]:
    for word in text.split():
        if not word.startswith(('http://', 'https://')):
            continue
        try:
            parsed = urllib.parse.urlparse(word)
            host = (parsed.hostname or '').casefold().removeprefix('www.')
            if host in HOST_MAP:
                return (HOST_MAP[host], word)
            for domain, provider in HOST_MAP.items():
                normalized = domain.removeprefix('www.')
                if host.endswith('.' + normalized):
                    return (provider, word)
        except ValueError:
            continue
    return (None, None)

def guess_suffix(url: str, title: str='') -> str:
    lower = (url + title).casefold()
    if any((item in lower for item in ('.mp3', 'audio', '/play', 'music', 'song'))):
        return '.mp3'
    if any((item in lower for item in ('.mp4', 'video', '/video'))):
        return '.mp4'
    return '.mp4'
