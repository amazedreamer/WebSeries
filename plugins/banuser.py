# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.
#

import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from bot import Bot
from config import *
from helper_func import *
from database.database import *



#BAN-USER-SYSTEM
@Bot.on_message(filters.private & filters.command('ban') & admin)
async def add_banuser(client: Client, message: Message):        
    pro = await message.reply("⏳ <i>Pʀᴏᴄᴇssɪɴɢ ʀᴇǫᴜᴇsᴛ...</i>", quote=True)
    banuser_ids = await db.get_ban_users()
    banusers = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close")]])

    if not banusers:
        return await pro.edit(
            "<b>❗ Yᴏᴜ ᴍᴜsᴛ ᴘʀᴏᴠɪᴅᴇ ᴜsᴇʀ IDs ᴛᴏ ʙᴀɴ.</b>\n\n"
            "<b>📌 Usᴀɢᴇ:</b>\n"
            "<code>/ban [user_id]</code> — Ban one or more users by ID.",
            reply_markup=reply_markup
        )

    report, success_count = "", 0
    for uid in banusers:
        try:
            uid_int = int(uid)
        except:
            report += f"⚠️ Iɴᴠᴀʟɪᴅ ID: <code>{uid}</code>\n"
            continue

        if uid_int in await db.get_all_admins() or uid_int == OWNER_ID:
            report += f"⛔ Sᴋɪᴘᴘᴇᴅ ᴀᴅᴍɪɴ/ᴏᴡɴᴇʀ ID: <code>{uid_int}</code>\n"
            continue

        if uid_int in banuser_ids:
            report += f"⚠️ Aʟʀᴇᴀᴅʏ : <code>{uid_int}</code>\n"
            continue

        await db.add_ban_user(uid_int)
        report += f"✅ Bᴀɴɴᴇᴅ: <code>{uid_int}</code>\n"
        success_count += 1

    if success_count:
        await pro.edit(f"<b>✅ Bᴀɴɴᴇᴅ Usᴇʀs Uᴘᴅᴀᴛᴇᴅ:</b>\n\n{report}", reply_markup=reply_markup)
    else:
        await pro.edit(f"<b>❌ Nᴏ ᴜsᴇʀs ᴡᴇʀᴇ ʙᴀɴɴᴇᴅ.</b>\n\n{report}", reply_markup=reply_markup)


@Bot.on_message(filters.private & filters.command('unban') & admin)
async def delete_banuser(client: Client, message: Message):        
    pro = await message.reply("⏳ <i>Pʀᴏᴄᴇssɪɴɢ ʀᴇǫᴜᴇsᴛ...</i>", quote=True)
    banusers = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close")]])

    if not banusers:
        return await pro.edit(
            "<b>❗ Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴜsᴇʀ IDs ᴛᴏ ᴜɴʙᴀɴ.</b>\n\n"
            "<b>📌 Usage:</b>\n"
            "<code>/unban [user_id]</code> — Unban specific user(s)\n"
            "<code>/unban all</code> — Remove all banned users",
            reply_markup=reply_markup
        )

    # ── /unban all — clears BOTH manual bans AND bypass bans ─────────────────
    if banusers[0].lower() == "all":
        manual_ids = await db.get_ban_users()
        bypass_docs = await db.get_all_bypass_bans()
        bypass_ids = [doc['_id'] for doc in bypass_docs]

        all_ids = list(set(manual_ids + bypass_ids))

        if not all_ids:
            return await pro.edit("<b>✅ NO ᴜsᴇʀs ɪɴ ᴛʜᴇ ʙᴀɴ ʟɪsᴛ.</b>", reply_markup=reply_markup)

        for uid in all_ids:
            await db.full_unban_user(uid)

        listed = "\n".join([f"✅ Uɴʙᴀɴɴᴇᴅ: <code>{uid}</code>" for uid in all_ids])
        return await pro.edit(f"<b>🚫 Cʟᴇᴀʀᴇᴅ Bᴀɴ Lɪsᴛ:</b>\n\n{listed}", reply_markup=reply_markup)

    # ── /unban [ids] — checks BOTH ban stores then clears both ────────────────
    report = ""
    for uid in banusers:
        try:
            uid_int = int(uid)
        except:
            report += f"⚠️ Iɴᴀᴠʟɪᴅ ID: <code>{uid}</code>\n"
            continue

        # Check both ban stores
        is_manually_banned = await db.ban_user_exist(uid_int)
        bypass_ban = await db.get_bypass_ban(uid_int)

        if is_manually_banned or bypass_ban:
            # full_unban_user clears both banned_user_data and bypass_bans
            await db.full_unban_user(uid_int)
            report += f"✅ Uɴʙᴀɴɴᴇᴅ: <code>{uid_int}</code>\n"
        else:
            report += f"⚠️ Nᴏᴛ ɪɴ ʙᴀɴ ʟɪsᴛ: <code>{uid_int}</code>\n"

    await pro.edit(f"<b>🚫 Uɴʙᴀɴ Rᴇᴘᴏʀᴛ:</b>\n\n{report}", reply_markup=reply_markup)


@Bot.on_message(filters.private & filters.command('banlist') & admin)
async def get_banuser_list(client: Client, message: Message):        
    pro = await message.reply("⏳ <i>Fᴇᴛᴄʜɪɴɢ Bᴀɴ Lɪsᴛ...</i>", quote=True)

    # Fetch both ban stores in parallel
    manual_ids = await db.get_ban_users()
    bypass_docs = await db.get_all_bypass_bans()

    # Build a unified map: user_id -> ban info
    # Manual bans take precedence; bypass bans are labelled accordingly
    ban_map = {}

    for uid in manual_ids:
        ban_map[uid] = {'type': 'manual', 'label': '🔨 Mᴀɴᴜᴀʟ Bᴀɴ'}

    for doc in bypass_docs:
        uid = doc['_id']
        if uid in ban_map:
            # Already in manual list — add bypass note
            ban_map[uid]['label'] = '🔨 Mᴀɴᴜᴀʟ + ⚠️ Bʏᴘᴀss Bᴀɴ'
        else:
            if doc.get('permanent'):
                label = f"⛔ Pᴇʀᴍᴀɴᴇɴᴛ Bʏᴘᴀss Bᴀɴ (×{doc.get('strikes', '?')} sᴛʀɪᴋᴇs)"
            else:
                until = doc.get('banned_until', 0)
                remaining = max(0, int(until - time.time()))
                hours, rem = divmod(remaining, 3600)
                mins = rem // 60
                time_str = f"{hours}h {mins}m" if hours else f"{mins}m"
                label = f"⏳ Tᴇᴍᴘ Bʏᴘᴀss Bᴀɴ — {time_str} ʟᴇꜰᴛ (×{doc.get('strikes', '?')} sᴛʀɪᴋᴇs)"
            ban_map[uid] = {'type': 'bypass', 'label': label}

    if not ban_map:
        return await pro.edit(
            "<b>✅ NO ᴜsᴇʀs ɪɴ ᴛʜᴇ ʙᴀɴ Lɪsᴛ.</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close")]])
        )

    result = f"<b>🚫 Bᴀɴɴᴇᴅ Usᴇʀs ({len(ban_map)}):</b>\n\n"
    for uid, info in ban_map.items():
        await message.reply_chat_action(ChatAction.TYPING)
        try:
            user = await client.get_users(uid)
            user_link = f'<a href="tg://user?id={uid}">{user.first_name}</a>'
            result += f"• {user_link} — <code>{uid}</code>\n  ↳ {info['label']}\n\n"
        except:
            result += f"• <code>{uid}</code> — <i>Could not fetch name</i>\n  ↳ {info['label']}\n\n"

    await pro.edit(
        result,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close")]])
    )
