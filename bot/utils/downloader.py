import aiohttp
import aiofiles
import tempfile
import os
import urllib.parse
from bot.core.config import API_BASE_URL, MAX_DL_MB, HOST_MAP

_TIMEOUT = aiohttp.ClientTimeout(total=150, connect=20, sock_read=120)
_HEADERS = {"User-Agent": "TGGroupAssistantBot/2.0"}
_MAX_BYTES = MAX_DL_MB * 1024 * 1024


async def call_api(endpoint: str, params: dict) -> dict | None:
    url = f"{API_BASE_URL}{endpoint}"
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT, headers=_HEADERS) as s:
            async with s.get(url, params=params) as r:
                if r.status != 200:
                    return None
                return await r.json(content_type=None)
    except Exception:
        return None


def extract_url(data: dict) -> str | None:
    for k in ("url", "audio_url", "video_url", "download_url", "link", "file_url", "src"):
        v = data.get(k)
        if v and isinstance(v, str) and v.startswith("http"):
            return v
    if isinstance(data.get("data"), dict):
        return extract_url(data["data"])
    medias = data.get("medias") or data.get("media") or []
    if medias and isinstance(medias, list):
        first = medias[0]
        if isinstance(first, dict):
            for k in ("url", "link", "src"):
                v = first.get(k)
                if v and isinstance(v, str):
                    return v
    return None


def extract_meta(data: dict) -> dict:
    flat = data.get("data", data) if isinstance(data.get("data"), dict) else data
    return {
        "title":     flat.get("title") or flat.get("name") or "",
        "duration":  flat.get("duration") or flat.get("duration_seconds"),
        "thumbnail": flat.get("thumbnail") or flat.get("thumb") or flat.get("cover"),
        "quality":   flat.get("quality") or flat.get("format") or "",
    }


async def fetch_file(url: str, suffix: str = ".mp4") -> tuple[str | None, int]:
    tmpdir = tempfile.mkdtemp()
    dest = os.path.join(tmpdir, f"media{suffix}")
    size = 0
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return None, 0
                async with aiofiles.open(dest, "wb") as f:
                    async for chunk in r.content.iter_chunked(65536):
                        await f.write(chunk)
                        size += len(chunk)
                        if size > _MAX_BYTES:
                            return None, -1
        if size < 512:
            return None, 0
        return dest, size
    except Exception:
        return None, 0


def detect_provider(text: str) -> tuple[str | None, str | None]:
    for word in text.split():
        if not word.startswith(("http://", "https://")):
            continue
        try:
            host = urllib.parse.urlparse(word).netloc.lower()
            host = host.lstrip("www.")
            if host in HOST_MAP:
                return HOST_MAP[host], word
            for domain, prov in HOST_MAP.items():
                if host.endswith("." + domain):
                    return prov, word
        except Exception:
            continue
    return None, None


def guess_suffix(url: str, title: str = "") -> str:
    lower = (url + title).lower()
    if any(x in lower for x in (".mp3", "audio", "/play", "music", "song")):
        return ".mp3"
    if any(x in lower for x in (".mp4", "video", "/video")):
        return ".mp4"
    return ".mp4"
