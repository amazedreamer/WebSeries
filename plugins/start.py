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
import re
import random
import sys
import string
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                             CallbackQuery, ChatInviteLink, ChatPrivileges)
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from bot import Bot
from config import *
from helper_func import *
from database.database import *
from database.db_premium import *


BAN_SUPPORT = f"{BAN_SUPPORT}"
TUT_VID = f"{TUT_VID}"


def _format_wait_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    parts = []
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


async def _delete_message_safely(client: Client, chat_id: int, message_id: int):
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception:
        pass


async def _cleanup_prior_pending_for_user(client: Client, user_id: int):
    try:
        prior = await db.find_active_pendings_for_user(user_id)
    except Exception as e:
        print(f"[bypass] cleanup lookup failed: {e}")
        return
    for p in prior:
        await _delete_message_safely(client, p.get('chat_id'), p.get('message_id'))
        try:
            await db.expire_pending(p['user_id'], p['base64'])
        except Exception:
            pass


async def _auto_expire_short_msg(client: Client, user_id: int, base64_string: str,
                                  chat_id: int, message_id: int, delay: int):
    try:
        await asyncio.sleep(max(1, int(delay)))
        pending = await db.get_pending_shortener(user_id, base64_string)
        if pending is None:
            return
        await _delete_message_safely(client, chat_id, message_id)
        try:
            await db.expire_pending(user_id, base64_string)
        except Exception:
            pass
    except Exception as e:
        print(f"[bypass] auto-expire task failed: {e}")


async def _auto_delete_message(client: Client, chat_id: int, message_id: int, delay: int):
    try:
        await asyncio.sleep(max(1, int(delay)))
        await _delete_message_safely(client, chat_id, message_id)
    except Exception as e:
        print(f"[autodelete] failed: {e}")


async def short_url(client: Client, message: Message, base64_string):
    """
    Send the verification/shortener link message for a non-premium user.
    Includes a "ɢᴇᴛ ꜰʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ" button in addition to the regular buttons.
    """
    try:
        user_id = message.from_user.id

        await _cleanup_prior_pending_for_user(client, user_id)

        prem_link = f"https://t.me/{client.username}?start=yu3elk{base64_string}7"
        short_link, wait_seconds, _slot_idx = await get_shortlink_for_user(user_id, prem_link)

        if short_link is None:
            wait_str = _format_wait_time(wait_seconds)
            await message.reply_photo(
                photo=SHORTENER_PIC,
                caption=(
                    f"⏳ <b>ʏᴏᴜ'ᴠᴇ ᴜꜱᴇᴅ ᴀʟʟ {len(SHORTLINK_PROVIDERS)} ꜰʀᴇᴇ ᴀᴄᴄᴇꜱꜱ ꜱʟᴏᴛꜱ ꜰᴏʀ ᴛᴏᴅᴀʏ‼️</b>\n\n"
                    f"<blockquote>» ᴀ <b>24-ʜᴏᴜʀ ᴄᴏᴏʟᴅᴏᴡɴ</b> ɪs ɪɴ ᴇꜰꜰᴇᴄᴛ ⚠️.</blockquote>\n"
                    f"<blockquote>» ʏᴏᴜʀ ɴᴇxᴛ ꜱʟᴏᴛ ᴏᴘᴇɴꜱ ɪɴ: <b>{wait_str}</b></blockquote>\n\n"
                    f"<blockquote>💎 <b>ᴜᴘɢʀᴀᴅᴇ ᴛᴏ ᴘʀᴇᴍɪᴜᴍ</b> ꜰᴏʀ:\n"
                    f"• ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇꜱꜱ.\n"
                    f"• ᴢᴇʀᴏ ᴀᴅꜱ.\n"
                    f"• ɴᴇᴠᴇʀ ᴡᴀɪᴛ ᴀɢᴀɪɴ ✨.</blockquote>"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")],
                    [InlineKeyboardButton("🎁 ɢᴇᴛ ꜰʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ", callback_data="free_premium")],
                    [InlineKeyboardButton(f"⏰ ᴄᴏᴍᴇ ʙᴀᴄᴋ ɪɴ {wait_str}", callback_data="close")],
                ]),
            )
            return

        masked_link = await create_masked_link(short_link)

        buttons = [
            [InlineKeyboardButton("🔰 ᴏᴘᴇɴ ʟɪɴᴋ 🔰", url=masked_link)],
            [InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
            [
                InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium"),
                InlineKeyboardButton("🎁 ꜰʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ", callback_data="free_premium"),
            ],
        ]

        sent = await message.reply_photo(
            photo=SHORTENER_PIC,
            caption=SHORT_MSG.format(),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        try:
            await db.create_pending_shortener(
                user_id=user_id,
                base64=base64_string,
                chat_id=sent.chat.id,
                message_id=sent.id,
            )
        except Exception as e:
            print(f"[bypass] failed to create pending record: {e}")

        asyncio.create_task(_auto_expire_short_msg(
            client, user_id, base64_string,
            sent.chat.id, sent.id, SHORT_MSG_AUTO_DELETE_SECONDS,
        ))

    except IndexError:
        pass


async def _handle_bypass_attempt(client: Client, message: Message,
                                  user_id: int, base64_string: str):
    try:
        result = await db.register_bypass_attempt(user_id)
    except Exception as e:
        print(f"[bypass] register_bypass_attempt failed: {e}")
        return

    action = result['action']
    strikes = result['strikes']

    try:
        await db.expire_pending(user_id, base64_string)
    except Exception:
        pass

    common_header = (
        f"<blockquote>⚠️ <b>ʙʏᴘᴀss ᴀᴛᴛᴇᴍᴘᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ</b></blockquote>\n"
        f"<blockquote>ᴀᴄᴄᴇꜱꜱ ᴛʜʀᴏᴜɢʜ sʜᴏʀᴛ-ʟɪɴᴋ sᴋɪᴘᴘɪɴɢ — ɴᴏᴛ ᴀʟʟᴏᴡᴇᴅ.</blockquote>\n\n"
        f"<blockquote>» <b>sᴛʀɪᴋᴇ #{strikes}</b> ᴏɴ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ.</blockquote>\n"
    )

    if action == 'warn':
        text = (
            common_header +
            f"<blockquote>👉 ᴛʜɪs ɪs ʏᴏᴜʀ <b>ꜰɪʀsᴛ ᴀɴᴅ ᴏɴʟʏ ᴡᴀʀɴɪɴɢ</b>.</blockquote>\n"
            f"<blockquote>👉 ᴄᴏᴍᴘʟᴇᴛᴇ ᴀʟʟ sᴛᴇᴘs ᴘʀᴏᴘᴇʀʟʏ — ᴡᴀᴛᴄʜ ᴛʜᴇ ᴛᴜᴛᴏʀɪᴀʟ.</blockquote>\n"
            f"<blockquote>⚠️ ɴᴇxᴛ ᴀᴛᴛᴇᴍᴘᴛ → <b>12-ʜᴏᴜʀ ʙᴀɴ</b>.</blockquote>"
        )
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
        ]))
        await short_url(client, message, base64_string)
        return

    if action in ('ban_12h', 'ban_24h'):
        hours = 12 if action == 'ban_12h' else 24
        text = (
            common_header +
            f"<blockquote>⛔ ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ <b>ʙᴀɴɴᴇᴅ ꜰᴏʀ {hours} ʜᴏᴜʀs</b>.</blockquote>\n"
            f"<blockquote>» ɴᴇxᴛ ʙʏᴘᴀss → "
            f"<b>{'24-ʜᴏᴜʀ' if hours == 12 else 'ᴘᴇʀᴍᴀɴᴇɴᴛ'} ʙᴀɴ</b>.</blockquote>\n"
            f"<blockquote>👉 ᴄᴏᴍᴘʟᴇᴛᴇ ᴀʟʟ sᴛᴇᴘs ᴘʀᴏᴘᴇʀʟʏ ɴᴇxᴛ ᴛɪᴍᴇ.</blockquote>"
        )
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ", url=BAN_SUPPORT)],
        ]))
        return

    text = (
        common_header +
        f"<blockquote>⛔ ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ <b>ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ʙᴀɴɴᴇᴅ</b> ꜰʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.</blockquote>\n"
        f"<blockquote>» ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ ɪꜰ ʏᴏᴜ ʙᴇʟɪᴇᴠᴇ ᴛʜɪs ɪs ᴀ ᴍɪsᴛᴀᴋᴇ.</blockquote>"
    )
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ", url=BAN_SUPPORT)],
    ]))


# ═══════════════════════════════════════════════════════════════════════════
# /start command handler
# ═══════════════════════════════════════════════════════════════════════════
@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    is_premium = await is_premium_user(user_id)
    is_super_premium = await is_super_premium_user(user_id)

    # ── Register user if new ─────────────────────────────────────────────────
    is_new_user = not await db.present_user(user_id)
    if is_new_user:
        try:
            await db.add_user(user_id)
        except Exception:
            pass

    # ── Parse start param ───────────────────────────────────────────────────
    text = message.text
    start_param = text.split(" ", 1)[1] if len(text) > 7 else ""

    # ── Handle referral join (ref<referrer_id>) ──────────────────────────────
    # Must be processed BEFORE force-sub check so the referrer gets notified
    # even if the new user still needs to join channels.
    if start_param.startswith("ref") and start_param[3:].isdigit():
        referrer_id = int(start_param[3:])
        if referrer_id != user_id:
            is_new_referral = await db.record_referral_join(
                invitee_id=user_id,
                referrer_id=referrer_id
            )
            if is_new_referral:
                # Notify the referrer that someone joined via their link
                try:
                    await client.send_message(
                        chat_id=referrer_id,
                        text=(
                            f"<blockquote>🎉 <b>ɴᴇᴡ ɪɴᴠɪᴛᴇ ᴊᴏɪɴ!</b></blockquote>\n\n"
                            f"<blockquote>ꜱᴏᴍᴇᴏɴᴇ ᴊᴜꜱᴛ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴠɪᴀ ʏᴏᴜʀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ! 👥</blockquote>\n\n"
                            f"<blockquote expandable>⚠️ ᴛʜɪs ɪɴᴠɪᴛᴇ ᴡɪʟʟ <b>ᴏɴʟʏ ʙᴇ ᴄᴏᴜɴᴛᴇᴅ</b> ᴡʜᴇɴ ᴛʜᴇʏ:\n"
                            f"• ᴄᴏᴍᴘʟᴇᴛᴇ ᴀ sʜᴏʀᴛ-ʟɪɴᴋ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ, ᴏʀ\n"
                            f"• ᴘᴜʀᴄʜᴀꜱᴇ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ᴡɪᴛʜɪɴ ᴛʜɪs ᴍᴏɴᴛʜ.</blockquote>"
                        ),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📊 ᴍʏ ɪɴᴠɪᴛᴇ ᴅᴀꜱʜʙᴏᴀʀᴅ", callback_data="free_premium")],
                        ])
                    )
                except Exception:
                    pass

    # ── Force subscription check ─────────────────────────────────────────────
    if not await is_subscribed(client, user_id):
        return await not_joined(client, message, start_param)

    # ── Manual ban check ─────────────────────────────────────────────────────
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        return await message.reply_text(
            f"<blockquote>⛔️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ</b></blockquote>\n\n"
            f"<blockquote>ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ <b>ʙᴀɴɴᴇᴅ</b> ꜰᴏʀ ʙʏᴘᴀss ᴀᴛᴛᴇᴍᴘᴛs.</blockquote>\n"
            f"<blockquote>ᴡᴇ ᴅᴏ ɴᴏᴛ ᴛᴏʟᴇʀᴀᴛᴇ ᴄʜᴇᴀᴛɪɴɢ. ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ ᴛᴏ ᴀᴘᴘᴇᴀʟ.</blockquote>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ", url=BAN_SUPPORT)]]
            )
        )

    # ── Bypass-protection ban check ──────────────────────────────────────────
    bypass_ban = await db.get_bypass_ban(user_id)
    if bypass_ban:
        if bypass_ban.get('permanent'):
            ban_text = (
                f"<blockquote>⛔️ <b>ᴀᴄᴄᴇss ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ʙʟᴏᴄᴋᴇᴅ</b></blockquote>\n"
                f"<blockquote>» ʀᴇᴀꜱᴏɴ: ʀᴇᴘᴇᴀᴛᴇᴅ ʙʏᴘᴀss ᴀᴛᴛᴇᴍᴘᴛs.</blockquote>\n"
                f"<blockquote>» ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ ᴛᴏ ᴀᴘᴘᴇᴀʟ.</blockquote>"
            )
        else:
            remaining = max(0, int(float(bypass_ban.get('banned_until', 0)) - time.time()))
            ban_text = (
                f"<blockquote>⛔️ <b>ᴛᴇᴍᴘᴏʀᴀʀʏ ʙᴀɴ</b></blockquote>\n"
                f"<blockquote>» ʀᴇᴀꜱᴏɴ: ʙʏᴘᴀss ᴀᴛᴛᴇᴍᴘᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ.</blockquote>\n"
                f"<blockquote>» ᴜɴʙᴀɴ ɪɴ: <b>{_format_wait_time(remaining)}</b></blockquote>\n"
                f"<blockquote>» ɴᴇxᴛ ᴠɪᴏʟᴀᴛɪᴏɴ ᴡɪʟʟ ɪɴᴄʀᴇᴀꜱᴇ ᴛʜᴇ ᴘᴇɴᴀʟᴛʏ.</blockquote>"
            )
        return await message.reply_text(
            ban_text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ", url=BAN_SUPPORT)]]
            )
        )

    # ── Track new channel join today ─────────────────────────────────────────
    if is_new_user:
        try:
            await db.record_new_channel_join(user_id)
        except Exception:
            pass

    # ── Thank referral invitee for joining channels ──────────────────────────
    if is_new_user:
        referrer_id = await db.get_referrer_of(user_id)
        if referrer_id:
            try:
                await message.reply_text(
                    f"<blockquote>🎉 <b>ᴡᴇʟᴄᴏᴍᴇ!</b></blockquote>\n\n"
                    f"<blockquote>ᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴊᴏɪɴɪɴɢ ᴏᴜʀ ᴄʜᴀɴɴᴇʟꜱ! 🙌</blockquote>\n"
                    f"<blockquote expandable>ᴛᴏ <b>ᴄᴏᴜɴᴛ ᴀꜱ ᴀ ᴠᴀʟɪᴅ ɪɴᴠɪᴛᴇ</b> ꜰᴏʀ ʏᴏᴜʀ ɪɴᴠɪᴛᴇʀ, ᴘʟᴇᴀsᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ᴀᴛ ʟᴇᴀsᴛ ᴏɴᴇ sʜᴏʀᴛ-ʟɪɴᴋ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴡʜᴇɴ ʏᴏᴜ ᴅᴏᴡɴʟᴏᴀᴅ ᴄᴏɴᴛᴇɴᴛ.</blockquote>"
                )
            except Exception:
                pass

    FILE_AUTO_DELETE = await db.get_del_timer()

    # ── No start param — show home screen ───────────────────────────────────
    if not start_param or start_param.startswith("ref"):
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("• ᴍᴏʀᴇ ᴄʜᴀɴɴᴇʟs •", url="https://t.me/TheEroticBhabhiOfficial/18")],
                [
                    InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data="about"),
                    InlineKeyboardButton('ʜᴇʟᴘ •', callback_data="help")
                ]
            ]
        )
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name or "",
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            message_effect_id=5104841245755180586
        )
        return

    # ── File / content start param ───────────────────────────────────────────
    try:
        basic = start_param
        if basic.startswith("yu3elk"):
            base64_string = basic[6:-1]
        else:
            base64_string = basic

        if not is_premium and not is_super_premium and user_id != OWNER_ID and not basic.startswith("yu3elk"):
            _vmode = await db.get_verification_mode()
            if _vmode != 'instant':
                _has_access, _ = await db.check_shortener_access(user_id)
                if _has_access:
                    pass
                else:
                    await short_url(client, message, base64_string)
                    return
            else:
                await short_url(client, message, base64_string)
                return

        # ── Bypass protection ────────────────────────────────────────────────
        if basic.startswith("yu3elk") and not is_premium and not is_super_premium and user_id != OWNER_ID:
            try:
                pending = await db.get_pending_shortener(user_id, base64_string)
            except Exception as e:
                pending = None
                print(f"[bypass] lookup failed: {e}")

            if pending is None:
                pass
            elif pending.get('expired'):
                await message.reply_text(
                    "<blockquote>⏳ <b>ᴛʜɪs ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ ʜᴀs ᴇxᴘɪʀᴇᴅ</b></blockquote>\n\n"
                    "<blockquote>» ᴘʟᴇᴀꜱᴇ ᴅᴏɴ'ᴛ ᴜꜱᴇ ᴏʟᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ʟɪɴᴋꜱ, ᴋɪɴᴅʟʏ ʀᴇǫᴜᴇꜱᴛ ᴀ ɴᴇᴡ ᴏɴᴇ.</blockquote>\n",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
                    ])
                )
                await short_url(client, message, base64_string)
                return
            else:
                elapsed = time.time() - float(pending.get('sent_at', 0))
                if elapsed < BYPASS_PROTECTION_SECONDS:
                    await _handle_bypass_attempt(client, message, user_id, base64_string)
                    return
                try:
                    await db.delete_pending(user_id, base64_string)
                except Exception:
                    pass

        # ── Track successful access + validate referral ──────────────────────
        try:
            if is_premium or is_super_premium or user_id == OWNER_ID:
                await db.record_premium_access(user_id, base64_string)
            elif basic.startswith("yu3elk"):
                completed_idx = await db.consume_shortener_success(user_id)
                if completed_idx >= 0:
                    await db.increment_shortener_success(completed_idx)
                    try:
                        await db.mark_shortener_used(user_id, completed_idx, hours=24)
                    except Exception as cd_err:
                        print(f"[cooldown] mark_shortener_used failed: {cd_err}")
                    try:
                        _vmode_grant = await db.get_verification_mode()
                        if _vmode_grant == '12h':
                            await db.grant_shortener_access(user_id, hours=12)
                        elif _vmode_grant == '24h':
                            await db.grant_shortener_access(user_id, hours=24)
                    except Exception as vg_err:
                        print(f"[vmode] grant_shortener_access failed: {vg_err}")
                    try:
                        cur = await db.get_verify_count(user_id)
                        await db.set_verify_count(user_id, cur + 1)
                    except Exception:
                        pass

                    # ── Referral validation: this user just completed their first shortener ──
                    await _handle_referral_validation(client, user_id)

        except Exception as track_err:
            print(f"Tracking error (non-fatal): {track_err}")

    except Exception as e:
        print(f"Error processing start payload: {e}")

    # ── Decode and serve file(s) ─────────────────────────────────────────────
    try:
        string = await decode(base64_string)
        argument = string.split("-")
        ids = []
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                print(f"Error decoding IDs: {e}")
                return
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except Exception as e:
                print(f"Error decoding ID: {e}")
                return

        temp_msg = await message.reply("<b>ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ...</b>")
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await message.reply_text("sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ!")
            print(f"Error getting messages: {e}")
            return
        finally:
            await temp_msg.delete()

        codeflix_msgs = []
        for msg in messages:
            original_caption = msg.caption.html if msg.caption else ""
            caption = f"{original_caption}\n\n{CUSTOM_CAPTION}" if CUSTOM_CAPTION else original_caption
            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None
            _file_protect = False if is_super_premium else PROTECT_CONTENT
            try:
                snt_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=_file_protect
                )
                await asyncio.sleep(0.5)
                codeflix_msgs.append(snt_msg)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=_file_protect
                )
                codeflix_msgs.append(copied_msg)
            except Exception:
                pass

        if FILE_AUTO_DELETE > 0:
            notification_msg = await message.reply(
                f"<b>ᴛʜɪs ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ {get_exp_time(FILE_AUTO_DELETE)}.</b>"
            )
            await asyncio.sleep(FILE_AUTO_DELETE)
            for snt_msg in codeflix_msgs:
                if snt_msg:
                    try:
                        await snt_msg.delete()
                    except Exception as e:
                        print(f"Error deleting message {snt_msg.id}: {e}")
            try:
                reload_url = (
                    f"https://t.me/{client.username}?start={message.command[1]}"
                    if message.command and len(message.command) > 1
                    else None
                )
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("ɢᴇᴛ ꜰɪʟᴇ ᴀɢᴀɪɴ!", url=reload_url)]]
                ) if reload_url else None
                await notification_msg.edit("🕊️", reply_markup=keyboard)
            except Exception as e:
                print(f"Error updating notification: {e}")

    except Exception as e:
        print(f"Error serving file: {e}")


async def _handle_referral_validation(client: Client, user_id: int):
    """
    Called when user_id successfully completes a short-link verification.
    Validates their referral (if any) and checks whether the referrer
    has hit a new reward milestone this month.
    """
    try:
        referrer_id = await db.validate_referral(user_id)
        if referrer_id <= 0:
            return

        # Check if referrer has crossed a new reward milestone
        days_reward, label = await db.check_and_get_pending_reward(referrer_id)
        if days_reward > 0:
            # Grant the reward
            from database.db_premium import add_premium
            await add_premium(referrer_id, days_reward, 'd')
            try:
                await client.send_message(
                    chat_id=referrer_id,
                    text=(
                        f"<blockquote>🎁 <b>ʀᴇᴡᴀʀᴅ ᴜɴʟᴏᴄᴋᴇᴅ!</b></blockquote>\n\n"
                        f"<blockquote>🏆 ʏᴏᴜ ʜᴀᴠᴇ ᴇᴀʀɴᴇᴅ <b>{label}</b> ᴏꜰ ꜰʀᴇᴇ ɴᴏʀᴍᴀʟ ᴘʀᴇᴍɪᴜᴍ!</blockquote>\n"
                        f"<blockquote expandable>ᴛʜɪs ʀᴇᴡᴀʀᴅ ʜᴀs ʙᴇᴇɴ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴏɴ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ. ᴋᴇᴇᴘ ɪɴᴠɪᴛɪɴɢ ꜰʀɪᴇɴᴅs ᴛᴏ ᴇᴀʀɴ ᴍᴏʀᴇ!</blockquote>"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📊 ᴍʏ ɪɴᴠɪᴛᴇ ᴅᴀꜱʜʙᴏᴀʀᴅ", callback_data="free_premium")],
                    ])
                )
            except Exception:
                pass
        else:
            # Just notify referrer that a new invitee validated
            try:
                stats = await db.get_referral_stats(referrer_id)
                validated = stats['month_validated']
                # Find next milestone
                next_milestone = None
                next_label = ""
                for (min_inv, d, lbl) in REFERRAL_MILESTONES:
                    if min_inv not in stats['rewards_given_this_month'] and validated < min_inv:
                        next_milestone = min_inv
                        next_label = lbl
                        break
                progress_msg = (
                    f"<blockquote>✅ <b>ɪɴᴠɪᴛᴇ ᴠᴀʟɪᴅᴀᴛᴇᴅ!</b></blockquote>\n\n"
                    f"<blockquote>ᴀ ᴜꜱᴇʀ ʏᴏᴜ ɪɴᴠɪᴛᴇᴅ ʜᴀs ᴊᴜsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇɪʀ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ! 🎯</blockquote>\n"
                    f"<blockquote>» ᴠᴀʟɪᴅᴀᴛᴇᴅ ᴛʜɪs ᴍᴏɴᴛʜ: <b>{validated}</b></blockquote>"
                )
                if next_milestone:
                    progress_msg += (
                        f"\n<blockquote>» ɴᴇxᴛ ʀᴇᴡᴀʀᴅ: <b>{next_milestone - validated}</b> ᴍᴏʀᴇ ᴛᴏ ᴇᴀʀɴ <b>{next_label}</b> ꜰʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ!</blockquote>"
                    )
                await client.send_message(
                    chat_id=referrer_id,
                    text=progress_msg,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📊 ᴍʏ ᴅᴀꜱʜʙᴏᴀʀᴅ", callback_data="free_premium")],
                    ])
                )
            except Exception:
                pass
    except Exception as e:
        print(f"[referral] validation handler failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# Force-sub: not joined screen
# ═══════════════════════════════════════════════════════════════════════════
chat_data_cache = {}


async def not_joined(client: Client, message: Message, start_param: str = ""):
    temp = await message.reply("<b>(●'◡'●)</b>")
    user_id = message.from_user.id
    buttons = []
    count = 0

    try:
        all_channels = await db.show_channels()
        for total, chat_id in enumerate(all_channels, start=1):
            mode = await db.get_channel_mode(chat_id)
            await message.reply_chat_action(ChatAction.TYPING)

            if not await is_sub(client, user_id, chat_id):
                try:
                    if chat_id in chat_data_cache:
                        data = chat_data_cache[chat_id]
                    else:
                        data = await client.get_chat(chat_id)
                        chat_data_cache[chat_id] = data

                    name = data.title

                    if mode == "on" and not data.username:
                        invite = await client.create_chat_invite_link(
                            chat_id=chat_id,
                            creates_join_request=True,
                            expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None
                        )
                        link = invite.invite_link
                    else:
                        if data.username:
                            link = f"https://t.me/{data.username}"
                        else:
                            invite = await client.create_chat_invite_link(
                                chat_id=chat_id,
                                expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None
                            )
                            link = invite.invite_link

                    buttons.append([InlineKeyboardButton(text=name, url=link)])
                    count += 1
                    await temp.edit(f"<b>{'! ' * count}</b>")

                except Exception as e:
                    print(f"Error with chat {chat_id}: {e}")
                    return await temp.edit(
                        f"<b><i>! ᴇʀʀᴏʀ, ᴄᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ ꜱᴏʟᴠᴇ ᴛʜᴇ ɪꜱꜱᴜᴇꜱ @sakxxii</i></b>\n"
                        f"<blockquote expandable><b>ʀᴇᴀꜱᴏɴ:</b> {e}</blockquote>"
                    )

        try:
            # Preserve start param in reload URL so file is served after join
            reload_param = start_param if start_param and not start_param.startswith("ref") else message.command[1] if message.command and len(message.command) > 1 else None
            if reload_param:
                buttons.append([
                    InlineKeyboardButton(
                        text='♻️ ᴛʀʏ ᴀɢᴀɪɴ',
                        url=f"https://t.me/{client.username}?start={reload_param}"
                    )
                ])
        except IndexError:
            pass

        await message.reply_photo(
            photo=FORCE_PIC,
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name or "",
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        print(f"Final Error: {e}")
        await temp.edit(
            f"<b><i>! ᴇʀʀᴏʀ, ᴄᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ @sakxxii</i></b>\n"
            f"<blockquote expandable><b>ʀᴇᴀꜱᴏɴ:</b> {e}</blockquote>"
        )


# ═══════════════════════════════════════════════════════════════════════════
# /myplan
# ═══════════════════════════════════════════════════════════════════════════
@Bot.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id
    sp_status = await check_super_premium_plan(user_id)
    prem_status = await check_user_plan(user_id)
    text = (
        f"<blockquote>🚀 <b>sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ</b></blockquote>\n{sp_status}\n\n"
        f"<blockquote>💎 <b>ɴᴏʀᴍᴀʟ ᴘʀᴇᴍɪᴜᴍ</b></blockquote>\n{prem_status}"
    )
    await message.reply(text)


# ═══════════════════════════════════════════════════════════════════════════
# Super Premium commands (owner only)
# ═══════════════════════════════════════════════════════════════════════════
@Bot.on_message(filters.command('addsuperpremium') & filters.private & filters.user(OWNER_ID))
async def add_super_premium_command(client: Client, msg: Message):
    if len(msg.command) != 3:
        await msg.reply_text(
            "ᴜsᴀɢᴇ: /addsuperpremium <user_id> <days>\n\n"
            "ᴇxᴀᴍᴘʟᴇs:\n"
            "/addsuperpremium 123456789 30 → 30 ᴅᴀʏs\n"
            "/addsuperpremium 123456789 365 → 1 ʏᴇᴀʀ"
        )
        return
    try:
        target_id = int(msg.command[1])
        days = int(msg.command[2])
        if days <= 0:
            raise ValueError("days must be > 0")
        expiry = await add_super_premium(target_id, days)
        await msg.reply_text(
            f"✅ ᴜsᴇʀ <code>{target_id}</code> ɢʀᴀɴᴛᴇᴅ <b>sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ</b> ꜰᴏʀ <b>{days} ᴅᴀʏ(s)</b>.\n"
            f"ᴇxᴘɪʀᴇs: <code>{expiry}</code>"
        )
        try:
            await client.send_message(
                chat_id=target_id,
                text=(
                    f"<blockquote>🚀 <b>sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</b></blockquote>\n\n"
                    f"<blockquote>ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs! ʏᴏᴜʀ <b>sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ</b> ᴘʟᴀɴ ɪs ɴᴏᴡ ᴀᴄᴛɪᴠᴇ.</blockquote>\n"
                    f"<blockquote>✅ sʜᴏʀᴛᴇɴᴇʀ sᴋɪᴘᴘᴇᴅ — ᴅɪʀᴇᴄᴛ ꜰɪʟᴇ ᴀᴄᴄᴇss</blockquote>\n"
                    f"<blockquote>✅ ᴄᴏᴘʏ & ꜰᴏʀᴡᴀʀᴅ ᴇɴᴀʙʟᴇᴅ</blockquote>\n\n"
                    f"<blockquote>🗓 <b>ᴇxᴘɪʀᴇs:</b> <code>{expiry}</code></blockquote>"
                )
            )
        except Exception:
            pass
    except ValueError as e:
        await msg.reply_text(f"❌ ɪɴᴠᴀʟɪᴅ ɪɴᴘᴜᴛ: {e}")


@Bot.on_message(filters.command('remove_superpremium') & filters.private & filters.user(OWNER_ID))
async def remove_super_premium_command(client: Client, msg: Message):
    if len(msg.command) != 2:
        await msg.reply_text("ᴜsᴀɢᴇ: /remove_superpremium <user_id>")
        return
    try:
        target_id = int(msg.command[1])
        await remove_super_premium(target_id)
        await msg.reply_text(f"✅ sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ᴜsᴇʀ <code>{target_id}</code>.")
        try:
            await client.send_message(
                chat_id=target_id,
                text=(
                    "<blockquote>ℹ️ <b>sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴇɴᴅᴇᴅ</b></blockquote>\n\n"
                    "<blockquote>ʏᴏᴜʀ sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ʙʏ ᴛʜᴇ ᴏᴡɴᴇʀ.</blockquote>"
                )
            )
        except Exception:
            pass
    except ValueError:
        await msg.reply_text("❌ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ.")


@Bot.on_message(filters.command('superpremium_users') & filters.private & filters.user(OWNER_ID))
async def list_super_premium_command(client: Client, msg: Message):
    users = await list_super_premium_users()
    if not users:
        await msg.reply_text("ɴᴏ ᴀᴄᴛɪᴠᴇ sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ꜰᴏᴜɴᴅ.")
        return
    text = "<b>🚀 ᴀᴄᴛɪᴠᴇ sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs:</b>\n\n"
    for u in users:
        text += f"• {u}\n"
    await msg.reply_text(text)


# ═══════════════════════════════════════════════════════════════════════════
# Premium user management (admin)
# ═══════════════════════════════════════════════════════════════════════════
@Bot.on_message(filters.command('addpremium') & filters.private & admin)
async def add_premium_user_command(client, msg):
    if len(msg.command) != 4:
        await msg.reply_text(
            "ᴜsᴀɢᴇ: /addpremium <user_id> <time_value> <time_unit>\n\n"
            "ᴛɪᴍᴇ ᴜɴɪᴛs: s m h d y\n\n"
            "ᴇxᴀᴍᴘʟᴇs:\n"
            "/addpremium 123456789 30 d → 30 ᴅᴀʏs\n"
            "/addpremium 123456789 1 y → 1 ʏᴇᴀʀ"
        )
        return
    try:
        user_id = int(msg.command[1])
        time_value = int(msg.command[2])
        time_unit = msg.command[3].lower()
        expiration_time = await add_premium(user_id, time_value, time_unit)
        await msg.reply_text(
            f"✅ ᴜsᴇʀ <code>{user_id}</code> ᴀᴅᴅᴇᴅ ᴀs ᴘʀᴇᴍɪᴜᴍ ꜰᴏʀ {time_value}{time_unit}.\n"
            f"ᴇxᴘɪʀᴇs: <code>{expiration_time}</code>"
        )
        try:
            await client.send_message(
                chat_id=user_id,
                text=(
                    f"<blockquote>👑 <b>ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</b></blockquote>\n\n"
                    f"<blockquote>ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs! ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ᴜᴘɢʀᴀᴅᴇᴅ ᴛᴏ ᴘʀᴇᴍɪᴜᴍ.</blockquote>\n"
                    f"<blockquote>✅ ᴢᴇʀᴏ ᴀᴅs • ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss</blockquote>\n\n"
                    f"<blockquote>🗓 <b>ᴇxᴘɪʀᴇs:</b> <code>{expiration_time}</code></blockquote>"
                ),
            )
        except Exception:
            pass
    except ValueError:
        await msg.reply_text("❌ ɪɴᴠᴀʟɪᴅ ɪɴᴘᴜᴛ.")


@Bot.on_message(filters.command('remove_premium') & filters.private & admin)
async def remove_premium_user_command(client, msg):
    if len(msg.command) != 2:
        await msg.reply_text("ᴜsᴀɢᴇ: /remove_premium <user_id>")
        return
    try:
        user_id = int(msg.command[1])
        await remove_premium(user_id)
        await msg.reply_text(f"✅ ᴘʀᴇᴍɪᴜᴍ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ᴜsᴇʀ <code>{user_id}</code>.")
    except ValueError:
        await msg.reply_text("❌ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ.")


@Bot.on_message(filters.command('premium_users') & filters.private & admin)
async def list_premium_users_command(client, msg):
    users = await list_premium_users()
    if not users:
        await msg.reply_text("ɴᴏ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ꜰᴏᴜɴᴅ.")
        return
    text = "<b>💎 ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs:</b>\n\n"
    for u in users:
        text += f"• {u}\n"
    await msg.reply_text(text)
