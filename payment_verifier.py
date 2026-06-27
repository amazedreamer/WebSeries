"""
Paytm Auto-Payment Verifier for PromoCH
=========================================
Polls the Vercel Paytm-proxy API every PAYMENT_VERIFY_INTERVAL seconds.
On success: auto-activates the plan, notifies the user, and logs the
transaction to the admin/owner channel — no manual admin approval needed.

API endpoint (public proxy):
  GET https://pay-api-master.vercel.app/?mid=<MID>&oid=<order_id>

The UPI QR code embeds  &tr=<order_id>  so Paytm records the order_id as
the merchant transaction reference, making it look-uppable via the API.
"""

import asyncio
import aiohttp
import logging
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

from config import (
    PAYTM_MID, PAYMENT_API_URL,
    PAYMENT_VERIFY_INTERVAL, PAYMENT_MAX_MINUTES, AMOUNT_TOLERANCE,
    PAYMENT_LOG_CHANNEL_ID, OWNER_ID, OWNER_TAG,
)

logger = logging.getLogger(__name__)

# ── Active background verifier tasks: {order_id: asyncio.Task} ───────────────
_active_verifiers: Dict[str, asyncio.Task] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_order_id(user_id: int) -> str:
    """
    Generate a unique order ID.  Example: ORD-7445966907-X8Y2
    The suffix ensures uniqueness even if a user starts a new purchase
    before the previous one expires.
    """
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORD-{user_id}-{suffix}"


def format_expiry(dt: datetime) -> str:
    """Convert a datetime to a readable IST expiry string."""
    if not dt:
        return "N/A"
    try:
        from pytz import timezone as _tz
        ist = _tz("Asia/Kolkata")
        dt_ist = dt.astimezone(ist)
        return dt_ist.strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        return dt.strftime("%d %b %Y, %H:%M UTC")


# ─────────────────────────────────────────────────────────────────────────────
# Single API verification call
# ─────────────────────────────────────────────────────────────────────────────

async def verify_payment_once(order_id: str, expected_amount: float) -> Optional[dict]:
    """
    Hit the Vercel proxy API and validate the response.
    Returns transaction details dict on success, None otherwise.

    Security checks performed:
      1. HTTP 200 response
      2. STATUS == "TXN_SUCCESS"
      3. ORDERID matches our order_id (prevents cross-order injection)
      4. TXNAMOUNT matches expected_amount within AMOUNT_TOLERANCE
      5. TXNID not already used (replay-attack protection)
    """
    from database.database import db

    url = f"{PAYMENT_API_URL}?mid={PAYTM_MID}&oid={order_id}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"[PayVerify] HTTP {resp.status} for order {order_id}")
                    return None
                data = await resp.json(content_type=None)
    except asyncio.TimeoutError:
        logger.warning(f"[PayVerify] Timeout for order {order_id}")
        return None
    except Exception as e:
        logger.error(f"[PayVerify] Connection error: {e}")
        return None

    if not data or data.get("STATUS") != "TXN_SUCCESS":
        return None

    # 3 — Order ID must match exactly
    if data.get("ORDERID") != order_id:
        logger.warning(
            f"[PayVerify] Order ID mismatch! expected={order_id} got={data.get('ORDERID')}"
        )
        return None

    # 4 — Amount check
    try:
        paid = float(data.get("TXNAMOUNT", 0))
        if abs(paid - expected_amount) > AMOUNT_TOLERANCE:
            logger.warning(
                f"[PayVerify] Amount mismatch! expected={expected_amount} paid={paid}"
            )
            return None
    except (ValueError, TypeError):
        return None

    # 5 — Replay-attack protection
    txn_id = data.get("TXNID")
    if txn_id and await db.is_txn_id_used(txn_id):
        logger.critical(
            f"[PayVerify] REPLAY ATTACK BLOCKED — TXN_ID {txn_id} already used!"
        )
        return None

    return {
        "txn_id":      txn_id,
        "bank_txn_id": data.get("BANKTXNID"),
        "txn_amount":  paid,
        "txn_date":    data.get("TXNDATE"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Success Handler
# ─────────────────────────────────────────────────────────────────────────────

async def on_payment_success(client, user_id: int, order_id: str,
                              amount: float, days: int, plan_key: str,
                              plan_type: str, plan_label: str,
                              txn_info: dict, chat_id: int,
                              qr_message_id: Optional[int] = None):
    """
    Called once a payment is confirmed.
    1. Deletes the QR message (if still present).
    2. Grants the plan (normal or super premium).
    3. Notifies the user.
    4. Logs the sale to the admin channel + owner.
    """
    from database.database import db
    from database.db_premium import add_premium

    # 0 ── Delete QR/payment message so user sees clean confirmation ──────────
    if qr_message_id:
        try:
            await client.delete_messages(chat_id=chat_id, message_ids=qr_message_id)
        except Exception:
            pass

    # 1 ── Activate plan ─────────────────────────────────────────────────────
    expiry = None
    try:
        if plan_type == "super":
            from database.db_premium import add_super_premium
            expiry = await add_super_premium(user_id, days)
        else:
            expiry = await add_premium(user_id, days, 'd')
    except Exception as plan_err:
        logger.error(f"[PayVerify] Plan activation failed for user {user_id}: {plan_err}")

    # 2 ── Update order to success ────────────────────────────────────────────
    await db.update_order_status(order_id, "success", txn_id=txn_info.get("txn_id"))

    # 3 ── Notify user ────────────────────────────────────────────────────────
    plan_emoji = "🚀" if plan_type == "super" else "💎"
    expiry_str = format_expiry(expiry) if expiry else "N/A"
    user_text = (
        f"<blockquote>{plan_emoji} <b>ᴘʟᴀɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ!</b></blockquote>\n\n"
        f"<blockquote>✅ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ʜᴀs ʙᴇᴇɴ ᴠᴇʀɪꜰɪᴇᴅ ᴀɴᴅ ʏᴏᴜʀ ᴘʟᴀɴ ɪs ɴᴏᴡ ᴀᴄᴛɪᴠᴇ.</blockquote>\n"
        f"<blockquote>» ᴘʟᴀɴ: <b>{plan_label}</b></blockquote>\n"
        f"<blockquote>» ᴇxᴘɪʀᴇs: <code>{expiry_str}</code></blockquote>\n\n"
        f"<blockquote>ᴇɴᴊᴏʏ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss. ᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ʏᴏᴜʀ ꜱᴜᴘᴘᴏʀᴛ! 🙏</blockquote>"
    )
    try:
        sent = await client.send_message(chat_id=chat_id, text=user_text)
        try:
            await client.pin_chat_message(
                chat_id=chat_id, message_id=sent.id, disable_notification=False
            )
        except Exception:
            pass
    except Exception as ue:
        logger.warning(f"[PayVerify] Could not notify user {user_id}: {ue}")

    # 4 ── Log to admin channel ───────────────────────────────────────────────
    log_text = (
        f"<blockquote>💰 <b>ɴᴇᴡ ᴘʀᴇᴍɪᴜᴍ sᴀʟᴇ (ᴀᴜᴛᴏ-ᴠᴇʀɪꜰɪᴇᴅ)</b></blockquote>\n\n"
        f"<blockquote>👤 ᴜsᴇʀ ɪᴅ: <code>{user_id}</code></blockquote>\n"
        f"<blockquote>📦 ᴘʟᴀɴ: <b>{plan_label}</b></blockquote>\n"
        f"<blockquote>💳 ᴀᴍᴏᴜɴᴛ: <b>₹{amount}</b></blockquote>\n"
        f"<blockquote>🆔 ᴏʀᴅᴇʀ ɪᴅ: <code>{order_id}</code></blockquote>\n"
        f"<blockquote>🏦 ᴘᴀʏᴛᴍ ᴛxɴ ɪᴅ: <code>{txn_info.get('txn_id', 'N/A')}</code></blockquote>\n"
        f"<blockquote>🏛 ʙᴀɴᴋ ᴛxɴ ɪᴅ: <code>{txn_info.get('bank_txn_id', 'N/A')}</code></blockquote>\n"
        f"<blockquote>📅 ᴛxɴ ᴅᴀᴛᴇ: <code>{txn_info.get('txn_date', 'N/A')}</code></blockquote>\n"
        f"<blockquote>⏳ ᴇxᴘɪʀᴇs: <code>{expiry_str}</code></blockquote>"
    )
    for log_target in {PAYMENT_LOG_CHANNEL_ID, OWNER_ID}:
        try:
            await client.send_message(chat_id=log_target, text=log_text)
        except Exception as le:
            logger.warning(f"[PayVerify] Log send failed to {log_target}: {le}")

    logger.info(
        f"[PayVerify] SUCCESS | user={user_id} order={order_id} "
        f"txn={txn_info.get('txn_id')} amount=₹{amount}"
    )

    # 5 ── Referral credit (if applicable) ───────────────────────────────────
    try:
        ref_id = await db.mark_referral_plan_bought(user_id)
        if ref_id and ref_id > 0:
            from plugins.start import _handle_referral_validation
            await _handle_referral_validation(client, user_id)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Background auto-verifier loop
# ─────────────────────────────────────────────────────────────────────────────

async def _run_auto_verifier(client, user_id: int, order_id: str,
                              amount: float, days: int, plan_key: str,
                              plan_type: str, plan_label: str,
                              chat_id: int, expiry_dt: datetime,
                              qr_message_id: Optional[int] = None):
    """
    Background task: polls the Vercel API every PAYMENT_VERIFY_INTERVAL seconds.

    Lifecycle:
      - Pending  → polls API → SUCCESS → activate plan, log, notify user
      - Pending  → wall-clock hits expiry_dt → delete QR → grace period (2 min)
                   → recheck once more → if still pending → mark EXPIRED, notify user
      - Pending  → order manually cancelled via button → loop breaks on status check
    """
    from database.database import db
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    max_checks = max(1, (PAYMENT_MAX_MINUTES * 60) // PAYMENT_VERIFY_INTERVAL)
    logger.info(
        f"[AutoVerifier] Started | order={order_id} user={user_id} "
        f"amount=₹{amount} max_checks={max_checks}"
    )

    for attempt in range(max_checks):
        await asyncio.sleep(PAYMENT_VERIFY_INTERVAL)

        # ── Check if already handled (success / cancelled / manual) ──────────
        order = await db.get_order(order_id)
        if not order or order["status"] != "pending":
            logger.info(f"[AutoVerifier] Order {order_id} no longer pending — stopping.")
            break

        # ── Check wall-clock expiry ───────────────────────────────────────────
        if datetime.now(timezone.utc) >= expiry_dt:
            # Delete QR message so user can't scan an expired code
            if qr_message_id:
                try:
                    await client.delete_messages(chat_id=chat_id, message_ids=qr_message_id)
                except Exception:
                    pass

            # Give 2-minute grace period for payments made right before expiry
            logger.info(f"[AutoVerifier] Order {order_id} expired. 2-min grace check...")
            await asyncio.sleep(120)

            order = await db.get_order(order_id)
            if order and order["status"] == "pending":
                result = await verify_payment_once(order_id, amount)
                if result:
                    logger.info(f"[AutoVerifier] Late payment detected for {order_id}")
                    await on_payment_success(
                        client, user_id, order_id, amount, days,
                        plan_key, plan_type, plan_label, result, chat_id
                    )
                    break

                # Confirmed expired — notify user
                await db.update_order_status(order_id, "expired")
                try:
                    await client.send_message(
                        chat_id=chat_id,
                        text=(
                            f"<blockquote>⏰ <b>ᴘᴀʏᴍᴇɴᴛ sᴇssɪᴏɴ ᴇxᴘɪʀᴇᴅ</b></blockquote>\n\n"
                            f"<blockquote>ʏᴏᴜʀ ᴏʀᴅᴇʀ <code>{order_id}</code> ʜᴀs ᴇxᴘɪʀᴇᴅ.</blockquote>\n"
                            f"<blockquote>ɪꜰ ʏᴏᴜ ᴘᴀɪᴅ, ᴘʟᴇᴀsᴇ ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ᴡɪᴛʜ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ.</blockquote>"
                        ),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                "💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ",
                                url=f"https://t.me/{OWNER_TAG}"
                            )
                        ]])
                    )
                except Exception:
                    pass
                logger.info(f"[AutoVerifier] Order {order_id} marked EXPIRED after grace.")
            break

        # ── Normal poll ───────────────────────────────────────────────────────
        result = await verify_payment_once(order_id, amount)
        if result:
            # Delete QR so the user doesn't see a stale payment screen
            if qr_message_id:
                try:
                    await client.delete_messages(chat_id=chat_id, message_ids=qr_message_id)
                except Exception:
                    pass
            await on_payment_success(
                client, user_id, order_id, amount, days,
                plan_key, plan_type, plan_label, result, chat_id
            )
            break

    # Cleanup
    _active_verifiers.pop(order_id, None)
    logger.info(f"[AutoVerifier] Task ended for order {order_id}")


def start_auto_verifier(client, user_id: int, order_id: str,
                        amount: float, days: int, plan_key: str,
                        plan_type: str, plan_label: str,
                        chat_id: int, expiry_dt: datetime,
                        qr_message_id: Optional[int] = None):
    """
    Launch the background auto-verifier task.
    Safe to call multiple times — duplicate calls for same order_id are ignored.
    """
    if order_id in _active_verifiers:
        return
    task = asyncio.create_task(
        _run_auto_verifier(
            client, user_id, order_id, amount, days,
            plan_key, plan_type, plan_label, chat_id, expiry_dt,
            qr_message_id
        )
    )
    _active_verifiers[order_id] = task
    logger.info(f"[AutoVerifier] Task registered for order {order_id}")
