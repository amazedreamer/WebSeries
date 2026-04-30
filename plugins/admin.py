import asyncio
import os
import random
import sys
import time
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus, ChatType
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatMemberUpdated, ChatPermissions
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, InviteHashEmpty, ChatAdminRequired, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from bot import Bot
from config import *
from helper_func import *
from database.database import *



# Commands for adding admins by owner
@Bot.on_message(filters.command('add_admin') & filters.private & filters.user(OWNER_ID))
async def add_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    check = 0
    admin_ids = await db.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>You need to provide user ID(s) to add as admin.</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/add_admin [user_id]</code> — Add one or more user IDs\n\n"
            "<b>Example:</b>\n"
            "<code>/add_admin 1234567890 9876543210</code>",
            reply_markup=reply_markup
        )

    admin_list = ""
    for id in admins:
        try:
            id = int(id)
        except:
            admin_list += f"<blockquote><b>Invalid ID: <code>{id}</code></b></blockquote>\n"
            continue

        if id in admin_ids:
            admin_list += f"<blockquote><b>ID <code>{id}</code> already exists.</b></blockquote>\n"
            continue

        id = str(id)
        if id.isdigit() and len(id) == 10:
            admin_list += f"<b><blockquote>(ID: <code>{id}</code>) added.</blockquote></b>\n"
            check += 1
        else:
            admin_list += f"<blockquote><b>Invalid ID: <code>{id}</code></b></blockquote>\n"

    if check == len(admins):
        for id in admins:
            await db.add_admin(int(id))
        await pro.edit(f"<b>✅ Admin(s) added successfully:</b>\n\n{admin_list}", reply_markup=reply_markup)
    else:
        await pro.edit(
            f"<b>❌ Some errors occurred while adding admins:</b>\n\n{admin_list.strip()}\n\n"
            "<b><i>Please check and try again.</i></b>",
            reply_markup=reply_markup
        )


@Bot.on_message(filters.command('deladmin') & filters.private & filters.user(OWNER_ID))
async def delete_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    admin_ids = await db.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>Please provide valid admin ID(s) to remove.</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/deladmin [user_id]</code> — Remove specific IDs\n"
            "<code>/deladmin all</code> — Remove all admins",
            reply_markup=reply_markup
        )

    if len(admins) == 1 and admins[0].lower() == "all":
        if admin_ids:
            for id in admin_ids:
                await db.del_admin(id)
            ids = "\n".join(f"<blockquote><code>{admin}</code> ✅</blockquote>" for admin in admin_ids)
            return await pro.edit(f"<b>⛔️ All admin IDs have been removed:</b>\n{ids}", reply_markup=reply_markup)
        else:
            return await pro.edit("<b><blockquote>No admin IDs to remove.</blockquote></b>", reply_markup=reply_markup)

    if admin_ids:
        passed = ''
        for admin_id in admins:
            try:
                id = int(admin_id)
            except:
                passed += f"<blockquote><b>Invalid ID: <code>{admin_id}</code></b></blockquote>\n"
                continue

            if id in admin_ids:
                await db.del_admin(id)
                passed += f"<blockquote><code>{id}</code> ✅ Removed</blockquote>\n"
            else:
                passed += f"<blockquote><b>ID <code>{id}</code> not found in admin list.</b></blockquote>\n"

        await pro.edit(f"<b>⛔️ Admin removal result:</b>\n\n{passed}", reply_markup=reply_markup)
    else:
        await pro.edit("<b><blockquote>No admin IDs available to delete.</blockquote></b>", reply_markup=reply_markup)


@Bot.on_message(filters.command('admins') & filters.private & admin)
async def get_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    admin_ids = await db.get_all_admins()

    if not admin_ids:
        admin_list = "<b><blockquote>❌ No admins found.</blockquote></b>"
    else:
        admin_list = "\n".join(f"<b><blockquote>ID: <code>{id}</code></blockquote></b>" for id in admin_ids)

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])
    await pro.edit(f"<b>⚡ Current Admin List:</b>\n\n{admin_list}", reply_markup=reply_markup)


# ============================================================================
# /count — admin daily statistics dashboard
# ----------------------------------------------------------------------------
# All counts auto-reset every day at 00:00 IST via the scheduler in bot.py.
# Shows:
#   • Total successful shortener completions today
#   • Per-shortener breakdown (domain + success count)
#   • Premium users who visited today (unique count)
#   • Unique link accesses by premium users (no duplicates)
# ============================================================================
@Bot.on_message(filters.command('count') & filters.private & admin)
async def daily_count_dashboard(client: Client, message: Message):
    pro = await message.reply("<b><i>ꜰᴇᴛᴄʜɪɴɢ ᴅᴀɪʟʏ ꜱᴛᴀᴛꜱ...</i></b>", quote=True)

    try:
        stats = await db.get_today_stats()
    except Exception as e:
        return await pro.edit(f"<b>❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ʟᴏᴀᴅ ꜱᴛᴀᴛꜱ:</b>\n<code>{e}</code>")

    today = stats.get('_id', '')
    total_success = int(stats.get('total_success', 0) or 0)
    per_slot = stats.get('shortener_success', {}) or {}
    premium_users = stats.get('premium_users', []) or []
    premium_unique_links = int(stats.get('premium_unique_link_count', 0) or 0)
    bypass_attempts = int(stats.get('bypass_attempts', 0) or 0)

    try:
        ban_counts = await db.count_active_bypass_bans()
    except Exception:
        ban_counts = {'timed': 0, 'permanent': 0, 'total': 0}

    # Build per-shortener breakdown using the live config
    providers = SHORTLINK_PROVIDERS
    if not providers:
        per_slot_block = "<blockquote>» ɴᴏ ꜱʜᴏʀᴛᴇɴᴇʀꜱ ᴄᴏɴꜰɪɢᴜʀᴇᴅ.</blockquote>"
    else:
        lines = []
        for i, p in enumerate(providers):
            domain = p.get('url', '—')
            count = int(per_slot.get(str(i), 0) or 0)
            lines.append(
                f"<blockquote>» <b>#{i+1}</b> <code>{domain}</code> "
                f"→ <b>{count}</b> ꜱᴜᴄᴄᴇꜱꜱ</blockquote>"
            )
        per_slot_block = "\n".join(lines)

    text = (
        f"<b>📊 ᴅᴀɪʟʏ ᴄᴏᴜɴᴛ ᴅᴀꜱʜʙᴏᴀʀᴅ</b>\n"
        f"<blockquote>» ᴅᴀᴛᴇ (ɪꜱᴛ): <b>{today}</b></blockquote>\n"
        f"<blockquote>» ʀᴇꜱᴇᴛꜱ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴀᴛ <b>00:00 ɪꜱᴛ</b></blockquote>\n\n"
        f"<b>✅ ᴛᴏᴛᴀʟ ᴄᴏᴍᴘʟᴇᴛɪᴏɴꜱ</b>\n"
        f"<blockquote>» <b>{total_success}</b> ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴꜱ ᴛᴏᴅᴀʏ</blockquote>\n\n"
        f"<b>🔗 ᴘᴇʀ-ꜱʜᴏʀᴛᴇɴᴇʀ ʙʀᴇᴀᴋᴅᴏᴡɴ</b>\n"
        f"{per_slot_block}\n\n"
        f"<b>💎 ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠɪᴛʏ</b>\n"
        f"<blockquote>» ᴜɴɪQᴜᴇ ᴠɪꜱɪᴛᴇᴅ: <b>{len(premium_users)}</b></blockquote>\n"
        f"<blockquote>» ᴜɴɪQᴜᴇ ʟɪɴᴋꜱ ᴀᴄᴄᴇꜱꜱ: <b>{premium_unique_links}</b></blockquote>\n\n"
        f"<b>🛡️ ʙʏᴘᴀꜱꜱ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ</b>\n"
        f"<blockquote>» ᴀᴛᴛᴇᴍᴘᴛꜱ ᴛᴏᴅᴀʏ: <b>{bypass_attempts}</b></blockquote>\n"
        f"<blockquote>» ᴄᴜʀʀᴇɴᴛʟʏ ʙᴀɴɴᴇᴅ: <b>{ban_counts['total']}</b> "
        f"(ᴛɪᴍᴇᴅ <b>{ban_counts['timed']}</b> + ᴘᴇʀᴍᴀ <b>{ban_counts['permanent']}</b>)</blockquote>"
    )

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])
    await pro.edit(text, reply_markup=reply_markup)
