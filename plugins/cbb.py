#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
import re as _re
import urllib.parse
from pyrogram import Client, filters
from bot import Bot
from config import *
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import *
from database.db_premium import add_premium, is_premium_user, is_super_premium_user


# ── Inline definition guarantees availability even if the deployed config.py
#    is an older version that does not yet export parse_price_amount. ─────────
def parse_price_amount(price_str: str) -> int:
    """Extract numeric rupee amount from a price string like '50 rs' → 50."""
    m = _re.search(r'\d+', str(price_str))
    return int(m.group()) if m else 0


async def _get_referral_invite_link(client: Client, user_id: int) -> str:
    """
    Return the correct invite link for this user based on the current invite mode:
      - 'bot'     → classic deep-link  t.me/<bot>?start=ref<user_id>
      - 'channel' → unique per-user channel invite link (created on demand)
    Falls back to bot link on any error.
    """
    try:
        mode = await db.get_invite_link_mode()
        if mode == "channel":
            channel_id = await db.get_invite_channel()
            if channel_id:
                return await db.get_or_create_channel_invite(user_id, channel_id, client)
    except Exception as e:
        print(f"[cbb] _get_referral_invite_link error: {e}")
    # Default / fallback
    return f"https://t.me/{client.username}?start=ref{user_id}"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _autodelete_after(client: Client, chat_id: int, message_id: int, delay: int):
    try:
        await asyncio.sleep(max(1, int(delay)))
        await client.delete_messages(chat_id, message_id)
    except Exception:
        pass


async def _smart_edit(client, query, text, reply_markup):
    """Edit text or replace media message with a new text message."""
    try:
        if query.message.photo or query.message.video or query.message.document:
            await query.message.delete()
            await client.send_message(
                chat_id=query.message.chat.id,
                text=text,
                disable_web_page_preview=True,
                reply_markup=reply_markup,
            )
        else:
            await query.message.edit_text(
                text=text,
                disable_web_page_preview=True,
                reply_markup=reply_markup,
            )
    except Exception as e:
        print(f"[cbb] _smart_edit error ({query.data}): {e}")
        try:
            await query.answer("sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.", show_alert=True)
        except Exception:
            pass


def _plan_key_to_info(key: str) -> dict:
    """Look up plan info by key (e.g. 'np_0', 'sp_1')."""
    return ALL_PLANS.get(key)


# ─────────────────────────────────────────────────────────────────────────────
# Main callback handler
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(
    r'^(help|about|start|premium|close|free_premium|ref_back|'
    r'plan_type_|plan_select_|pmt_done|pmt_ok_|pmt_no_|'
    r'rfs_ch_|rfs_toggle_|fsub_back)'
))
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    # ── Help ──────────────────────────────────────────────────────────────────
    if data == "help":
        await _smart_edit(
            client, query,
            text=HELP_TXT.format(first=query.from_user.first_name),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start"),
                    InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close"),
                ]
            ]),
        )

    # ── About ─────────────────────────────────────────────────────────────────
    elif data == "about":
        await _smart_edit(
            client, query,
            text=ABOUT_TXT.format(first=query.from_user.first_name),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start"),
                    InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close"),
                ]
            ]),
        )

    # ── Home / Start ──────────────────────────────────────────────────────────
    elif data == "start":
        await _smart_edit(
            client, query,
            text=START_MSG.format(
                first=query.from_user.first_name,
                last=query.from_user.last_name or "",
                username=f"@{query.from_user.username}" if query.from_user.username else "",
                mention=query.from_user.mention,
                id=query.from_user.id,
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("ʜᴇʟᴘ", callback_data="help"),
                    InlineKeyboardButton("ᴀʙᴏᴜᴛ", callback_data="about"),
                ]
            ]),
        )

    # ── Buy Premium — Step 1: choose plan type ────────────────────────────────
    elif data == "premium":
        await _smart_edit(
            client, query,
            text=(
                f"<blockquote>💎 <b>ᴄʜᴏᴏsᴇ ʏᴏᴜʀ ᴘʟᴀɴ</b></blockquote>\n\n"
                f"<blockquote><b>💎 ɴᴏʀᴍᴀʟ ᴘʀᴇᴍɪᴜᴍ</b>\n"
                f"• ᴢᴇʀᴏ ᴀᴅs & ᴜɴʟɪᴍɪᴛᴇᴅ ꜰɪʟᴇ ᴀᴄᴄᴇss\n"
                f"• sʜᴏʀᴛ-ʟɪɴᴋ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ sᴋɪᴘᴘᴇᴅ\n"
                f"• ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏᴛᴇᴄᴛᴇᴅ (ɴᴏ ᴄᴏᴘʏ/ꜰᴏʀᴡᴀʀᴅ)</blockquote>\n\n"
                f"<blockquote><b>🚀 sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ</b>\n"
                f"• ᴇᴠᴇʀʏᴛʜɪɴɢ ɪɴ ɴᴏʀᴍᴀʟ ᴘʀᴇᴍɪᴜᴍ\n"
                f"• ᴄᴏᴘʏ & ꜰᴏʀᴡᴀʀᴅ ᴇɴᴀʙʟᴇᴅ\n"
                f"• ᴠɪᴘ ᴀᴄᴄᴇss</blockquote>"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 ɴᴏʀᴍᴀʟ ᴘʀᴇᴍɪᴜᴍ", callback_data="plan_type_normal")],
                [InlineKeyboardButton("🚀 sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ", callback_data="plan_type_super")],
                [
                    InlineKeyboardButton("🎁 ꜰʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ", callback_data="free_premium"),
                    InlineKeyboardButton("✖️ ᴄʟᴏsᴇ", callback_data="close"),
                ],
            ]),
        )

    # ── Buy Premium — Step 2: choose duration ─────────────────────────────────
    elif data in ("plan_type_normal", "plan_type_super"):
        is_super = (data == "plan_type_super")
        plans = SUPER_PLANS if is_super else NORMAL_PLANS
        plan_type_label = "🚀 sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ" if is_super else "💎 ɴᴏʀᴍᴀʟ ᴘʀᴇᴍɪᴜᴍ"

        buttons = []
        for p in plans:
            btn_label = f"{p['label']}  —  {p['price_str']}"
            buttons.append([InlineKeyboardButton(btn_label, callback_data=f"plan_select_{p['key']}")])

        buttons.append([
            InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="premium"),
            InlineKeyboardButton("✖️ ᴄʟᴏsᴇ", callback_data="close"),
        ])

        await _smart_edit(
            client, query,
            text=(
                f"<blockquote>{plan_type_label}</blockquote>\n\n"
                f"<blockquote>sᴇʟᴇᴄᴛ ᴀ ᴅᴜʀᴀᴛɪᴏɴ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ:</blockquote>"
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    # ── Buy Premium — Step 3: show payment QR ────────────────────────────────
    elif data.startswith("plan_select_"):
        plan_key = data[len("plan_select_"):]
        plan = _plan_key_to_info(plan_key)
        if not plan:
            await query.answer("ɪɴᴠᴀʟɪᴅ ᴘʟᴀɴ.", show_alert=True)
            return

        amount = parse_price_amount(plan['price_str'])
