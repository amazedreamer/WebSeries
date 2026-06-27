#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
import io
import re as _re
import time
import urllib.parse
import qrcode
import qrcode.constants

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


# ── Dynamic UPI QR Code Generator ────────────────────────────────────────────
def _generate_upi_qr(amount: int, user_id: int) -> tuple:
    """
    Generate a dynamic UPI QR code for the given amount.

    The QR encodes a UPI deep link:
      upi://pay?pa=<UPI_ID>&pn=<PAYEE>&am=<AMOUNT>&cu=INR&tn=<REF>

    This works with ALL UPI apps (Paytm, GPay, PhonePe, BHIM, etc.).
    The amount is pre-filled so the user cannot change it.

    Returns (BytesIO image, ref_id string).
    """
    ref_id = f"PMT{user_id}{int(time.time())}"
    upi_url = (
        f"upi://pay"
        f"?pa={UPI_ID}"
        f"&pn={urllib.parse.quote(UPI_PAYEE_NAME)}"
        f"&am={amount}"
        f"&cu=INR"
        f"&tn={urllib.parse.quote(f'Premium {ref_id}')}"
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    bio = io.BytesIO()
    bio.name = "paytm_qr.png"
    img.save(bio, format="PNG")
    bio.seek(0)

    return bio, ref_id


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

    # ── Buy Premium — Step 3: show dynamic Paytm QR for exact plan amount ─────
    elif data.startswith("plan_select_"):
        plan_key = data[len("plan_select_"):]
        plan = _plan_key_to_info(plan_key)
        if not plan:
            await query.answer("ɪɴᴠᴀʟɪᴅ ᴘʟᴀɴ.", show_alert=True)
            return

        amount = parse_price_amount(plan['price_str'])
        plan_type_str = "sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ" if plan_key.startswith("sp") else "ɴᴏʀᴍᴀʟ ᴘʀᴇᴍɪᴜᴍ"

        await query.answer("ɢᴇɴᴇʀᴀᴛɪɴɢ ᴘᴀʏᴍᴇɴᴛ ǫʀ...")

        # ── Generate dynamic UPI QR code for this exact plan amount ────────
        try:
            qr_bio, ref_id = _generate_upi_qr(amount, query.from_user.id)
        except Exception as qr_err:
            print(f"[cbb] QR generation failed: {qr_err}")
            await query.answer("QR ɢᴇɴᴇʀᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ. ᴛʀʏ ᴀɢᴀɪɴ.", show_alert=True)
            return

        caption = (
            f"<blockquote>💳 <b>ᴘᴀʏᴍᴇɴᴛ ᴅᴇᴛᴀɪʟs</b></blockquote>\n\n"
            f"<blockquote>» ᴘʟᴀɴ: <b>{plan_type_str}</b></blockquote>\n"
            f"<blockquote>» ᴅᴜʀᴀᴛɪᴏɴ: <b>{plan['label']}</b></blockquote>\n"
            f"<blockquote>» ᴀᴍᴏᴜɴᴛ: <b>₹{amount}</b></blockquote>\n\n"
            f"<blockquote>📱 sᴄᴀɴ ᴛʜɪs ᴅʏɴᴀᴍɪᴄ ǫʀ ᴄᴏᴅᴇ ᴡɪᴛʜ ᴀɴʏ ᴜᴘɪ ᴀᴘᴘ.\n"
            f"ᴛʜᴇ ᴀᴍᴏᴜɴᴛ ₹{amount} ɪs ᴘʀᴇ-ꜰɪʟʟᴇᴅ — ᴅᴏ ɴᴏᴛ ᴄʜᴀɴɢᴇ ɪᴛ.</blockquote>\n"
            f"<blockquote>» ᴜᴘɪ ɪᴅ: <code>{UPI_ID}</code>\n"
            f"» ᴘᴀʏᴇᴇ: <b>{UPI_PAYEE_NAME}</b></blockquote>\n\n"
            f"<blockquote expandable>📝 ɪɴsᴛʀᴜᴄᴛɪᴏɴs:\n"
            f"1️⃣ sᴄᴀɴ ǫʀ ᴄᴏᴅᴇ & ᴘᴀʏ ᴇxᴀᴄᴛʟʏ ₹{amount}.\n"
            f"2️⃣ ᴄʟɪᴄᴋ <b>ᴘᴀʏᴍᴇɴᴛ ᴅᴏɴᴇ</b> ᴀꜰᴛᴇʀ ᴘᴀʏɪɴɢ.\n"
            f"3️⃣ sᴇɴᴅ ʏᴏᴜʀ <b>ᴜᴘɪ ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ɪᴅ / ᴜᴛʀ</b> ɴᴜᴍʙᴇʀ.\n"
            f"4️⃣ ᴏᴜʀ ᴛᴇᴀᴍ ᴡɪʟʟ ᴠᴇʀɪꜰʏ & ᴀᴄᴛɪᴠᴀᴛᴇ ʏᴏᴜʀ ᴘʟᴀɴ ꜱᴏᴏɴ.</blockquote>"
        )

        try:
            await query.message.delete()
        except Exception:
            pass

        try:
            sent = await client.send_photo(
                chat_id=query.message.chat.id,
                photo=qr_bio,
                caption=caption,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"✅ ᴘᴀʏᴍᴇɴᴛ ᴅᴏɴᴇ", callback_data=f"pmt_done_{plan_key}")],
                    [
                        InlineKeyboardButton("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url=f"https://t.me/{OWNER_TAG}"),
                        InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="premium"),
                    ],
                    [InlineKeyboardButton("✖️ ᴄʟᴏsᴇ", callback_data="close")],
                ]),
            )
            asyncio.create_task(_autodelete_after(
                client, sent.chat.id, sent.id, PREMIUM_MSG_AUTO_DELETE_SECONDS
            ))
        except Exception as e:
            print(f"[cbb] plan_select send_photo failed: {e}")
            await query.answer("ᴄᴏᴜʟᴅ ɴᴏᴛ ʟᴏᴀᴅ ᴘᴀʏᴍᴇɴᴛ ɪɴꜰᴏ. ᴛʀʏ ᴀɢᴀɪɴ.", show_alert=True)

    # ── Payment Done — collect UTR then forward to admin ─────────────────────
    elif data.startswith("pmt_done_"):
        plan_key = data[len("pmt_done_"):]
        plan = _plan_key_to_info(plan_key)
        user_id = query.from_user.id

        if not plan:
            await query.answer("ɪɴᴠᴀʟɪᴅ ᴘʟᴀɴ.", show_alert=True)
            return

        amount = parse_price_amount(plan['price_str'])
        plan_type_str = "Super Premium" if plan_key.startswith("sp") else "Normal Premium"
        plan_label = plan['label']

        # Check for duplicate pending request
        existing = await db.get_payment_request(user_id)
        if existing and existing.get('status') == 'pending':
            await query.answer(
                "ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ʜᴀᴠᴇ ᴀ ᴘᴇɴᴅɪɴɢ ᴘᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ. ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ꜰᴏʀ ᴀᴘᴘʀᴏᴠᴀʟ.",
                show_alert=True
            )
            return

        await query.answer("ᴘʟᴇᴀsᴇ sᴇɴᴅ ʏᴏᴜʀ ᴜᴛʀ ɴᴜᴍʙᴇʀ...", show_alert=False)

        # ── Delete the QR message ────────────────────────────────────────────
        try:
            await query.message.delete()
        except Exception:
            pass

        # ── Ask user to provide UPI Transaction Reference (UTR) ──────────────
        ask_msg = None
        try:
            ask_msg = await client.send_message(
                chat_id=user_id,
                text=(
                    f"<blockquote>📋 <b>ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴜᴛʀ ɴᴜᴍʙᴇʀ</b></blockquote>\n\n"
                    f"<blockquote>ᴘʟᴇᴀsᴇ sᴇɴᴅ ʏᴏᴜʀ <b>ᴜᴘɪ ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ʀᴇꜰᴇʀᴇɴᴄᴇ (ᴜᴛʀ)</b> ɴᴜᴍʙᴇʀ.</blockquote>\n\n"
                    f"<blockquote expandable>ʜᴏᴡ ᴛᴏ ꜰɪɴᴅ ᴜᴛʀ:\n"
                    f"• <b>Paytm</b> → ʜɪsᴛᴏʀʏ → ᴛᴀᴘ ᴛʀᴀɴsᴀᴄᴛɪᴏɴ → ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ɪᴅ\n"
                    f"• <b>GPay / PhonePe</b> → ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ʜɪsᴛᴏʀʏ → ᴜᴛʀ ɴᴜᴍʙᴇʀ\n"
                    f"• ᴇxᴀᴍᴘʟᴇ: <code>T2506271234567890</code></blockquote>\n\n"
                    f"<blockquote>⏳ ʏᴏᴜ ʜᴀᴠᴇ <b>3 ᴍɪɴᴜᴛᴇs</b> ᴛᴏ sᴇɴᴅ ᴛʜᴇ ᴜᴛʀ.</blockquote>"
                ),
            )
        except Exception as ask_err:
            print(f"[cbb] pmt_done: ask_msg failed: {ask_err}")

        # ── Wait for UTR via pyromod listen ───────────────────────────────────
        utr_text = "ɴᴏᴛ ᴘʀᴏᴠɪᴅᴇᴅ"
        try:
            utr_response = await client.listen(user_id, timeout=180)
            if utr_response and utr_response.text:
                utr_text = utr_response.text.strip()[:100]  # cap at 100 chars
        except asyncio.TimeoutError:
            utr_text = "ᴛɪᴍᴇᴅ ᴏᴜᴛ"
        except Exception as listen_err:
            print(f"[cbb] pmt_done: listen failed: {listen_err}")

        # Delete the "ask" message
        if ask_msg:
            try:
                await ask_msg.delete()
            except Exception:
                pass

        # ── Create payment request in DB ─────────────────────────────────────
        plan_type_db = "super" if plan_key.startswith("sp") else "normal"
        await db.create_payment_request(
            user_id=user_id,
            plan_key=plan_key,
            plan_type=plan_type_db,
            days=plan['days'],
            amount=amount,
        )

        # ── Store UTR separately ─────────────────────────────────────────────
        try:
            await db.payment_requests.update_one(
                {'_id': user_id},
                {'$set': {'utr': utr_text}}
            )
        except Exception as utr_err:
            print(f"[cbb] UTR store failed: {utr_err}")

        # ── Notify user ───────────────────────────────────────────────────────
        try:
            await client.send_message(
                chat_id=user_id,
                text=(
                    f"<blockquote>⏳ <b>ᴘᴀʏᴍᴇɴᴛ ᴜɴᴅᴇʀ ʀᴇᴠɪᴇᴡ</b></blockquote>\n\n"
                    f"<blockquote>ᴘʟᴀɴ: <b>{plan_type_str} — {plan_label}</b> (₹{amount})</blockquote>\n"
                    f"<blockquote>ᴜᴛʀ: <code>{utr_text}</code></blockquote>\n\n"
                    f"<blockquote>✅ ᴡᴇ ᴡɪʟʟ ᴠᴇʀɪꜰʏ ᴀɴᴅ ᴀᴄᴛɪᴠᴀᴛᴇ ʏᴏᴜʀ ᴘʟᴀɴ sᴏᴏɴ. 🙏</blockquote>"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url=f"https://t.me/{OWNER_TAG}")],
                ])
            )
        except Exception:
            pass

        # ── Notify all admins + owner (including UTR) ─────────────────────────
        user_mention = query.from_user.mention
        username_str = f"@{query.from_user.username}" if query.from_user.username else "ɴ/ᴀ"
        admin_text = (
            f"<blockquote>💰 <b>ɴᴇᴡ ᴘᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ</b></blockquote>\n\n"
            f"<blockquote>» ᴜsᴇʀ: {user_mention} ({username_str})</blockquote>\n"
            f"<blockquote>» ɪᴅ: <code>{user_id}</code></blockquote>\n"
            f"<blockquote>» ᴘʟᴀɴ: <b>{plan_type_str} — {plan_label}</b></blockquote>\n"
            f"<blockquote>» ᴀᴍᴏᴜɴᴛ: <b>₹{amount}</b></blockquote>\n"
            f"<blockquote>» ᴜᴘɪ ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ɪᴅ (ᴜᴛʀ): <code>{utr_text}</code></blockquote>\n\n"
            f"<blockquote>ᴠᴇʀɪꜰʏ ᴛʜɪs ᴜᴛʀ ɪɴ ʏᴏᴜʀ Paytm ᴍᴇʀᴄʜᴀɴᴛ ᴅᴀsʜʙᴏᴀʀᴅ, ᴛʜᴇɴ ᴀᴘᴘʀᴏᴠᴇ ᴏʀ ʀᴇᴊᴇᴄᴛ.</blockquote>"
        )
        admin_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"✅ ᴀᴘᴘʀᴏᴠᴇ", callback_data=f"pmt_ok_{user_id}"),
                InlineKeyboardButton(f"❌ ʀᴇᴊᴇᴄᴛ", callback_data=f"pmt_no_{user_id}"),
            ]
        ])

        # Send to owner
        try:
            sent_owner = await client.send_message(
                chat_id=OWNER_ID,
                text=admin_text,
                reply_markup=admin_markup,
            )
            await db.add_admin_msg_to_payment(user_id, OWNER_ID, sent_owner.id)
        except Exception as oe:
            print(f"[cbb] pmt_done: notify owner failed: {oe}")

        # Send to all admins
        admin_ids = await db.get_all_admins()
        for aid in admin_ids:
            if aid == OWNER_ID:
                continue
            try:
                sent_adm = await client.send_message(
                    chat_id=aid,
                    text=admin_text,
                    reply_markup=admin_markup,
                )
                await db.add_admin_msg_to_payment(user_id, aid, sent_adm.id)
            except Exception:
                pass

    # ── Admin: Approve payment ────────────────────────────────────────────────
    elif data.startswith("pmt_ok_"):
        target_uid = int(data[len("pmt_ok_"):])
        approver_id = query.from_user.id

        req = await db.get_payment_request(target_uid)
        if not req:
            await query.answer("ᴘᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ ɴᴏᴛ ꜰᴏᴜɴᴅ ᴏʀ ᴀʟʀᴇᴀᴅʏ ᴘʀᴏᴄᴇssᴇᴅ.", show_alert=True)
            return
        if req.get('status') != 'pending':
            await query.answer(f"ᴛʜɪs ʀᴇǫᴜᴇsᴛ ᴡᴀs ᴀʟʀᴇᴀᴅʏ {req.get('status', 'processed')}.", show_alert=True)
            return

        # Activate plan
        plan_type = req.get('plan_type', 'normal')
        days = int(req.get('days', 0))
        plan_key = req.get('plan_key', '')
        plan = _plan_key_to_info(plan_key)
        plan_label = plan['label'] if plan else f"{days} ᴅᴀʏs"
        plan_type_str = "Super Premium" if plan_type == "super" else "Normal Premium"
        utr_stored = req.get('utr', 'ɴ/ᴀ')

        if plan_type == "super":
            from database.db_premium import add_super_premium
            expiry = await add_super_premium(target_uid, days)
        else:
            expiry = await add_premium(target_uid, days, 'd')

        await db.update_payment_request_status(target_uid, 'approved', approved_by=approver_id)

        await query.answer("✅ ᴀᴘᴘʀᴏᴠᴇᴅ — ᴘʟᴀɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!", show_alert=False)

        # Edit ALL admin notification messages
        resolved_text = (
            f"<blockquote>✅ <b>ᴘᴀʏᴍᴇɴᴛ ᴀᴘᴘʀᴏᴠᴇᴅ</b></blockquote>\n\n"
            f"<blockquote>» ᴜsᴇʀ ɪᴅ: <code>{target_uid}</code></blockquote>\n"
            f"<blockquote>» ᴘʟᴀɴ: <b>{plan_type_str} — {plan_label}</b></blockquote>\n"
            f"<blockquote>» ᴜᴛʀ: <code>{utr_stored}</code></blockquote>\n"
            f"<blockquote>» ᴀᴘᴘʀᴏᴠᴇᴅ ʙʏ: <code>{approver_id}</code></blockquote>\n"
            f"<blockquote>» ᴇxᴘɪʀᴇs: <code>{expiry}</code></blockquote>"
        )
        for entry in req.get('admin_msg_ids', []):
            try:
                admin_id, msg_id = entry[0], entry[1]
                await client.edit_message_text(
                    chat_id=admin_id,
                    message_id=msg_id,
                    text=resolved_text,
                )
            except Exception:
                pass

        # Activate message to user + pin it
        plan_emoji = "🚀" if plan_type == "super" else "💎"
        user_text = (
            f"<blockquote>{plan_emoji} <b>ᴘʟᴀɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</b></blockquote>\n\n"
            f"<blockquote>ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs! ʏᴏᴜʀ <b>{plan_type_str}</b> ᴘʟᴀɴ ɪs ɴᴏᴡ ᴀᴄᴛɪᴠᴇ.</blockquote>\n"
            f"<blockquote>» ᴅᴜʀᴀᴛɪᴏɴ: <b>{plan_label}</b></blockquote>\n"
            f"<blockquote>» ᴇxᴘɪʀᴇs: <code>{expiry}</code></blockquote>\n\n"
            f"<blockquote>✅ ᴇɴᴊᴏʏ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss. ᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ! 🙏</blockquote>"
        )
        try:
            sent_user_msg = await client.send_message(
                chat_id=target_uid,
                text=user_text,
            )
            try:
                await client.pin_chat_message(
                    chat_id=target_uid,
                    message_id=sent_user_msg.id,
                    disable_notification=False,
                )
            except Exception:
                pass
        except Exception as ue:
            print(f"[cbb] pmt_ok: notify user failed: {ue}")

        # If this user was referred, count as plan_bought validation
        try:
            ref_id = await db.mark_referral_plan_bought(target_uid)
            if ref_id > 0:
                from plugins.start import _handle_referral_validation
                await _handle_referral_validation(client, target_uid)
        except Exception:
            pass

    # ── Admin: Reject payment ─────────────────────────────────────────────────
    elif data.startswith("pmt_no_"):
        target_uid = int(data[len("pmt_no_"):])
        rejecter_id = query.from_user.id

        req = await db.get_payment_request(target_uid)
        if not req:
            await query.answer("ᴘᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ ɴᴏᴛ ꜰᴏᴜɴᴅ ᴏʀ ᴀʟʀᴇᴀᴅʏ ᴘʀᴏᴄᴇssᴇᴅ.", show_alert=True)
            return
        if req.get('status') != 'pending':
            await query.answer(f"ᴛʜɪs ʀᴇǫᴜᴇsᴛ ᴡᴀs ᴀʟʀᴇᴀᴅʏ {req.get('status', 'processed')}.", show_alert=True)
            return

        await db.update_payment_request_status(target_uid, 'rejected', approved_by=rejecter_id)
        await query.answer("❌ ʀᴇᴊᴇᴄᴛᴇᴅ.", show_alert=False)

        plan_key = req.get('plan_key', '')
        plan = _plan_key_to_info(plan_key)
        plan_label = plan['label'] if plan else f"{req.get('days', '?')} ᴅᴀʏs"
        plan_type_str = "Super Premium" if req.get('plan_type') == "super" else "Normal Premium"
        utr_stored = req.get('utr', 'ɴ/ᴀ')

        # Edit all admin messages
        resolved_text = (
            f"<blockquote>❌ <b>ᴘᴀʏᴍᴇɴᴛ ʀᴇᴊᴇᴄᴛᴇᴅ</b></blockquote>\n\n"
            f"<blockquote>» ᴜsᴇʀ ɪᴅ: <code>{target_uid}</code></blockquote>\n"
            f"<blockquote>» ᴘʟᴀɴ: <b>{plan_type_str} — {plan_label}</b></blockquote>\n"
            f"<blockquote>» ᴜᴛʀ: <code>{utr_stored}</code></blockquote>\n"
            f"<blockquote>» ʀᴇᴊᴇᴄᴛᴇᴅ ʙʏ: <code>{rejecter_id}</code></blockquote>"
        )
        for entry in req.get('admin_msg_ids', []):
            try:
                admin_id, msg_id = entry[0], entry[1]
                await client.edit_message_text(
                    chat_id=admin_id,
                    message_id=msg_id,
                    text=resolved_text,
                )
            except Exception:
                pass

        # Notify user
        try:
            await client.send_message(
                chat_id=target_uid,
                text=(
                    f"<blockquote>❌ <b>ᴘᴀʏᴍᴇɴᴛ ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ</b></blockquote>\n\n"
                    f"<blockquote>ᴡᴇ ᴄᴏᴜʟᴅ ɴᴏᴛ ᴠᴇʀɪꜰʏ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ꜰᴏʀ <b>{plan_type_str} — {plan_label}</b>.</blockquote>\n"
                    f"<blockquote expandable>ɪꜰ ʏᴏᴜ ᴅɪᴅ ᴍᴀᴋᴇ ᴛʜᴇ ᴘᴀʏᴍᴇɴᴛ, ᴘʟᴇᴀsᴇ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ ᴀᴅᴍɪɴ ᴡɪᴛʜ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ.</blockquote>"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url=f"https://t.me/{OWNER_TAG}")],
                ])
            )
        except Exception:
            pass

    # ── Get Free Premium — Referral Dashboard ────────────────────────────────
    elif data == "free_premium":
        user_id = query.from_user.id

        # Fetch stats + dynamic invite link simultaneously
        stats = await db.get_referral_stats(user_id)
        invite_link = await _get_referral_invite_link(client, user_id)

        validated = stats['month_validated']
        invited = stats['month_invited']
        rewards_given = stats['rewards_given_this_month']
        total_all_time = stats['total_all_time']

        # Build milestone progress display
        milestones_text = ""
        for (min_inv, days, label) in REFERRAL_MILESTONES:
            if min_inv in rewards_given:
                milestones_text += f"✅ {min_inv} ɪɴᴠɪᴛᴇs → {label} ꜰʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ (ᴄʟᴀɪᴍᴇᴅ)\n"
            elif validated >= min_inv:
                milestones_text += f"🎁 {min_inv} ɪɴᴠɪᴛᴇs → {label} ꜰʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ (ᴇᴀʀɴᴇᴅ!)\n"
            else:
                milestones_text += f"🔒 {min_inv} ɪɴᴠɪᴛᴇs → {label} ꜰʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ ({validated}/{min_inv})\n"

        dashboard_text = (
            f"<blockquote>🎁 <b>ɪɴᴠɪᴛᴇ & ᴇᴀʀɴ — ᴅᴀꜱʜʙᴏᴀʀᴅ</b></blockquote>\n\n"
            f"<blockquote>📨 ʏᴏᴜʀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ:</blockquote>\n"
            f"<code>{invite_link}</code>\n\n"
            f"<blockquote>📊 ᴛʜɪs ᴍᴏɴᴛʜ's ᴘʀᴏɢʀᴇss:\n"
            f"» ɪɴᴠɪᴛᴇᴅ: <b>{invited}</b> ᴜsᴇʀs\n"
            f"» ᴠᴀʟɪᴅᴀᴛᴇᴅ: <b>{validated}</b> ᴜsᴇʀs\n"
            f"» ᴀʟʟ-ᴛɪᴍᴇ ɪɴᴠɪᴛᴇᴅ: <b>{total_all_time}</b></blockquote>\n\n"
            f"<blockquote expandable>🏆 ʀᴇᴡᴀʀᴅ ᴍɪʟᴇsᴛᴏɴᴇs (ᴛʜɪs ᴍᴏɴᴛʜ):\n"
            f"{milestones_text}"
            f"\nɪɴᴠɪᴛᴇ ᴄᴏᴜɴᴛs ᴀs ᴠᴀʟɪᴅ ᴏɴʟʏ ᴡʜᴇɴ ᴛʜᴇ ɪɴᴠɪᴛᴇᴅ ᴜsᴇʀ ᴄᴏᴍᴘʟᴇᴛᴇs ᴀ sʜᴏʀᴛ-ʟɪɴᴋ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴏʀ ʙᴜʏs ᴀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ᴡɪᴛʜɪɴ ᴛʜɪs ᴍᴏɴᴛʜ.\n"
            f"ʀᴇsᴇᴛs ᴇᴠᴇʀʏ 1sᴛ ᴏꜰ ᴛʜᴇ ᴍᴏɴᴛʜ.</blockquote>"
        )

        # Build share URL — opens Telegram's native forward/share sheet
        share_text = (
            "🔥 ᴊᴏɪɴ ᴛʜɪs ᴀᴍᴀᴢɪɴɢ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ɢᴇᴛ ᴇxᴄʟᴜsɪᴠᴇ ᴄᴏɴᴛᴇɴᴛ ᴅᴀɪʟʏ! 💎\n\n"
            "✨ ᴍᴏᴠɪᴇs, sʜᴏᴡs, ᴡᴇʙ sᴇʀɪᴇs ᴀɴᴅ ᴍᴏʀᴇ — ᴀʟʟ ꜰᴏʀ ꜰʀᴇᴇ!\n\n"
            "👇 ᴄʟɪᴄᴋ ᴛᴏ ᴊᴏɪɴ:"
        )
        share_url = (
            f"https://t.me/share/url"
            f"?url={urllib.parse.quote(invite_link, safe='')}"
            f"&text={urllib.parse.quote(share_text, safe='')}"
        )

        await _smart_edit(
            client, query,
            text=dashboard_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 sʜᴀʀᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ", url=share_url)],
                [InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")],
                [
                    InlineKeyboardButton("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url=f"https://t.me/{OWNER_TAG}"),
                    InlineKeyboardButton("✖️ ᴄʟᴏsᴇ", callback_data="close"),
                ],
            ]),
        )

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
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏꜰꜰ"
            new_mode = "off" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(
                    f"ʀᴇǫ ᴍᴏᴅᴇ {'ᴏꜰꜰ' if mode == 'on' else 'ᴏɴ'}",
                    callback_data=f"rfs_toggle_{cid}_{new_mode}"
                )],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")],
            ]
            await _smart_edit(
                client, query,
                text=f"ᴄʜᴀɴɴᴇʟ: {chat.title}\nᴄᴜʀʀᴇɴᴛ ꜰᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ: {status}",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        except Exception as e:
            print(f"[cbb] rfs_ch_ error: {e}")
            await query.answer("ꜰᴀɪʟᴇᴅ ᴛᴏ ꜰᴇᴛᴄʜ ᴄʜᴀɴɴᴇʟ ɪɴꜰᴏ.", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        parts = data.split("_")
        cid = int(parts[2])
        action = parts[3]
        mode = "on" if action == "on" else "off"
        await db.set_channel_mode(cid, mode)
        await query.answer(f"ꜰᴏʀᴄᴇ-sᴜʙ sᴇᴛ ᴛᴏ {'ᴏɴ' if mode == 'on' else 'ᴏꜰꜰ'}")
        try:
            chat = await client.get_chat(cid)
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏꜰꜰ"
            new_mode = "off" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(
                    f"ʀᴇǫ ᴍᴏᴅᴇ {'ᴏꜰꜰ' if mode == 'on' else 'ᴏɴ'}",
                    callback_data=f"rfs_toggle_{cid}_{new_mode}"
                )],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")],
            ]
            await _smart_edit(
                client, query,
                text=f"ᴄʜᴀɴɴᴇʟ: {chat.title}\nᴄᴜʀʀᴇɴᴛ ꜰᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ: {status}",
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
                text="sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ꜰᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        except Exception as e:
            print(f"[cbb] fsub_back error: {e}")


# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
