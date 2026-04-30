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
import re
import string
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
from database.db_premium import *


BAN_SUPPORT = f"{BAN_SUPPORT}"
TUT_VID = f"{TUT_VID}"


def _format_wait_time(seconds: int) -> str:
    """Convert a raw seconds count into a human-readable string like '2h 30m 15s'."""
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
    """
    Delete any active short-link messages this user still has open and
    invalidate their pending records. Called whenever the user requests a
    new file or a new short link — implements "delete the previous one
    and generate a new one" behaviour.
    """
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
    """
    Background task: after `delay` seconds, delete the short-link message
    UNLESS it has already been completed (record was deleted on success).
    If the user successfully verified, the pending doc is gone and we
    leave the message alone.
    """
    try:
        await asyncio.sleep(max(1, int(delay)))
        pending = await db.get_pending_shortener(user_id, base64_string)
        if pending is None:
            return  # user already redeemed it — leave the message be
        # Still pending (or marked expired) → delete the unused message.
        await _delete_message_safely(client, chat_id, message_id)
        # Also expire the record so a future click shows "link expired".
        try:
            await db.expire_pending(user_id, base64_string)
        except Exception:
            pass
    except Exception as e:
        print(f"[bypass] auto-expire task failed: {e}")


async def _auto_delete_message(client: Client, chat_id: int, message_id: int, delay: int):
    """Plain-and-simple delete-after-delay used for the buy-premium QR message."""
    try:
        await asyncio.sleep(max(1, int(delay)))
        await _delete_message_safely(client, chat_id, message_id)
    except Exception as e:
        print(f"[autodelete] failed: {e}")


async def short_url(client: Client, message: Message, base64_string):
    """
    Send the verification/shortener link message for a non-premium user.

    Behaviour:
    1. Cleans up any previously open short-link messages for this user
       (so they only ever have ONE active short link at a time).
    2. If a shortener slot is available, sends the new link, records a
       pending short-link doc with the timestamp (used by bypass detection),
       and schedules a 20-min auto-delete if the link goes unused.
    3. If the user has cleared every shortener for today, shows a
       "come back tomorrow / buy premium" message instead.
    """
    try:
        user_id = message.from_user.id

        # ── Cleanup: kill any prior short-link msg the user still has open
        await _cleanup_prior_pending_for_user(client, user_id)

        prem_link = f"https://t.me/{client.username}?start=yu3elk{base64_string}7"

        short_link, wait_seconds, _slot_idx = await get_shortlink_for_user(user_id, prem_link)

        # ── All shorteners exhausted for today ───────────────────────────────
        if short_link is None:
            wait_str = _format_wait_time(wait_seconds)
            await message.reply_photo(
                photo=SHORTENER_PIC,
                caption=(
                    f"⏳ <b>ʏᴏᴜ'ᴠᴇ ᴜꜱᴇᴅ ᴀʟʟ {len(SHORTLINK_PROVIDERS)} ꜰʀᴇᴇ ᴀᴄᴄᴇꜱꜱ ꜰᴏʀ ᴛᴏᴅᴀʏ‼️</b>\n\n"
                    f"<blockquote>» ᴀ <b>24-ʜᴏᴜʀ ᴄᴏᴏʟᴅᴏᴡɴ</b> ⚠️.</blockquote>\n"
                    f"<blockquote>» ʏᴏᴜʀ ɴᴇxᴛ ꜱʟᴏᴛ ᴏᴘᴇɴꜱ ɪɴ: <b>{wait_str}</b></blockquote>\n\n"
                    f"<blockquote>💎 <b>ᴜᴘɢʀᴀᴅᴇ ᴛᴏ ᴘʀᴇᴍɪᴜᴍ</b> ꜰᴏʀ:\n"
                    f"• ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇꜱꜱ.\n"
                    f"• ᴢᴇʀᴏ ᴀᴅꜱ.\n"
                    f"• ɴᴇᴠᴇʀ ᴡᴀɪᴛ ᴀɢᴀɪɴ ✨.</blockquote>"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ — ᴀᴅ ꜰʀᴇᴇ", callback_data="premium")],
                    [InlineKeyboardButton(f"⏰ ᴄᴏᴍᴇ ʙᴀᴄᴋ ɪɴ {wait_str}", callback_data="close")],
                ]),
            )
            return

        # ── Shortener slot available — normal flow ────────────────────────────
        masked_link = await create_masked_link(short_link)

        buttons = [
            [InlineKeyboardButton("🔰 ᴏᴘᴇɴ ʟɪɴᴋ 🔰", url=masked_link)],
            [InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
            [InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="premium")]
        ]

        sent = await message.reply_photo(
            photo=SHORTENER_PIC,
            caption=SHORT_MSG.format(),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        # Record pending shortener (this both starts the bypass timer and
        # tells the auto-expire task that the message is still "in use").
        try:
            await db.create_pending_shortener(
                user_id=user_id,
                base64=base64_string,
                chat_id=sent.chat.id,
                message_id=sent.id,
            )
        except Exception as e:
            print(f"[bypass] failed to create pending record: {e}")

        # Schedule the 20-min unused-link auto-delete in the background.
        asyncio.create_task(_auto_expire_short_msg(
            client, user_id, base64_string,
            sent.chat.id, sent.id, SHORT_MSG_AUTO_DELETE_SECONDS,
        ))

    except IndexError:
        pass


async def _handle_bypass_attempt(client: Client, message: Message,
                                 user_id: int, base64_string: str):
    """
    Apply the next escalation step for a bypass attempt and send the user
    the appropriate notice. Always finishes by issuing a fresh short link
    (when the user isn't permanently/temporarily banned out of access).
    """
    try:
        result = await db.register_bypass_attempt(user_id)
    except Exception as e:
        print(f"[bypass] register_bypass_attempt failed: {e}")
        return

    action = result['action']
    strikes = result['strikes']

    # Mark the abused link as expired so re-clicking it won't work.
    try:
        await db.expire_pending(user_id, base64_string)
    except Exception:
        pass

    # Compose the warning / ban message — themed to match the rest of the bot.
    common_header = (
        f"<blockquote>⚠️ <b>ʙʏᴘᴀss ᴀᴛᴛᴇᴍᴘᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ</b></blockquote>\n"
        f"<blockquote>» ʏᴏᴜ ʀᴇᴛᴜʀɴᴇᴅ ɪɴ ʟᴇss ᴛʜᴀɴ "
        f"<b>{BYPASS_PROTECTION_SECONDS}s</b> — ᴛʜᴀᴛ ɪs ɴᴏᴛ ᴀʟʟᴏᴡᴇᴅ.</blockquote>\n"
        f"<blockquote>» sᴛʀɪᴋᴇ <b>#{strikes}</b> ᴏɴ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ.</blockquote>\n"
    )

    if action == 'warn':
        text = (
            common_header +
            f"<blockquote>👉 ᴛʜɪs ɪs ʏᴏᴜʀ <b>ғɪʀsᴛ ᴀɴᴅ ᴏɴʟʏ ᴡᴀʀɴɪɴɢ</b>.</blockquote>\n"
            f"<blockquote>👉 ᴄᴏᴍᴘʟᴇᴛᴇ ᴀʟʟ sᴛᴇᴘs ᴘʀᴏᴘᴇʀʟʏ — ᴡᴀᴛᴄʜ ᴛʜᴇ ᴛᴜᴛᴏʀɪᴀʟ.</blockquote>\n"
            f"<blockquote>⚠️ ɴᴇxᴛ ᴀᴛᴛᴇᴍᴘᴛ → <b>12-ʜᴏᴜʀ ʙᴀɴ</b>.</blockquote>"
        )
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
        ]))
        # Re-issue a fresh short link so the user can try again the right way.
        await short_url(client, message, base64_string)
        return

    if action in ('ban_12h', 'ban_24h'):
        hours = 12 if action == 'ban_12h' else 24
        text = (
            common_header +
            f"<blockquote>⛔ ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ <b>ʙᴀɴɴᴇᴅ ғᴏʀ {hours} ʜᴏᴜʀs</b>.</blockquote>\n"
            f"<blockquote>» ɴᴇxᴛ ʙʏᴘᴀss → "
            f"<b>{'24-ʜᴏᴜʀ' if hours == 12 else 'ᴘᴇʀᴍᴀɴᴇɴᴛ'} ʙᴀɴ</b>.</blockquote>\n"
            f"<blockquote>👉 ᴄᴏᴍᴘʟᴇᴛᴇ ᴀʟʟ sᴛᴇᴘs ᴘʀᴏᴘᴇʀʟʏ ɴᴇxᴛ ᴛɪᴍᴇ.</blockquote>"
        )
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Contact Support", url=BAN_SUPPORT)],
        ]))
        return

    # Permanent
    text = (
        common_header +
        f"<blockquote>⛔ ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ <b>ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ʙᴀɴɴᴇᴅ</b> ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.</blockquote>\n"
        f"<blockquote>» ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ ɪғ ʏᴏᴜ ʙᴇʟɪᴇᴠᴇ ᴛʜɪs ɪs ᴀ ᴍɪsᴛᴀᴋᴇ.</blockquote>"
    )
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Contact Support", url=BAN_SUPPORT)],
    ]))


@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    id = message.from_user.id
    is_premium = await is_premium_user(id)

    # Add user if not already present
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except:
            pass

    # ✅ Check Force Subscription
    if not await is_subscribed(client, user_id):
        return await not_joined(client, message)

    # Check if user is banned (admin permanent ban list)
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        return await message.reply_text(
            f"<blockquote>⛔️ <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ</b></blockquote>\n\n"
                            f"<blockquote>ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ <b>ʙᴀɴɴᴇᴅ </b> ғᴏʀ ʙʏᴘᴀss ᴀᴛᴛᴇᴍᴘᴛs.</blockquote>\n"
                            f"<blockquote>ᴡᴇ ᴅᴏ ɴᴏᴛ ᴛᴏʟᴇʀᴀᴛᴇ ᴄʜᴇᴀᴛɪɴɢ. ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ ᴛᴏ ᴀᴘᴘᴇᴀʟ.</blockquote>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Contact Support", url=BAN_SUPPORT)]]
            )
        )

    # Check timed/permanent bypass-protection ban
    bypass_ban = await db.get_bypass_ban(user_id)
    if bypass_ban:
        if bypass_ban.get('permanent'):
            ban_text = (
                f"<blockquote>⛔️ <b>ᴀᴄᴄᴇss ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ʙʟᴏᴄᴋᴇᴅ</b></blockquote>\n"
                f"<blockquote>» ʀᴇᴀsᴏɴ: ʀᴇᴘᴇᴀᴛᴇᴅ ʙʏᴘᴀss ᴀᴛᴛᴇᴍᴘᴛs.</blockquote>\n"
                f"<blockquote>» ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ ᴛᴏ ᴀᴘᴘᴇᴀʟ.</blockquote>"
            )
        else:
            remaining = max(0, int(float(bypass_ban.get('banned_until', 0)) - time.time()))
            ban_text = (
                f"<blockquote>⛔️ <b>ᴛᴇᴍᴘᴏʀᴀʀʏ ʙᴀɴ</b></blockquote>\n"
                f"<blockquote>» ʀᴇᴀsᴏɴ: ʙʏᴘᴀss ᴀᴛᴛᴇᴍᴘᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ.</blockquote>\n"
                f"<blockquote>» ᴜɴʙᴀɴ ɪɴ: <b>{_format_wait_time(remaining)}</b></blockquote>\n"
                f"<blockquote>» ɴᴇxᴛ ᴠɪᴏʟᴀᴛɪᴏɴ ᴡɪʟʟ ɪɴᴄʀᴇᴀsᴇ ᴛʜᴇ ᴘᴇɴᴀʟᴛʏ.</blockquote>"
            )
        return await message.reply_text(
            ban_text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Contact Support", url=BAN_SUPPORT)]]
            )
        )

    # File auto-delete time in seconds
    FILE_AUTO_DELETE = await db.get_del_timer()

    # Handle normal message flow
    text = message.text

    if len(text) > 7:
        try:
            basic = text.split(" ", 1)[1]
            if basic.startswith("yu3elk"):
                base64_string = basic[6:-1]
            else:
                base64_string = basic

            if not is_premium and user_id != OWNER_ID and not basic.startswith("yu3elk"):
                # Brand-new file request from a non-premium user → fresh short link.
                await short_url(client, message, base64_string)
                return

            # === BYPASS PROTECTION (yu3elk callbacks only) ===================
            # When a non-premium user returns via the yu3elk verification link
            # we check how long it's been since the short link was sent. If
            # they're back too fast it's a bypass attempt → escalate.
            if basic.startswith("yu3elk") and not is_premium and user_id != OWNER_ID:
                try:
                    pending = await db.get_pending_shortener(user_id, base64_string)
                except Exception as e:
                    pending = None
                    print(f"[bypass] lookup failed: {e}")

                if pending is None:
                    # No pending record. Either the user already redeemed this
                    # link (legit "Get File Again" reload) or it was wiped by
                    # the daily reset. Allow the file but don't double-count.
                    pass
                elif pending.get('expired'):
                    # Link was invalidated (previous bypass / auto-expire / new
                    # short link issued). Refuse and re-issue.
                    await message.reply_text(
                        "<blockquote>⏳ <b>ᴛʜɪs ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ʟɪɴᴋ ʜᴀs ᴇxᴘɪʀᴇᴅ</b></blockquote>\n"
                        "<blockquote>» ᴀ ɴᴇᴡ sʜᴏʀᴛ ʟɪɴᴋ ʜᴀs ʙᴇᴇɴ ɢᴇɴᴇʀᴀᴛᴇᴅ ʙᴇʟᴏᴡ.</blockquote>\n"
                        "<blockquote>» ᴘʟᴇᴀsᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ᴀʟʟ sᴛᴇᴘs ᴘʀᴏᴘᴇʀʟʏ ᴀɴᴅ ᴡᴀᴛᴄʜ ᴛʜᴇ ᴛᴜᴛᴏʀɪᴀʟ.</blockquote>",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
                        ])
                    )
                    await short_url(client, message, base64_string)
                    return
                else:
                    elapsed = time.time() - float(pending.get('sent_at', 0))
                    if elapsed < BYPASS_PROTECTION_SECONDS:
                        await _handle_bypass_attempt(
                            client, message, user_id, base64_string
                        )
                        return
                    # Legit: clear pending so the message can stay (no auto-delete)
                    try:
                        await db.delete_pending(user_id, base64_string)
                    except Exception:
                        pass
            # =================================================================

            # === SUCCESS / ACCESS TRACKING ============================
            # We only reach this block when the user is actually being
            # granted file access:
            #   * Premium users / OWNER  → record a premium access
            #   * Regular users coming back via the yu3elk callback
            #     → that means they just completed a shortener; advance
            #       their sequential progress and bump the daily counters.
            try:
                if is_premium or user_id == OWNER_ID:
                    await db.record_premium_access(user_id, base64_string)
                elif basic.startswith("yu3elk"):
                    completed_idx = await db.consume_shortener_success(user_id)
                    if completed_idx >= 0:
                        await db.increment_shortener_success(completed_idx)
                        try:
                            cur = await db.get_verify_count(user_id)
                            await db.set_verify_count(user_id, cur + 1)
                        except Exception:
                            pass
            except Exception as track_err:
                print(f"Tracking error (non-fatal): {track_err}")
            # ==========================================================

        except Exception as e:
            print(f"Error processing start payload: {e}")

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

        temp_msg = await message.reply("<b>Please wait...</b>")
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await message.reply_text("Something went wrong!")
            print(f"Error getting messages: {e}")
            return
        finally:
            await temp_msg.delete()

        codeflix_msgs = []

        for msg in messages:
            original_caption = msg.caption.html if msg.caption else ""
            caption = f"{original_caption}\n\n{CUSTOM_CAPTION}" if CUSTOM_CAPTION else original_caption
            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            try:
                snt_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
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
                    protect_content=PROTECT_CONTENT
                )
                codeflix_msgs.append(copied_msg)
            except:
                pass

        if FILE_AUTO_DELETE > 0:
            notification_msg = await message.reply(
                f"<b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇᴅ ɪɴ  {get_exp_time(FILE_AUTO_DELETE)}.</b>"
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
                    [[InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ!", url=reload_url)]]
                ) if reload_url else None

                await notification_msg.edit(
                    "🕊️",
                    reply_markup=keyboard
                )
            except Exception as e:
                print(f"Error updating notification with 'Get File Again' button: {e}")
    else:
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
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            message_effect_id=5104841245755180586)  # 🔥

        return


# =====================================================================================##
# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport


# Create a global dictionary to store chat data
chat_data_cache = {}


async def not_joined(client: Client, message: Message):
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
                        f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @sakxxii</i></b>\n"
                        f"<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e}</blockquote>"
                    )

        try:
            buttons.append([
                InlineKeyboardButton(
                    text='♻️ Tʀʏ Aɢᴀɪɴ',
                    url=f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ])
        except IndexError:
            pass

        await message.reply_photo(
            photo=FORCE_PIC,
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        print(f"Final Error: {e}")
        await temp.edit(
            f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ ᴛᴏ sᴏʟᴠᴇ ᴛʜᴇ ɪssᴜᴇs @sakxxii</i></b>\n"
            f"<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e}</blockquote>"
        )


# =====================================================================================##

@Bot.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id
    status_message = await check_user_plan(user_id)
    await message.reply(status_message)


# =====================================================================================##
@Bot.on_message(filters.command('addpremium') & filters.private & admin)
async def add_premium_user_command(client, msg):
    if len(msg.command) != 4:
        await msg.reply_text(
            "Usage: /addpremium <user_id> <time_value> <time_unit>\n\n"
            "Time Units:\n"
            "s - seconds\n"
            "m - minutes\n"
            "h - hours\n"
            "d - days\n"
            "y - years\n\n"
            "Examples:\n"
            "/addpremium 123456789 30 m → 30 minutes\n"
            "/addpremium 123456789 2 h → 2 hours\n"
            "/addpremium 123456789 1 d → 1 day\n"
            "/addpremium 123456789 1 y → 1 year"
        )
        return

    try:
        user_id = int(msg.command[1])
        time_value = int(msg.command[2])
        time_unit = msg.command[3].lower()

        expiration_time = await add_premium(user_id, time_value, time_unit)

        await msg.reply_text(
            f"✅ User `{user_id}` added as a premium user for {time_value} {time_unit}.\n"
            f"Expiration Time: `{expiration_time}`"
        )

        await client.send_message(
            chat_id=user_id,
            text=(
                f"<blockquote>👑 <b>Pʀᴇᴍɪᴜᴍ Uᴘɢʀᴀᴅᴇ Dᴇᴛᴇᴄᴛᴇᴅ</b></blockquote>\n\n"
                f"<blockquote>ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴꜱ! ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ᴜᴘɢʀᴀᴅᴇᴅ ᴛᴏ ᴛʜᴇ <b>ꜱᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ</b>.</blockquote>\n"
                f"<blockquote>ʏᴏᴜ ɴᴏᴡ ᴘᴏꜱꜱᴇꜱꜱ ᴜɴʀᴇꜱᴛʀɪᴄᴛᴇᴅ ᴀᴄᴄᴇꜱꜱ ᴛᴏ ᴇxᴄʟᴜꜱɪᴠᴇ ᴄᴏɴᴛᴇɴᴛ ᴀɴᴅ ꜰᴇᴀᴛᴜʀᴇꜱ ꜰᴏʀ <b>{time_value} {time_unit}</b>.</blockquote>\n\n"
                f"<blockquote>🗓 <b>ᴇxᴘɪʀᴇꜱ ᴏɴ: </b> `{expiration_time}` </blockquote>"
            ),
        )

    except ValueError:
        await msg.reply_text("❌ Invalid input. Please provide a valid user ID and time.")


# =====================================================================================##
@Bot.on_message(filters.command('remove_premium') & filters.private & admin)
async def remove_premium_user_command(client, msg):
    if len(msg.command) != 2:
        await msg.reply_text("Usage: /remove_premium <user_id>")
        return

    try:
        user_id = int(msg.command[1])
        await remove_premium(user_id)
        await msg.reply_text(f"✅ Premium removed from user `{user_id}`.")
    except ValueError:
        await msg.reply_text("❌ Invalid user ID.")


# =====================================================================================##
@Bot.on_message(filters.command('premium_users') & filters.private & admin)
async def list_premium_users_command(client, msg):
    users = await list_premium_users()
    if not users:
        await msg.reply_text("No premium users found.")
        return

    text = "<b>Premium Users:</b>\n\n"
    for u in users:
        text += f"• {u}\n"

    await msg.reply_text(text)
