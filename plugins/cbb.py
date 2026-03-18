#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram import Client, filters
from bot import Bot
from config import *
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import *


# ──────────────────────────────────────────────────────────────────────────────
# Helper: edit a message's text safely regardless of whether it is a
# plain-text or a photo/media message.
#
# • Plain-text message  → edit_text  (fast, no flicker)
# • Photo/media message → delete the old message, send a fresh text message
#   (Telegram does NOT allow edit_text on media messages — doing so raises a
#    BadRequest and leaves the buttons frozen/stuck)
# ──────────────────────────────────────────────────────────────────────────────
async def _smart_edit(client, query, text, reply_markup):
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
            await query.answer("Something went wrong. Please try again.", show_alert=True)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Main callback handler
# ──────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(r'^(help|about|start|premium|close|rfs_ch_|rfs_toggle_|fsub_back)'))
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
                    InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data="close"),
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
                    InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data="close"),
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

    # ── Buy Premium ───────────────────────────────────────────────────────────
    elif data == "premium":
        try:
            await query.message.delete()
        except Exception as e:
            print(f"[cbb] premium: delete failed: {e}")
        try:
            await client.send_photo(
                chat_id=query.message.chat.id,
                photo=QR_PIC,
                caption=(
                    f"<blockquote>✨ <b>𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗣𝗹𝗮𝗻𝘀 — {query.from_user.first_name}</b></blockquote>\n\n"

                    f"<blockquote>💎 <b>ℕ𝕠𝕣𝕞𝕒𝕝 𝐏𝕣𝕖𝕞𝕚𝕦𝕞 </b></blockquote>\n"
                    f"<blockquote>ᴢᴇʀᴏ ᴀᴅs • ᴜɴʟɪᴍɪᴛᴇᴅ ᴠɪᴇᴡs</blockquote>\n"
                    f"<blockquote>• {PRICE1} — 𝟷𝟶 ᴅᴀʏs\n"
                    f"• {PRICE2} — 𝟶𝟷 ᴍᴏɴᴛʜ\n"
                    f"• {PRICE3} — 𝟶𝟹 ᴍᴏɴᴛʜs\n"
                    f"• {PRICE4} — 𝟶6 ᴍᴏɴᴛʜs\n"
                    f"• {PRICE5} — 𝟶𝟷 ʏᴇᴀʀ</blockquote>\n\n"

                    f"<blockquote>💳 <b>ᴘᴀʏ ᴠɪᴀ ᴜᴘɪ ɪᴅ:</b></blockquote>"
                    f"<code>{UPI_ID}</code>\n"
                    f"<blockquote>(Tap to copy UPI)</blockquote>\n\n"

                    f"<blockquote><b>📝 ɪᴍᴘᴏʀᴛᴀɴᴛ ɪɴsᴛʀᴜᴄᴛɪᴏɴs:</b></blockquote>\n"
                    f"<blockquote>1️⃣ ᴘᴀʏ ᴛʜᴇ ᴀᴍᴏᴜɴᴛ ᴠɪᴀ ᴜᴘɪ.\n"
                    f"2️⃣ ᴄʟɪᴄᴋ 'sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ' ʙᴇʟᴏᴡ.</blockquote>"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👨‍💻 sᴇɴᴅ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ", url=SCREENSHOT_URL)],
                    [InlineKeyboardButton("✖️ ᴄʟᴏsᴇ ᴍᴇɴᴜ", callback_data="close")],
                ]),
            )
        except Exception as e:
            print(f"[cbb] premium: send_photo failed: {e}")
            await query.answer("Could not load premium info. Try again.", show_alert=True)

    # ── Close / Dismiss ───────────────────────────────────────────────────────
    elif data == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            await query.message.reply_to_message.delete()
        except Exception:
            pass

    # ── Force-sub channel settings ────────────────────────────────────────────
    elif data.startswith("rfs_ch_"):
        cid = int(data.split("_")[2])
        try:
            chat = await client.get_chat(cid)
            mode = await db.get_channel_mode(cid)
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏғғ"
            new_mode = "ᴏғғ" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(
                    f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}",
                    callback_data=f"rfs_toggle_{cid}_{new_mode}"
                )],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")],
            ]
            await _smart_edit(
                client, query,
                text=f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        except Exception as e:
            print(f"[cbb] rfs_ch_ error: {e}")
            await query.answer("Failed to fetch channel info.", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        parts = data.split("_")
        cid = int(parts[2])
        action = parts[3]
        mode = "on" if action == "on" else "off"

        await db.set_channel_mode(cid, mode)
        await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")

        try:
            chat = await client.get_chat(cid)
            status = "🟢 ON" if mode == "on" else "🔴 OFF"
            new_mode = "off" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(
                    f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}",
                    callback_data=f"rfs_toggle_{cid}_{new_mode}"
                )],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")],
            ]
            await _smart_edit(
                client, query,
                text=f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        except Exception as e:
            print(f"[cbb] rfs_toggle_ error: {e}")

    elif data == "fsub_back":
        try:
            channels = await db.show_channels()
            buttons = []
            for cid in channels:
                try:
                    chat = await client.get_chat(cid)
                    mode = await db.get_channel_mode(cid)
                    status = "🟢" if mode == "on" else "🔴"
                    buttons.append([
                        InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}")
                    ])
                except Exception:
                    continue

            await _smart_edit(
                client, query,
                text="sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        except Exception as e:
            print(f"[cbb] fsub_back error: {e}")


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
