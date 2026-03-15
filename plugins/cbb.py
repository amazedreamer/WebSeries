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

@Bot.on_callback_query(filters.regex(r'^(help|about|start|premium|close|rfs_ch_|rfs_toggle_|fsub_back)'))
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    if data == "help":
        await query.message.edit_text(
            text=HELP_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close')]
            ])
        )

    elif data == "about":
        await query.message.edit_text(
            text=ABOUT_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton('ᴄʟᴏꜱᴇ', callback_data='close')]
            ])
        )

    elif data == "start":
        await query.message.edit_text(
            text=START_MSG.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ʜᴇʟᴘ", callback_data='help'),
                 InlineKeyboardButton("ᴀʙᴏᴜᴛ", callback_data='about')]
            ])
        )


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


    elif data == "premium":
        await query.message.delete()
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
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("👨‍💻 sᴇɴᴅ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ", url=(SCREENSHOT_URL))],
                    [InlineKeyboardButton("✖️ ᴄʟᴏsᴇ ᴍᴇɴᴜ", callback_data="close")],
                ]
            )
        )



    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass

    elif data.startswith("rfs_ch_"):
        cid = int(data.split("_")[2])
        try:
            chat = await client.get_chat(cid)
            mode = await db.get_channel_mode(cid)
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏғғ"
            new_mode = "ᴏғғ" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
            ]
            await query.message.edit_text(
                f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            await query.answer("Failed to fetch channel info", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        cid, action = data.split("_")[2:]
        cid = int(cid)
        mode = "on" if action == "on" else "off"

        await db.set_channel_mode(cid, mode)
        await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")

        # Refresh the same channel's mode view
        chat = await client.get_chat(cid)
        status = "🟢 ON" if mode == "on" else "🔴 OFF"
        new_mode = "off" if mode == "on" else "on"
        buttons = [
            [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
            [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
        ]
        await query.message.edit_text(
            f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "fsub_back":
        channels = await db.show_channels()
        buttons = []
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                mode = await db.get_channel_mode(cid)
                status = "🟢" if mode == "on" else "🔴"
                buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}")])
            except:
                continue

        await query.message.edit_text(
            "sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


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
