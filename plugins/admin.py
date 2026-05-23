import asyncio
import os
import sys
import time
from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus, ChatType
from pyrogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                             CallbackQuery, ChatMemberUpdated, ChatPermissions)
from pyrogram.errors.exceptions.bad_request_400 import (
    UserNotParticipant, InviteHashEmpty, ChatAdminRequired,
    PeerIdInvalid, UserIsBlocked, InputUserDeactivated
)
from bot import Bot
from config import *
from helper_func import *
from database.database import *


# ═══════════════════════════════════════════════════════════
# /ichannel — set which channel to generate per-user invite links for
# ═══════════════════════════════════════════════════════════
@Bot.on_message(filters.command('ichannel') & filters.private & admin)
async def set_invite_channel_cmd(client: Client, message: Message):
    """
    Usage: /ichannel <channel_id>
    Sets the channel the bot will create unique per-user invite links for
    when invite mode is set to 'channel' in the /hash panel.

    Requirements:
    • Bot must be an admin in that channel with 'Invite Users' permission.
    • Switch invite mode to 'Channel Link' from /hash to activate.
    """
    parts = message.text.split()
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close")]])

    if len(parts) < 2:
        current_channel_id = await db.get_invite_channel()
        current_mode = await db.get_invite_link_mode()
        mode_label = "🔗 ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ" if current_mode == "channel" else "🤖 ʙᴏᴛ ʟɪɴᴋ"

        if current_channel_id:
            try:
                ch = await client.get_chat(current_channel_id)
                ch_name = ch.title
            except Exception:
                ch_name = str(current_channel_id)
            current_str = f"<b>{ch_name}</b> (<code>{current_channel_id}</code>)"
        else:
            current_str = "<i>ɴᴏᴛ sᴇᴛ</i>"

        return await message.reply(
            f"<blockquote>🔗 <b>ɪɴᴠɪᴛᴇ ʟɪɴᴋ ᴄʜᴀɴɴᴇʟ sᴇᴛᴛɪɴɢ</b></blockquote>\n\n"
            f"<blockquote>» ᴄᴜʀʀᴇɴᴛ ᴄʜᴀɴɴᴇʟ: {current_str}</blockquote>\n"
            f"<blockquote>» ᴄᴜʀʀᴇɴᴛ ᴍᴏᴅᴇ: {mode_label}</blockquote>\n\n"
            f"<b>ᴜsᴀɢᴇ:</b> <code>/ichannel -100xxxxxxxxxx</code>\n\n"
            f"<blockquote expandable>ɴᴏᴛᴇ: sᴡɪᴛᴄʜ ᴛᴏ <b>ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ</b> ᴍᴏᴅᴇ ᴠɪᴀ /ʜᴀsʜ ᴛᴏ ᴀᴄᴛɪᴠᴀᴛᴇ ᴘᴇʀ-ᴜsᴇʀ ᴄʜᴀɴɴᴇʟ ɪɴᴠɪᴛᴇ ʟɪɴᴋs.\n"
            f"ʙᴏᴛ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴡɪᴛʜ ᴛʜᴇ \"ɪɴᴠɪᴛᴇ ᴜsᴇʀs\" ᴘᴇʀᴍɪssɪᴏɴ.</blockquote>",
            reply_markup=reply_markup
        )

    try:
        channel_id = int(parts[1])
    except ValueError:
        return await message.reply(
            "<b>❌ ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ.</b>\n\n"
            "ᴄʜᴀɴɴᴇʟ ɪᴅs ᴀʀᴇ ɴᴇɢᴀᴛɪᴠᴇ ɪɴᴛᴇɢᴇʀs, ᴇ.ɢ. <code>-1001234567890</code>",
            reply_markup=reply_markup
        )

    # Verify we can access the channel and have invite permission
    try:
        ch = await client.get_chat(channel_id)
        ch_name = ch.title
    except Exception as e:
        return await message.reply(
            f"<b>❌ ᴄᴀɴɴᴏᴛ ᴀᴄᴄᴇss ᴄʜᴀɴɴᴇʟ <code>{channel_id}</code></b>\n\n"
            f"<blockquote>ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ.</blockquote>\n"
            f"<blockquote expandable>ᴇʀʀᴏʀ: {e}</blockquote>",
            reply_markup=reply_markup
        )

    # Test invite link creation to confirm bot has the permission
    try:
        test_invite = await client.create_chat_invite_link(
            chat_id=channel_id,
            name="permission_test",
        )
        # Immediately revoke test link — it was just a permission check
        await client.revoke_chat_invite_link(channel_id, test_invite.invite_link)
    except Exception as e:
        return await message.reply(
            f"<b>❌ ʙᴏᴛ ᴄᴀɴɴᴏᴛ ᴄʀᴇᴀᴛᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋs ɪɴ <b>{ch_name}</b></b>\n\n"
            f"<blockquote>ᴘʟᴇᴀsᴇ ɢʀᴀɴᴛ ᴛʜᴇ ʙᴏᴛ ᴛʜᴇ <b>\"ɪɴᴠɪᴛᴇ ᴜsᴇʀs\"</b> ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ.</blockquote>\n"
            f"<blockquote expandable>ᴇʀʀᴏʀ: {e}</blockquote>",
            reply_markup=reply_markup
        )

    await db.set_invite_channel(channel_id)
    current_mode = await db.get_invite_link_mode()
    mode_label = "🔗 ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ" if current_mode == "channel" else "🤖 ʙᴏᴛ ʟɪɴᴋ (ᴄʜᴀɴɢᴇ ᴠɪᴀ /ʜᴀsʜ ᴛᴏ ᴀᴄᴛɪᴠᴀᴛᴇ)"

    await message.reply(
        f"<blockquote>✅ <b>ɪɴᴠɪᴛᴇ ᴄʜᴀɴɴᴇʟ sᴇᴛ</b></blockquote>\n\n"
        f"<blockquote>» ᴄʜᴀɴɴᴇʟ: <b>{ch_name}</b> (<code>{channel_id}</code>)</blockquote>\n"
        f"<blockquote>» ᴍᴏᴅᴇ: {mode_label}</blockquote>\n\n"
        f"<blockquote expandable>ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ɴᴏᴡ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ᴜɴɪQᴜᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ ꜰᴏʀ ᴛʜɪs ᴄʜᴀɴɴᴇʟ ꜰᴏʀ ᴇᴀᴄʜ ᴜsᴇʀ ᴡʜᴏ ᴏᴘᴇɴs ᴛʜᴇɪʀ ɪɴᴠɪᴛᴇ ᴅᴀsʜʙᴏᴀʀᴅ (🎁 ꜰʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ).\n"
        f"ᴇᴀᴄʜ ʟɪɴᴋ ɪs ɴᴀᴍᴇᴅ \"ʀᴇꜰ_<ᴜsᴇʀ_ɪᴅ>\" ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ɪɴᴠɪᴛᴇ ʟɪɴᴋs ᴘᴀɴᴇʟ ꜰᴏʀ ᴇᴀsʏ ᴛʀᴀᴄᴋɪɴɢ.</blockquote>",
        reply_markup=reply_markup
    )


# ═══════════════════════════════════════════════════════════
# /add_admin — add admins (owner only)
# ═══════════════════════════════════════════════════════════
@Bot.on_message(filters.command('add_admin') & filters.private & filters.user(OWNER_ID))
async def add_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    check = 0
    admin_ids = await db.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴘʀᴏᴠɪᴅᴇ ᴜsᴇʀ ɪᴅ(s) ᴛᴏ ᴀᴅᴅ ᴀs ᴀᴅᴍɪɴ.</b>\n\n"
            "<b>ᴜsᴀɢᴇ:</b>\n"
            "<code>/add_admin [user_id]</code>\n\n"
            "<b>ᴇxᴀᴍᴘʟᴇ:</b>\n"
            "<code>/add_admin 1234567890 9876543210</code>",
            reply_markup=reply_markup
        )

    admin_list = ""
    for id in admins:
        try:
            id = int(id)
        except Exception:
            admin_list += f"<blockquote><b>ɪɴᴠᴀʟɪᴅ ɪᴅ: <code>{id}</code></b></blockquote>\n"
            continue

        if id in admin_ids:
            admin_list += f"<blockquote><b>ɪᴅ <code>{id}</code> ᴀʟʀᴇᴀᴅʏ ᴇxɪsᴛs.</b></blockquote>\n"
            continue

        await db.add_admin(id)
        admin_list += f"<b><blockquote>ɪᴅ <code>{id}</code> ᴀᴅᴅᴇᴅ.</blockquote></b>\n"
        check += 1

    await pro.edit(
        f"<b>✅ ᴀᴅᴍɪɴ(s) ᴜᴘᴅᴀᴛᴇᴅ:</b>\n\n{admin_list}",
        reply_markup=reply_markup
    )


# ═══════════════════════════════════════════════════════════
# /deladmin — remove admins (owner only)
# ═══════════════════════════════════════════════════════════
@Bot.on_message(filters.command('deladmin') & filters.private & filters.user(OWNER_ID))
async def delete_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    admin_ids = await db.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴠᴀʟɪᴅ ᴀᴅᴍɪɴ ɪᴅ(s) ᴛᴏ ʀᴇᴍᴏᴠᴇ.</b>\n\n"
            "<b>ᴜsᴀɢᴇ:</b>\n"
            "<code>/deladmin [user_id]</code>\n"
            "<code>/deladmin all</code> — ʀᴇᴍᴏᴠᴇ ᴀʟʟ ᴀᴅᴍɪɴs",
            reply_markup=reply_markup
        )

    if len(admins) == 1 and admins[0].lower() == "all":
        if admin_ids:
            for id in admin_ids:
                await db.del_admin(id)
            ids = "\n".join(f"<blockquote><code>{a}</code> ✅</blockquote>" for a in admin_ids)
            return await pro.edit(f"<b>⛔️ ᴀʟʟ ᴀᴅᴍɪɴs ʀᴇᴍᴏᴠᴇᴅ:</b>\n{ids}", reply_markup=reply_markup)
        else:
            return await pro.edit("<b><blockquote>ɴᴏ ᴀᴅᴍɪɴs ᴛᴏ ʀᴇᴍᴏᴠᴇ.</blockquote></b>", reply_markup=reply_markup)

    if admin_ids:
        passed = ''
        for admin_id in admins:
            try:
                id = int(admin_id)
            except Exception:
                passed += f"<blockquote><b>ɪɴᴠᴀʟɪᴅ ɪᴅ: <code>{admin_id}</code></b></blockquote>\n"
                continue

            if id in admin_ids:
                await db.del_admin(id)
                passed += f"<blockquote><code>{id}</code> ✅ ʀᴇᴍᴏᴠᴇᴅ</blockquote>\n"
            else:
                passed += f"<blockquote><b>ɪᴅ <code>{id}</code> ɴᴏᴛ ꜰᴏᴜɴᴅ ɪɴ ᴀᴅᴍɪɴ ʟɪsᴛ.</b></blockquote>\n"

        await pro.edit(f"<b>⛔️ ᴀᴅᴍɪɴ ʀᴇᴍᴏᴠᴀʟ ʀᴇsᴜʟᴛ:</b>\n\n{passed}", reply_markup=reply_markup)
    else:
        await pro.edit("<b><blockquote>ɴᴏ ᴀᴅᴍɪɴ ɪᴅs ᴀᴠᴀɪʟᴀʙʟᴇ ᴛᴏ ᴅᴇʟᴇᴛᴇ.</blockquote></b>", reply_markup=reply_markup)


# ═══════════════════════════════════════════════════════════
# /admins — list all admins
# ═══════════════════════════════════════════════════════════
@Bot.on_message(filters.command('admins') & filters.private & admin)
async def get_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..</i></b>", quote=True)
    admin_ids = await db.get_all_admins()

    if not admin_ids:
        admin_list = "<b><blockquote>❌ ɴᴏ ᴀᴅᴍɪɴs ꜰᴏᴜɴᴅ.</blockquote></b>"
    else:
        admin_list = "\n".join(f"<b><blockquote>ɪᴅ: <code>{id}</code></blockquote></b>" for id in admin_ids)

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])
    await pro.edit(f"<b>⚡ ᴄᴜʀʀᴇɴᴛ ᴀᴅᴍɪɴ ʟɪsᴛ:</b>\n\n{admin_list}", reply_markup=reply_markup)


# ═══════════════════════════════════════════════════════════
# /count — daily statistics dashboard
# ═══════════════════════════════════════════════════════════
@Bot.on_message(filters.command('count') & filters.private & admin)
async def daily_count_dashboard(client: Client, message: Message):
    pro = await message.reply("<b><i>ꜰᴇᴛᴄʜɪɴɢ ᴅᴀɪʟʏ sᴛᴀᴛs...</i></b>", quote=True)

    try:
        stats = await db.get_today_stats()
    except Exception as e:
        return await pro.edit(f"<b>❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ʟᴏᴀᴅ sᴛᴀᴛs:</b>\n<code>{e}</code>")

    today = stats.get('_id', '')
    total_success = int(stats.get('total_success', 0) or 0)
    per_slot = stats.get('shortener_success', {}) or {}
    premium_users = stats.get('premium_users', []) or []
    premium_unique_links = int(stats.get('premium_unique_link_count', 0) or 0)
    bypass_attempts = int(stats.get('bypass_attempts', 0) or 0)
    channel_joined_today = stats.get('channel_joined_today', []) or []

    try:
        ban_counts = await db.count_active_bypass_bans()
    except Exception:
        ban_counts = {'timed': 0, 'permanent': 0, 'total': 0}

    # Per-shortener breakdown
    providers = SHORTLINK_PROVIDERS
    if not providers:
        per_slot_block = "<blockquote>» ɴᴏ sʜᴏʀᴛᴇɴᴇʀs ᴄᴏɴꜰɪɢᴜʀᴇᴅ.</blockquote>"
    else:
        lines = []
        for i, p in enumerate(providers):
            domain = p.get('url', '—')
            count = int(per_slot.get(str(i), 0) or 0)
            lines.append(
                f"<blockquote>» <b>#{i+1}</b> <code>{domain}</code> "
                f"→ <b>{count}</b> sᴜᴄᴄᴇss</blockquote>"
            )
        per_slot_block = "\n".join(lines)

    text = (
        f"<b>📊 ᴅᴀɪʟʏ ᴄᴏᴜɴᴛ ᴅᴀsʜʙᴏᴀʀᴅ</b>\n"
        f"<blockquote>» ᴅᴀᴛᴇ (ɪsᴛ): <b>{today}</b></blockquote>\n"
        f"<blockquote>» ᴀᴜᴛᴏ-ʀᴇsᴇᴛs ᴀᴛ <b>00:00 ɪsᴛ</b></blockquote>\n\n"

        f"<b>👥 ᴄʜᴀɴɴᴇʟ ᴊᴏɪɴs</b>\n"
        f"<blockquote>» ɴᴇᴡ ᴜsᴇʀs ᴛᴏᴅᴀʏ: <b>{len(channel_joined_today)}</b></blockquote>\n\n"

        f"<b>✅ sʜᴏʀᴛ-ʟɪɴᴋ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴs</b>\n"
        f"<blockquote>» ᴛᴏᴛᴀʟ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛᴏᴅᴀʏ: <b>{total_success}</b></blockquote>\n\n"

        f"<b>🔗 ᴘᴇʀ-sʜᴏʀᴛᴇɴᴇʀ ʙʀᴇᴀᴋᴅᴏᴡɴ</b>\n"
        f"{per_slot_block}\n\n"

        f"<b>💎 ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠɪᴛʏ</b>\n"
        f"<blockquote>» ᴜɴɪǫᴜᴇ ᴠɪsɪᴛᴇᴅ: <b>{len(premium_users)}</b></blockquote>\n"
        f"<blockquote>» ᴜɴɪǫᴜᴇ ʟɪɴᴋs ᴀᴄᴄᴇssᴇᴅ: <b>{premium_unique_links}</b></blockquote>\n\n"

        f"<b>🛡️ ʙʏᴘᴀss ᴘʀᴏᴛᴇᴄᴛɪᴏɴ</b>\n"
        f"<blockquote>» ᴀᴛᴛᴇᴍᴘᴛs ᴛᴏᴅᴀʏ: <b>{bypass_attempts}</b></blockquote>\n"
        f"<blockquote>» ᴄᴜʀʀᴇɴᴛʟʏ ʙᴀɴɴᴇᴅ: <b>{ban_counts['total']}</b> "
        f"(ᴛɪᴍᴇᴅ <b>{ban_counts['timed']}</b> + ᴘᴇʀᴍᴀ <b>{ban_counts['permanent']}</b>)</blockquote>"
    )

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]])
    await pro.edit(text, reply_markup=reply_markup)
