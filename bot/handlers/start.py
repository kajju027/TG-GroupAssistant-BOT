from __future__ import annotations

import time

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.core import database as db
from bot.core.config import OWNER_ID, SUDO_IDS, START_TIME
from bot.utils import anim
from bot.utils.filters import NotBlockedFilter
from bot.utils.helpers import get_bot_username, safe_edit
from bot.utils.ui import bold, box, btn, fmt_uptime, kb, link, mono, quote, quote_expandable, row, sc, ubtn

router = Router()


# --------------------------------------------------------------- helpers ---
def _commands_help(user_id: int) -> str:
    group_block = quote_expandable('\n'.join([
        f"⚙️ <b>{sc('Settings')}</b> — open the panel (here, in private)",
        f"🔗 <b>{sc('Anti Link')}</b> — anti-link manager",
        f"🔤 <b>{sc('Anti Word')}</b> — banned words manager",
        f"🚫 <b>{sc('Anti Spam')}</b> — flood protection manager",
        f"👋 <b>{sc('Welcome / Goodbye')}</b> — greetings manager",
        f"🎭 <b>{sc('Reaction')}</b> — quick reaction status",
        f"⚠️ <b>{sc('Warn')}</b> · /unwarn · /warns · /resetwarns",
        f"🔇 <b>{sc('Mute')}</b> [10m/1h/1d] · /unmute · /kick · /ban /unban",
        f"👑 <b>{sc('Promote')}</b> · /demote · /pin /unpin · /purge /del",
        f"🔎 <b>{sc('Filter')}</b> [keyword] [reply] · /filters · /stop [keyword]",
        f"📣 <b>{sc('Tag')}</b> [message] — tag admins · /everyone — tag all",
        f"🛡️ <b>{sc('Antitag')}</b> on/off — channel guard",
        f"🆔 <b>{sc('Id')}</b> · /info · /adminlist · /ping",
    ]))
    dl_block = quote_expandable('\n'.join([
        f"🎧 <b>/play</b> {sc('song or YouTube link')}",
        f"🎬 <b>/video</b> {sc('video title or link')}",
        f"𝕏 <b>/tw</b> {sc('tweet link')}",
        f"📸 <b>/ig</b> {sc('instagram link')}",
        f"📘 <b>/fb</b> {sc('facebook link')}",
        f"📦 <b>/tb</b> {sc('terabox link')}",
        f"📌 <b>/pinterest</b> {sc('pin link')}",
        f"💡 {sc('Paste any supported link here — it is detected automatically.')}",
    ]))
    owner_block = quote_expandable('\n'.join([
        f"👤 <b>/allow</b> · /disallow {sc('id or @username')}",
        "🔒 <b>/block</b> · /unblock",
        f"📋 <b>/users</b> {sc('allowed users')}",
        f"📊 <b>/stats</b> {sc('bot statistics')}",
        f"📢 <b>/broadcast</b> {sc('text')}",
    ]))
    lines = [
        "🛡️ <b>" + sc("Group Management") + "</b>",
        group_block,
        '',
        f"⬇️ <b>{sc('Downloader')}</b>",
        dl_block,
    ]
    if user_id == OWNER_ID or user_id in SUDO_IDS:
        lines += ['', f"👑 <b>{sc('Owner Panel')}</b>", owner_block]
    return box('Commands 📋', lines)


def _about_text(user_id: int, name: str) -> str:
    lines = [
        row('Bot', bold(sc('Group Assistant'))),
        row('Engine', bold(sc('aiogram 3 · async python'))),
        row('Style', bold(sc('small caps + quotes'))),
        row('Uptime', bold(_uptime())),
    ]
    if user_id == OWNER_ID or user_id in SUDO_IDS:
        lines.append('')
        lines.append(f"  👑 {sc('Signed in as owner')} — {link(name, user_id)}")
    return box('About ℹ️', lines)


def _uptime() -> str:
    return fmt_uptime(time.time() - START_TIME)


def _start_text(user_id: int, name: str) -> str:
    from bot.core.config import SUDO_IDS

    if user_id == OWNER_ID or user_id in SUDO_IDS:
        return box('Group Assistant 🤖', [
            f"  👑 {bold(sc('Owner'))} — {link(name, user_id)}",
            '',
            quote(sc('All groups and channels are managed from this private chat — nothing is configured inside the chats.')),
        ])
    if db.is_allowed(user_id):
        return box('Group Assistant 🤖', [
            f"  ✅ {bold(sc('Access Granted'))} — {link(name, user_id)}",
            '',
            quote(sc('You can use the private downloader.')),
        ])
    return box('Group Assistant 🤖', [
        f"  🔒 {bold(sc('Private Bot'))}",
        '',
        quote(sc('Group admins can use /settings inside their groups. Contact the owner for downloader access.')),
    ])


def _start_kb(user_id: int, username: str | None) -> object:
    rows = []
    rows.append([btn('👥 My Chats', 'panel:list')])
    if user_id == OWNER_ID or user_id in SUDO_IDS:
        rows.append([btn('📊 Stats', 'stats:refresh'), btn('ℹ️ About', 'menu:about')])
    else:
        rows.append([btn('📋 Commands', 'menu:help'), btn('ℹ️ About', 'menu:about')])
    rows.append([btn('⬇️ Downloader', 'menu:help:dl')])
    if username:
        rows.append([ubtn('➕ Add To Group', f'https://t.me/{username}?startgroup=assistant')])
    return kb(*rows)


# --------------------------------------------------------------- commands --
@router.message(CommandStart(), NotBlockedFilter())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    db.inc_stat('commands')
    user = message.from_user
    if message.chat.type in {'group', 'supergroup'}:
        username = await get_bot_username(message.bot)
        markup = None
        if username:
            markup = kb([ubtn('⚙️ Open Settings', f'https://t.me/{username}?start=cfg{message.chat.id}')])
        await message.answer(f"✅ <b>{sc('Group Assistant is ready.')}</b>", reply_markup=markup)
        return
    username = await get_bot_username(message.bot)
    payload = command.args if command else None
    if payload == 'help':
        await anim.play(message, _commands_help(user.id), kind='sparkle', reply_markup=kb([btn('🔙 Back', 'menu:start')]))
        return
    if payload and payload.startswith('cfg') and payload[3:].lstrip('-').isdigit():
        from bot.handlers.panel import open_chat_panel_message

        await open_chat_panel_message(message, int(payload[3:]))
        return
    await anim.play(message, _start_text(user.id, user.full_name), kind='sparkle', reply_markup=_start_kb(user.id, username))


@router.message(Command('help', 'commands'), NotBlockedFilter())
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    db.inc_stat('commands')
    if message.chat.type in {'group', 'supergroup'}:
        username = await get_bot_username(message.bot)
        markup = kb([ubtn('📋 Full Commands', f'https://t.me/{username}?start=help')]) if username else None
        await message.answer(box('Commands 📋', [quote(sc('The full command list lives in my private chat — tap below.'))]), reply_markup=markup)
        return
    await anim.play(message, _commands_help(message.from_user.id), kind='sparkle', reply_markup=kb([btn('🔙 Back', 'menu:start')]))


@router.message(Command('ping'))
async def cmd_ping(message: Message):
    db.inc_stat('commands')
    started = time.perf_counter()
    sent = await message.answer('⏳ ...')
    elapsed = (time.perf_counter() - started) * 1000
    await sent.edit_text(box('Pong 🏓', [
        row('Round Trip', bold(f'{elapsed:.0f} ms')),
        row('Uptime', bold(_uptime())),
    ]))


@router.message(Command('id'))
async def cmd_id(message: Message):
    if message.chat.type in {'group', 'supergroup'}:
        await message.answer(box('Ids 🆔', [
            row('Chat', mono(str(message.chat.id))),
            row('Your Id', mono(str(message.from_user.id if message.from_user else '—'))),
        ]))
        return
    await message.answer(box('Your Id 🆔', [
        row('User', mono(str(message.from_user.id if message.from_user else '—'))),
    ]))


# -------------------------------------------------------------- callbacks --
async def _edit_menu(callback: CallbackQuery, text: str, markup=None) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await safe_edit(callback.message, text, markup)


@router.callback_query(lambda query: query.data == 'menu:start')
async def cb_start_menu(callback: CallbackQuery):
    username = await get_bot_username(callback.bot)
    await _edit_menu(callback, _start_text(callback.from_user.id, callback.from_user.full_name), _start_kb(callback.from_user.id, username))


@router.callback_query(lambda query: query.data in {'menu:help', 'help_cmds'})
async def cb_help(callback: CallbackQuery):
    await _edit_menu(callback, _commands_help(callback.from_user.id), kb([btn('🔙 Back', 'menu:start')]))


@router.callback_query(lambda query: query.data == 'menu:help:dl')
async def cb_help_dl(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id != OWNER_ID and not db.is_allowed(user_id):
        await callback.answer('You do not have downloader access.', show_alert=True)
        return
    from bot.handlers.download import DL_HELP

    await _edit_menu(callback, DL_HELP, kb([btn('🔙 Back', 'menu:start')]))


@router.callback_query(lambda query: query.data == 'menu:about')
async def cb_about(callback: CallbackQuery):
    await _edit_menu(callback, _about_text(callback.from_user.id, callback.from_user.full_name), kb([btn('🔙 Back', 'menu:start')]))


@router.callback_query(lambda query: query.data == 'stats:refresh')
async def cb_stats(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID and callback.from_user.id not in SUDO_IDS:
        await callback.answer('Owner only section.', show_alert=True)
        return
    db.inc_stat('commands')
    from bot.database import list_broadcast_chats

    chats = await list_broadcast_chats()
    groups = [c for c in chats if c.get('type') != 'channel']
    channels = [c for c in chats if c.get('type') == 'channel']
    allowed = db.get_allowed()
    stats = db.get_all_stats()
    text = box('Bot Statistics 📊', [
        row('Uptime', bold(_uptime())),
        row('Groups', bold(str(len(groups)))),
        row('Channels', bold(str(len(channels)))),
        row('Allowed Users', bold(str(len(allowed)))),
        row('Messages', bold(str(stats.get('messages', 0)))),
        row('Reactions', bold(str(stats.get('reactions', 0)))),
        row('Commands', bold(str(stats.get('commands', 0)))),
        row('Downloads', bold(str(stats.get('downloads', 0)))),
    ])
    await _edit_menu(callback, text, kb([btn('🔄 Refresh', 'stats:refresh'), btn('🔙 Back', 'menu:start')]))


@router.callback_query(lambda query: query.data == 'close')
async def cb_close(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer('Closed')
    if callback.message is not None:
        try:
            await callback.message.delete()
        except Exception:
            pass
