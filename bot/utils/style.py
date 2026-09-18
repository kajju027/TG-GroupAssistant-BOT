"""
bot/utils/style.py — Small-caps reply styling (Levanter/Raganork look).

Converts normal outgoing text into "small caps" Unicode letters
(ᴀʙᴄ) while keeping each word's FIRST letter as a normal English
capital, e.g. "Bot" -> "Bᴏᴛ", "hello world" -> "Hᴇʟʟᴏ Wᴏʀʟᴅ".

Exceptions (kept as normal, un-styled text):
  • URLs (http://, https://, t.me/, telegram.me/)
  • /commands (literal command names like /warn, /settings)
  • Anything inside an HTML tag's attributes (<a href="...">) or inside
    <code>...</code> (used throughout the bot to show literal settings
    values, variable placeholders like {name}, usage strings, etc.)
  • HTML tags themselves (<b>, </b>, <i>, <a href='...'>, etc.)
  • Emoji / non-letter characters are left untouched automatically,
    since the mapping table only touches ASCII letters.

This is applied automatically to every outgoing message (see
bot/utils/style.py:patch_outgoing_messages, called once from
bot/main.py) so individual handlers do NOT need to call this manually.
"""

import re

# Standard small-caps Unicode letters used by most "smallcaps" Telegram
# bots. Letters with no good small-caps glyph (q, x) fall back to a
# close visual match; anything not in the map (digits, punctuation,
# emoji, non-Latin scripts) passes through unchanged.
_SMALL_CAPS_MAP = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ꜰ",
    "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ",
    "m": "ᴍ", "n": "ɴ", "o": "ᴏ", "p": "ᴘ", "q": "ǫ", "r": "ʀ",
    "s": "s", "t": "ᴛ", "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x",
    "y": "ʏ", "z": "ᴢ",
}

# Capital-letter versions used for keeping the first letter of each
# word as a normal, easily-readable English capital.
_UPPER = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def _small_caps_word(word: str) -> str:
    """'Bot' -> 'Bᴏᴛ', 'HELLO' -> 'Hᴇʟʟᴏ', 'it's' -> 'Iᴛ's'."""
    if not word:
        return word
    first, rest = word[0], word[1:]
    first_out = first.upper() if first.isalpha() else first
    rest_out = "".join(_SMALL_CAPS_MAP.get(ch.lower(), ch) for ch in rest)
    return first_out + rest_out


def _small_caps_plain(text: str) -> str:
    """Apply small-caps word-by-word to a plain text (no HTML/URLs)."""
    return _WORD_RE.sub(lambda m: _small_caps_word(m.group(0)), text)


# ── Segmenting: pull out the parts that must stay completely normal ──

# Order matters: check HTML tags first, then URLs/commands within the
# remaining plain-text segments.
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^<>]*>")
_CODE_BLOCK_RE = re.compile(r"<code>.*?</code>", re.DOTALL)
_URL_RE = re.compile(
    r"(?:https?://|t\.me/|telegram\.me/|telegram\.dog/)[^\s<]+",
    re.IGNORECASE,
)
_COMMAND_RE = re.compile(r"(?<![\w/])/[a-zA-Z_][a-zA-Z0-9_]*(?:@\w+)?")
_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_]+\}")  # {name}, {group}, etc.

# Combined "leave alone" pattern, checked before falling back to
# small-caps word conversion for everything else.
_SKIP_RE = re.compile(
    "|".join([
        _CODE_BLOCK_RE.pattern,
        _HTML_TAG_RE.pattern,
        _URL_RE.pattern,
        _COMMAND_RE.pattern,
        _PLACEHOLDER_RE.pattern,
    ]),
    re.DOTALL | re.IGNORECASE,
)


def to_small_caps(text: str) -> str:
    """Convert `text` to small-caps style, HTML- and URL/command-safe.

    Splits on the parts that must stay literal (HTML tags, <code>
    blocks, URLs, /commands, {placeholders}) and only small-caps the
    plain-text segments in between.
    """
    if not text:
        return text

    out = []
    pos = 0
    for m in _SKIP_RE.finditer(text):
        if m.start() > pos:
            out.append(_small_caps_plain(text[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    if pos < len(text):
        out.append(_small_caps_plain(text[pos:]))
    return "".join(out)


def patch_outgoing_messages():
    """Monkeypatch aiogram's Message.answer/reply/edit_text and
    CallbackQuery.answer + Bot.send_message so EVERY outgoing text in
    the bot is automatically converted to small-caps style, without
    needing to touch every single handler by hand.

    Safe to call once at startup (see bot/main.py). Idempotent.
    """
    from aiogram import Bot
    from aiogram.types import Message, CallbackQuery

    if getattr(patch_outgoing_messages, "_patched", False):
        return
    patch_outgoing_messages._patched = True

    def _style_kwargs(args, kwargs, text_pos=0, text_key="text"):
        args = list(args)
        if len(args) > text_pos and isinstance(args[text_pos], str):
            args[text_pos] = to_small_caps(args[text_pos])
        elif text_key in kwargs and isinstance(kwargs[text_key], str):
            kwargs[text_key] = to_small_caps(kwargs[text_key])
        return tuple(args), kwargs

    _orig_msg_answer = Message.answer
    _orig_msg_reply = Message.reply
    _orig_msg_edit_text = Message.edit_text
    _orig_bot_send_message = Bot.send_message
    _orig_cbq_answer = CallbackQuery.answer

    async def answer(self, *args, **kwargs):
        args, kwargs = _style_kwargs(args, kwargs)
        return await _orig_msg_answer(self, *args, **kwargs)

    async def reply(self, *args, **kwargs):
        args, kwargs = _style_kwargs(args, kwargs)
        return await _orig_msg_reply(self, *args, **kwargs)

    async def edit_text(self, *args, **kwargs):
        args, kwargs = _style_kwargs(args, kwargs)
        return await _orig_msg_edit_text(self, *args, **kwargs)

    async def send_message(self, chat_id, text, *args, **kwargs):
        text = to_small_caps(text) if isinstance(text, str) else text
        return await _orig_bot_send_message(self, chat_id, text, *args, **kwargs)

    async def cbq_answer(self, text=None, *args, **kwargs):
        # callback_query.answer() popups are short system toasts (e.g.
        # "✅ Enabled: antilink") - style them too for consistency, but
        # callback answers have a strict length limit, so keep it safe.
        if isinstance(text, str):
            text = to_small_caps(text)
        return await _orig_cbq_answer(self, text, *args, **kwargs)

    Message.answer = answer
    Message.reply = reply
    Message.edit_text = edit_text
    Bot.send_message = send_message
    CallbackQuery.answer = cbq_answer
