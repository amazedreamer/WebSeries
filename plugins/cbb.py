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
import urllib.parse
import qrcode
import qrcode.constants
from datetime import datetime, timezone, timedelta

from pyrogram import Client, filters
from bot import Bot
from config import (
    UPI_ID, UPI_PAYEE_NAME, OWNER_TAG,
    ALL_PLANS, NORMAL_PLANS, SUPER_PLANS,
    REFERRAL_MILESTONES, PREMIUM_MSG_AUTO_DELETE_SECONDS,
    PAYMENT_MAX_MINUTES,
)
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import db
from database.db_premium import add_premium, is_premium_user, is_super_premium_user
from payment_verifier import (
    make_order_id, start_auto_verifier,
    verify_payment_once, on_payment_success,
)


# ── Price parser ──────────────────────────────────────────────────────────────
def parse_price_amount(price_str: str) -> int:
    m = _re.search(r'\d+', str(price_str))
    return int(m.group()) if m else 0


# ── Dynamic UPI QR Code Generator ────────────────────────────────────────────
def _generate_upi_qr(amount: int, order_id: str) -> io.BytesIO:
    """
    Generate a dynamic UPI QR code embedding amount + order_id in the
    standard UPI deep-link.  The &tr= field is crucial — Paytm records it
    as the merchant transaction reference, allowing API lookup by order_id.
    """
    upi_url = (
        f"upi://pay"
        f"?pa={UPI_ID}"
        f"&pn={urllib.parse.quote(UPI_PAYEE_NAME)}"
        f"&am={amount}"
        f"&tr={order_id}"                          # ← KEY: Paytm stores this as order ref
        f"&cu=INR"
        f"&tn={urllib.parse.quote('Premium Subscription')}"
    )
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    bio = io.BytesIO()
    bio.name = f"QR_{order_id}.png"
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio


# ── Misc helpers ──────────────────────────────────────────────────────────────
async def _get_referral_invite_link(client: Client, user_id: int) -> str:
    try:
        mode = await db.get_invite_link_mode()
        if mode == "channel":
            channel_id = await db.get_invite_channel()
            if channel_id:
                return await db.get_or_create_channel_invite(user_id, channel_id, client)
    except Exception as e:
        print(f"[cbb] _get_referral_invite_link error: {e}")
    return f"https://t.me/{client.username}?start=ref{user_id}"


async def _autodelete_after(client: Client, chat_id: int, message_id: int, delay: int):
    try:
        await asyncio.sleep(max(1, int(delay)))
        await client.delete_messages(chat_id, message_id)
    except Exception:
        pass


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
            await query.answer("sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.", show_alert=True)
        except Exception:
            pass


def _plan_key_to_info(key: str) -> dict:
    return ALL_PLANS.get(key)


# ─────────────────────────────────────────────────────────────────────────────
# Main callback handler
# ─────────────────────────────────────────────────────────────────────────────
@Bot.on_callback_query(filters.regex(
    r'^(help|about|start|premium|close|free_premium|'
    r'plan_type_|plan_select_|pmt_done_|pmt_cancel_|'
    r'pmt_ok_|pmt_no_|'
    r'rfs_ch_|rfs_toggle_|fsub_back)'
))
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    # ── Help ──────────────────────────────────────────────────────────────────
    if data == "help":
        from config import HELP_TXT
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
        from config import ABOUT_TXT
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
        from config import START_MSG
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

    # ── Buy Premium — Step 3: Generate dynamic QR + start auto-verifier ───────
    elif data.startswith("plan_select_"):
        plan_key = data[len("plan_select_"):]
        plan = _plan_key_to_info(plan_key)
        if not plan:
            await query.answer("ɪɴᴠᴀʟɪᴅ ᴘʟᴀɴ.", show_alert=True)
            return

        user_id = query.from_user.id
        amount = parse_price_amount(plan['price_str'])
        plan_type = "super" if plan_key.startswith("sp") else "normal"
        plan_type_str = "🚀 sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ" if plan_type == "super" else "💎 ɴᴏʀᴍᴀʟ ᴘʀᴇᴍɪᴜᴍ"
        plan_label = f"{plan_type_str.split()[-1]} {plan['label']}"   # e.g. "ᴘʀᴇᴍɪᴜᴍ 15 ᴅᴀʏs"

        # Block if user already has a pending order
        existing = await db.get_pending_order_for_user(user_id)
        if existing:
            await query.answer(
                "ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ʜᴀᴠᴇ ᴀ ᴘᴇɴᴅɪɴɢ ᴏʀᴅᴇʀ. "
                "ᴘʟᴇᴀsᴇ ᴘᴀʏ ᴏʀ ᴡᴀɪᴛ ꜰᴏʀ ɪᴛ ᴛᴏ ᴇxᴘɪʀᴇ.",
                show_alert=True
            )
            return

        await query.answer("ɢᴇɴᴇʀᴀᴛɪɴɢ ᴘᴀʏᴍᴇɴᴛ QR...", show_alert=False)

        # 1 — Create unique order ID & save to DB
        order_id = make_order_id(user_id)
        expiry_dt = datetime.now(timezone.utc) + timedelta(minutes=PAYMENT_MAX_MINUTES)

        await db.create_order(
            order_id=order_id,
            user_id=user_id,
            amount=float(amount),
            days=plan['days'],
            plan_key=plan_key,
            plan_type=plan_type,
        )

        # 2 — Generate dynamic QR (amount + order_id baked in)
        try:
            qr_bio = _generate_upi_qr(amount, order_id)
        except Exception as qr_err:
            print(f"[cbb] QR generation failed: {qr_err}")
            await db.update_order_status(order_id, "cancelled")
            await query.answer("QR ɢᴇɴᴇʀᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.", show_alert=True)
            return

        # 3 — Send QR to user
        caption = (
            f"<blockquote>💳 <b>ᴘᴀʏᴍᴇɴᴛ ᴅᴇᴛᴀɪʟs</b></blockquote>\n\n"
            f"<blockquote>» ᴘʟᴀɴ: {plan_type_str} — <b>{plan['label']}</b></blockquote>\n"
            f"<blockquote>» ᴀᴍᴏᴜɴᴛ: <b>₹{amount}</b> (ᴇxᴀᴄᴛ — ᴅᴏ ɴᴏᴛ ᴄʜᴀɴɢᴇ)</blockquote>\n"
            f"<blockquote>» ᴏʀᴅᴇʀ ɪᴅ: <code>{order_id}</code></blockquote>\n\n"
            f"<blockquote>📱 sᴄᴀɴ ᴡɪᴛʜ ᴀɴʏ ᴜᴘɪ ᴀᴘᴘ (Paytm / GPay / PhonePe).\n"
            f"ᴛʜᴇ ᴀᴍᴏᴜɴᴛ ɪs ᴘʀᴇ-ꜰɪʟʟᴇᴅ — ᴅᴏ ɴᴏᴛ ᴄʜᴀɴɢᴇ ɪᴛ.</blockquote>\n"
            f"<blockquote>» ᴜᴘɪ ɪᴅ: <code>{UPI_ID}</code></blockquote>\n\n"
            f"<blockquote expandable>⚡ ᴘʟᴀɴ ᴀᴄᴛɪᴠᴀᴛᴇs ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴀꜰᴛᴇʀ ᴘᴀʏᴍᴇɴᴛ.\n"
            f"ɪꜰ ɴᴏᴛ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴡɪᴛʜɪɴ 1-2 ᴍɪɴs, ᴛᴀᴘ <b>ɪ ʜᴀᴠᴇ ᴘᴀɪᴅ</b>.\n"
            f"⏳ ᴛʜɪs QR ᴇxᴘɪʀᴇs ɪɴ {PAYMENT_MAX_MINUTES} ᴍɪɴᴜᴛᴇs.</blockquote>"
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
                    [InlineKeyboardButton("✅ ɪ ʜᴀᴠᴇ ᴘᴀɪᴅ", callback_data=f"pmt_done_{order_id}")],
                    [
                        InlineKeyboardButton("💬 sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{OWNER_TAG}"),
                        InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data=f"pmt_cancel_{order_id}"),
                    ],
                ]),
            )
        except Exception as e:
            print(f"[cbb] plan_select send_photo failed: {e}")
            await db.update_order_status(order_id, "cancelled")
            return

        # 4 — Auto-delete QR message when order expires
        asyncio.create_task(_autodelete_after(
            client, sent.chat.id, sent.id, PAYMENT_MAX_MINUTES * 60
        ))

        # 5 — Start background auto-verifier
        start_auto_verifier(
            client=client,
            user_id=user_id,
            order_id=order_id,
            amount=float(amount),
            days=plan['days'],
            plan_key=plan_key,
            plan_type=plan_type,
            plan_label=f"{plan_type_str} — {plan['label']}",
            chat_id=sent.chat.id,
            expiry_dt=expiry_dt,
            qr_message_id=sent.id,
        )

    # ── "I Have Paid" — instant manual verification check ─────────────────────
    elif data.startswith("pmt_done_"):
        order_id = data[len("pmt_done_"):]
        order = await db.get_order(order_id)

        if not order:
            await query.answer("❌ ᴏʀᴅᴇʀ ɴᴏᴛ ꜰᴏᴜɴᴅ ᴏʀ ᴀʟʀᴇᴀᴅʏ ᴘʀᴏᴄᴇssᴇᴅ.", show_alert=True)
            return

        if order["status"] != "pending":
            status_msg = {
                "success":   "✅ ᴘᴀʏᴍᴇɴᴛ ᴀʟʀᴇᴀᴅʏ ᴠᴇʀɪꜰɪᴇᴅ!",
                "expired":   "⏰ ᴛʜɪs ᴏʀᴅᴇʀ ʜᴀs ᴇxᴘɪʀᴇᴅ.",
                "cancelled": "❌ ᴛʜɪs ᴏʀᴅᴇʀ ᴡᴀs ᴄᴀɴᴄᴇʟʟᴇᴅ.",
            }.get(order["status"], "ᴀʟʀᴇᴀᴅʏ ᴘʀᴏᴄᴇssᴇᴅ.")
            await query.answer(status_msg, show_alert=True)
            return

        # Verify owner matches
        if order["user_id"] != query.from_user.id:
            await query.answer("❌ ᴛʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ᴏʀᴅᴇʀ.", show_alert=True)
            return

        # ── Answer query ONCE — edit caption to show checking state ──────────
        # NOTE: query.answer() can only be called ONCE per callback.
        # We edit the caption first to show progress, then answer on result.
        try:
            await query.message.edit_caption(
                caption="⏳ <b>ᴄʜᴇᴄᴋɪɴɢ ᴘᴀʏᴛᴍ...</b> ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ.",
                reply_markup=None,
            )
        except Exception:
            pass

        result = await verify_payment_once(order_id, order["amount"])

        if result:
            plan = _plan_key_to_info(order["plan_key"]) or {}
            plan_type_str = "🚀 sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ" if order["plan_type"] == "super" else "💎 ɴᴏʀᴍᴀʟ ᴘʀᴇᴍɪᴜᴍ"
            plan_label = f"{plan_type_str} — {plan.get('label', str(order['days']) + ' ᴅᴀʏs')}"

            # Single query.answer — only call here (caption was edited above, not answered)
            try:
                await query.answer("✅ ᴘᴀʏᴍᴇɴᴛ ᴠᴇʀɪꜰɪᴇᴅ!", show_alert=True)
            except Exception:
                pass

            # on_payment_success deletes the QR message (qr_message_id = query.message.id)
            await on_payment_success(
                client=client,
                user_id=order["user_id"],
                order_id=order_id,
                amount=order["amount"],
                days=order["days"],
                plan_key=order["plan_key"],
                plan_type=order["plan_type"],
                plan_label=plan_label,
                txn_info=result,
                chat_id=query.message.chat.id,
                qr_message_id=query.message.id,
            )
        else:
            try:
                await query.message.edit_caption(
                    caption=(
                        f"<blockquote>💳 <b>ᴘᴀʏᴍᴇɴᴛ ɴᴏᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ ʏᴇᴛ</b></blockquote>\n\n"
                        f"<blockquote>ɪꜰ ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ᴘᴀɪᴅ, ᴡᴀɪᴛ 1-2 ᴍɪɴs ᴀɴᴅ ᴛᴀᴘ <b>ɪ ʜᴀᴠᴇ ᴘᴀɪᴅ</b> ᴀɢᴀɪɴ.\n"
                        f"ᴏʀᴅᴇʀ ɪᴅ: <code>{order_id}</code></blockquote>"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ ɪ ʜᴀᴠᴇ ᴘᴀɪᴅ", callback_data=f"pmt_done_{order_id}")],
                        [
                            InlineKeyboardButton("💬 sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{OWNER_TAG}"),
                            InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data=f"pmt_cancel_{order_id}"),
                        ],
                    ]),
                )
            except Exception:
                pass
            try:
                await query.answer(
                    "⏳ ᴘᴀʏᴍᴇɴᴛ ɴᴏᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ ʏᴇᴛ.\nᴡᴀɪᴛ 1-2 ᴍɪɴs & ᴛʀʏ ᴀɢᴀɪɴ.",
                    show_alert=True
                )
            except Exception:
                pass

    # ── Cancel order ──────────────────────────────────────────────────────────
    elif data.startswith("pmt_cancel_"):
        order_id = data[len("pmt_cancel_"):]
        order = await db.get_order(order_id)

        if order and order["user_id"] == query.from_user.id and order["status"] == "pending":
            await db.update_order_status(order_id, "cancelled")

        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            await client.send_message(
                chat_id=query.from_user.id,
                text=(
                    f"<blockquote>❌ <b>ᴏʀᴅᴇʀ ᴄᴀɴᴄᴇʟʟᴇᴅ</b></blockquote>\n\n"
                    f"<blockquote>ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ sᴇssɪᴏɴ ʜᴀs ʙᴇᴇɴ ᴄʟᴏsᴇᴅ.\n"
                    f"ᴜsᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ sᴛᴀʀᴛ ᴀ ɴᴇᴡ ᴘᴜʀᴄʜᴀsᴇ.</blockquote>"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")
                ]]),
            )
        except Exception:
            pass

    # ── Admin manual override: Approve ────────────────────────────────────────
    # (kept as admin fallback for edge cases where auto-verify fails)
    elif data.startswith("pmt_ok_"):
        target_uid = int(data[len("pmt_ok_"):])
        approver_id = query.from_user.id

        # Find a pending order for this user
        order = await db.get_pending_order_for_user(target_uid)
        if not order:
            await query.answer("ɴᴏ ᴘᴇɴᴅɪɴɢ ᴏʀᴅᴇʀ ꜰᴏᴜɴᴅ.", show_alert=True)
            return

        order_id = order["_id"]
        plan = _plan_key_to_info(order.get("plan_key", "")) or {}
        plan_type = order.get("plan_type", "normal")
        days = int(order.get("days", 0))
        amount = order.get("amount", 0)
        plan_label = f"{'Super' if plan_type == 'super' else 'Normal'} Premium — {plan.get('label', str(days) + ' days')}"

        if plan_type == "super":
            from database.db_premium import add_super_premium
            expiry = await add_super_premium(target_uid, days)
        else:
            expiry = await add_premium(target_uid, days, 'd')

        await db.update_order_status(order_id, "success", txn_id=f"MANUAL_{approver_id}")
        await query.answer("✅ ᴍᴀɴᴜᴀʟʟʏ ᴀᴘᴘʀᴏᴠᴇᴅ!", show_alert=False)

        from payment_verifier import format_expiry
        expiry_str = format_expiry(expiry) if expiry else "N/A"

        # Notify user
        plan_emoji = "🚀" if plan_type == "super" else "💎"
        try:
            await client.send_message(
                chat_id=target_uid,
                text=(
                    f"<blockquote>{plan_emoji} <b>ᴘʟᴀɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ʙʏ ᴀᴅᴍɪɴ</b></blockquote>\n\n"
                    f"<blockquote>» ᴘʟᴀɴ: <b>{plan_label}</b></blockquote>\n"
                    f"<blockquote>» ᴇxᴘɪʀᴇs: <code>{expiry_str}</code></blockquote>\n\n"
                    f"<blockquote>✅ ᴇɴᴊᴏʏ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss. ᴛʜᴀɴᴋ ʏᴏᴜ! 🙏</blockquote>"
                )
            )
        except Exception:
            pass

        try:
            await query.message.edit_text(
                f"<blockquote>✅ <b>ᴍᴀɴᴜᴀʟʟʏ ᴀᴘᴘʀᴏᴠᴇᴅ</b></blockquote>\n"
                f"<blockquote>» ᴜsᴇʀ: <code>{target_uid}</code></blockquote>\n"
                f"<blockquote>» ᴘʟᴀɴ: <b>{plan_label}</b></blockquote>\n"
                f"<blockquote>» ᴀᴘᴘʀᴏᴠᴇᴅ ʙʏ: <code>{approver_id}</code></blockquote>"
            )
        except Exception:
            pass

    # ── Admin manual override: Reject ─────────────────────────────────────────
    elif data.startswith("pmt_no_"):
        target_uid = int(data[len("pmt_no_"):])
        rejecter_id = query.from_user.id

        order = await db.get_pending_order_for_user(target_uid)
        if order:
            await db.update_order_status(order["_id"], "cancelled", txn_id=None)

        await query.answer("❌ ʀᴇᴊᴇᴄᴛᴇᴅ.", show_alert=False)

        try:
            await client.send_message(
                chat_id=target_uid,
                text=(
                    f"<blockquote>❌ <b>ᴘᴀʏᴍᴇɴᴛ ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ (ᴀᴅᴍɪɴ)</b></blockquote>\n\n"
                    f"<blockquote>ɪꜰ ʏᴏᴜ ᴅɪᴅ ᴘᴀʏ, ᴘʟᴇᴀsᴇ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ᴡɪᴛʜ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ.</blockquote>"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url=f"https://t.me/{OWNER_TAG}")
                ]])
            )
        except Exception:
            pass

        try:
            await query.message.edit_text(
                f"<blockquote>❌ <b>ᴏʀᴅᴇʀ ʀᴇᴊᴇᴄᴛᴇᴅ</b></blockquote>\n"
                f"<blockquote>» ᴜsᴇʀ: <code>{target_uid}</code></blockquote>\n"
                f"<blockquote>» ʀᴇᴊᴇᴄᴛᴇᴅ ʙʏ: <code>{rejecter_id}</code></blockquote>"
            )
        except Exception:
            pass

    # ── Get Free Premium — Referral Dashboard ────────────────────────────────
    elif data == "free_premium":
        user_id = query.from_user.id

        stats = await db.get_referral_stats(user_id)
        invite_link = await _get_referral_invite_link(client, user_id)

        validated = stats['month_validated']
        invited = stats['month_invited']
        rewards_given = stats['rewards_given_this_month']
        total_all_time = stats['total_all_time']

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


# ─────────────────────────────────────────────────────────────────────────────
# /id <DD-MM-YYYY>  — Admin: daily transaction report
# ─────────────────────────────────────────────────────────────────────────────

@Bot.on_message(filters.command("id") & filters.private)
async def id_transactions_cmd(client: Bot, message: Message):
    """
    /id 28-06-2026  →  shows all successful transactions for that day (IST)
    plus the total amount received. Admin/owner only.
    """
    from config import OWNER_ID
    try:
        from config import ADMINS
        admin_ids = list(ADMINS) if ADMINS else []
    except ImportError:
        admin_ids = []
    if OWNER_ID not in admin_ids:
        admin_ids.append(OWNER_ID)

    if message.from_user.id not in admin_ids:
        return  # silently ignore non-admins

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "<blockquote>📋 <b>ᴜsᴀɢᴇ</b></blockquote>\n\n"
            "<blockquote><code>/id DD-MM-YYYY</code></blockquote>\n"
            "<blockquote>ᴇxᴀᴍᴘʟᴇ: <code>/id 28-06-2026</code></blockquote>"
        )
        return

    date_str = args[1].strip()
    try:
        day, month, year = date_str.split('-')
        # Date range in UTC (IST = UTC+5:30, so IST midnight = UTC 18:30 prev day)
        # We use IST midnight to IST midnight for the date window
        ist_offset = timedelta(hours=5, minutes=30)
        ist_start = datetime(int(year), int(month), int(day), 0, 0, 0) - ist_offset
        ist_end   = ist_start + timedelta(days=1)
        start_utc = ist_start.replace(tzinfo=timezone.utc)
        end_utc   = ist_end.replace(tzinfo=timezone.utc)
    except Exception:
        await message.reply(
            "<blockquote>❌ <b>ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴇ ꜰᴏʀᴍᴀᴛ</b></blockquote>\n\n"
            "<blockquote>ᴜsᴇ ꜰᴏʀᴍᴀᴛ: <code>DD-MM-YYYY</code>\n"
            "ᴇxᴀᴍᴘʟᴇ: <code>/id 28-06-2026</code></blockquote>"
        )
        return

    orders = await db.get_orders_by_date(start_utc, end_utc)

    if not orders:
        await message.reply(
            f"<blockquote>📊 <b>ᴛʀᴀɴsᴀᴄᴛɪᴏɴs — {date_str}</b></blockquote>\n\n"
            f"<blockquote>ɴᴏ sᴜᴄᴄᴇssꜰᴜʟ ᴛʀᴀɴsᴀᴄᴛɪᴏɴs ꜰᴏᴜɴᴅ ꜰᴏʀ ᴛʜɪs ᴅᴀᴛᴇ.</blockquote>"
        )
        return

    total = sum(float(o.get('amount', 0)) for o in orders)
    lines = []

    for i, o in enumerate(orders, 1):
        # Format completion time in IST
        completed_at = o.get('completed_at') or o.get('created_at')
        if completed_at:
            try:
                from pytz import timezone as _pytz_tz
                ist = _pytz_tz("Asia/Kolkata")
                if not completed_at.tzinfo:
                    completed_at = completed_at.replace(tzinfo=timezone.utc)
                time_ist = completed_at.astimezone(ist).strftime("%I:%M %p")
            except Exception:
                time_ist = str(completed_at)[:16]
        else:
            time_ist = "N/A"

        plan_label = o.get('plan_key', 'N/A')
        plan_type  = o.get('plan_type', 'normal')
        plan_emoji = "🚀" if plan_type == "super" else "💎"
        txn_id     = o.get('txn_id') or "N/A"
        uid        = o.get('user_id', 'N/A')
        amt        = o.get('amount', 0)

        lines.append(
            f"<blockquote>{i}. {plan_emoji} <b>₹{amt}</b>  |  {time_ist} IST\n"
            f"» ᴜsᴇʀ: <code>{uid}</code>\n"
            f"» ᴘʟᴀɴ: <code>{plan_label}</code> ({plan_type})\n"
            f"» ᴛxɴ ɪᴅ: <code>{txn_id}</code></blockquote>"
        )

    # Telegram message size limit — split if too large
    header = (
        f"<blockquote>📊 <b>ᴛʀᴀɴsᴀᴄᴛɪᴏɴs — {date_str}</b></blockquote>\n\n"
    )
    footer = (
        f"\n<blockquote>💰 <b>ᴛᴏᴛᴀʟ ʀᴇᴄᴇɪᴠᴇᴅ: ₹{total:.0f}</b> "
        f"({len(orders)} ᴛʀᴀɴsᴀᴄᴛɪᴏɴ{'s' if len(orders) != 1 else ''})</blockquote>"
    )

    body = "\n".join(lines)
    full_msg = header + body + footer

    # If too long, split into chunks
    if len(full_msg) > 4000:
        await message.reply(header + f"<blockquote>({len(orders)} ᴛʀᴀɴsᴀᴄᴛɪᴏɴs ꜰᴏᴜɴᴅ)</blockquote>")
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) > 3800:
                await message.reply(chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk:
            await message.reply(chunk)
        await message.reply(footer)
    else:
        await message.reply(full_msg)


# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
