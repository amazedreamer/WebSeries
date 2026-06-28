# Hash-Based Link Masking - Crypto Module
# Implements 5 cryptographic algorithms for generating masked link IDs
# /hash command for admin to select algorithm

import os
import hashlib
import hmac
import secrets
import time
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import ChatAction
from bot import Bot
from config import OWNER_ID, LOGGER
from database.database import db
from helper_func import admin

# ======================== CRYPTO ALGORITHMS ======================== #

# Secret key for keyed algorithms (generated once, stored in memory)
_SECRET_KEY = os.environ.get("HASH_SECRET_KEY", secrets.token_hex(32))

def aes128_hash(data: str) -> str:
    """AES-128 based ID generation.
    Uses AES-128 in CTR mode to encrypt data, returns hex ciphertext as ID.
    """
    from hashlib import sha256
    # Derive a 16-byte key from the secret
    key = sha256(_SECRET_KEY.encode()).digest()[:16]
    # Use timestamp + random nonce for uniqueness
    nonce = secrets.token_bytes(8)
    timestamp = str(time.time()).encode()
    plaintext = data.encode() + timestamp + nonce
    
    # AES-128 CTR mode encryption
    from Crypto.Cipher import AES
    cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
    ciphertext = cipher.encrypt(plaintext)
    
    # Return nonce + ciphertext as hex (allows decryption if needed)
    return (nonce + ciphertext).hex()


def md5_hash(data: str) -> str:
    """MD5 hash-based ID generation.
    Combines data with timestamp and random salt for uniqueness.
    Returns 32 hex char ID.
    """
    salt = secrets.token_hex(8)
    timestamp = str(time.time())
    combined = f"{data}:{timestamp}:{salt}:{_SECRET_KEY}"
    return hashlib.md5(combined.encode()).hexdigest()


def sha256_hash(data: str) -> str:
    """SHA-256 hash-based ID generation.
    Returns 64 hex char ID.
    """
    salt = secrets.token_hex(8)
    timestamp = str(time.time())
    combined = f"{data}:{timestamp}:{salt}:{_SECRET_KEY}"
    return hashlib.sha256(combined.encode()).hexdigest()


def otp_hash(data: str) -> str:
    """One-Time Pad based ID generation.
    XORs the data with a random key of equal length.
    Returns hex-encoded result.
    """
    # Create a fixed-length representation of the data
    data_hash = hashlib.sha256(data.encode()).digest()  # 32 bytes
    timestamp = str(time.time()).encode()
    combined = data_hash + hashlib.md5(timestamp).digest()  # 48 bytes
    
    # Generate a random key of the same length (the "pad")
    pad = secrets.token_bytes(len(combined))
    
    # XOR the data with the pad
    result = bytes(a ^ b for a, b in zip(combined, pad))
    
    # Return pad + result as hex (allows "decryption" if needed)
    return (pad + result).hex()


def hmac_sha1_hash(data: str) -> str:
    """HMAC-SHA1 based ID generation.
    Uses a keyed hash for authentication.
    Returns 40 hex char ID.
    """
    salt = secrets.token_hex(8)
    timestamp = str(time.time())
    message = f"{data}:{timestamp}:{salt}"
    return hmac.new(
        _SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha1
    ).hexdigest()


# ======================== ALGORITHM REGISTRY ======================== #

ALGORITHMS = {
    "aes128": {
        "name": "AES-128",
        "func": aes128_hash,
        "description": "Advanced Encryption Standard (128-bit)",
        "output_len": "~64 hex chars",
        "icon": "🔐"
    },
    "md5": {
        "name": "MD5",
        "func": md5_hash,
        "description": "Message Digest Algorithm 5",
        "output_len": "32 hex chars",
        "icon": "🔢"
    },
    "sha256": {
        "name": "SHA-256",
        "func": sha256_hash,
        "description": "Secure Hash Algorithm 256-bit",
        "output_len": "64 hex chars",
        "icon": "🛡️"
    },
    "otp": {
        "name": "One-Time Pad",
        "func": otp_hash,
        "description": "XOR-based One-Time Pad Encryption",
        "output_len": "~192 hex chars",
        "icon": "🎲"
    },
    "hmac_sha1": {
        "name": "HMAC-SHA1",
        "func": hmac_sha1_hash,
        "description": "Hash-based Message Authentication Code",
        "output_len": "40 hex chars",
        "icon": "🔑"
    }
}


def generate_hash_id(algorithm: str, data: str) -> str:
    """Generate a hash ID using the specified algorithm."""
    if algorithm not in ALGORITHMS:
        algorithm = "sha256"  # Default fallback
    return ALGORITHMS[algorithm]["func"](data)


# ======================== HASH PANEL IMAGE ======================== #

HASH_PANEL_PIC = "https://telegra.ph/file/ec17880d61180d3312d6a.jpg"


# ======================== /hash COMMAND ======================== #

@Bot.on_message(filters.command('hash') & filters.private & admin)
async def hash_command(client: Client, message: Message):
    """Admin command to view and select the hashing algorithm."""
    await message.reply_chat_action(ChatAction.TYPING)
    await show_hash_panel(client, message)


VMODE_INFO = {
    'instant': {
        'label': '⚡ ɪɴsᴛᴀɴᴛ',
        'description': 'ᴜsᴇʀ ᴍᴜsᴛ sᴏʟᴠᴇ ᴜʀʟ sʜᴏʀᴛᴇɴᴇʀ ᴏɴ ᴇᴠᴇʀʏ ɴᴇᴡ ʟɪɴᴋ',
    },
    '12h': {
        'label': '🕛 12 ʜᴏᴜʀs',
        'description': 'ᴜsᴇʀ ꜱᴏʟᴠᴇꜱ ᴏɴᴄᴇ ᴀɴᴅ ɢᴇᴛs 12ʜ ꜰʀᴇᴇ ᴀᴄᴄᴇꜱꜱ',
    },
    '24h': {
        'label': '🕐 24 ʜᴏᴜʀs',
        'description': 'ᴜsᴇʀ ꜱᴏʟᴠᴇꜱ ᴏɴᴄᴇ ᴀɴᴅ ɢᴇᴛs 24ʜ ꜰʀᴇᴇ ᴀᴄᴄᴇꜱꜱ',
    },
}

BOT_MODE_INFO = {
    'free': {
        'label': '🟢 ꜰʀᴇᴇ',
        'description': 'ᴀʟʟ ᴜsᴇʀs ɢᴇᴛ ꜰɪʟᴇs ꜰʀᴇᴇʟʏ — ɴᴏ ᴛᴏᴋᴇɴ ᴏʀ ᴘʀᴇᴍɪᴜᴍ ɴᴇᴇᴅᴇᴅ',
    },
    'token': {
        'label': '🔗 ᴛᴏᴋᴇɴ',
        'description': 'ᴜsᴇʀ ᴍᴜsᴛ sᴏʟᴠᴇ sʜᴏʀᴛᴇɴᴇʀ ᴏʀ ʜᴀᴠᴇ ᴘʀᴇᴍɪᴜᴍ',
    },
    'premium': {
        'label': '💎 ᴘʀᴇᴍɪᴜᴍ',
        'description': 'N ꜰʀᴇᴇ ᴀᴄᴄᴇꜱꜱᴇꜱ ᴛʜᴇɴ ᴘʀᴇᴍɪᴜᴍ ʀᴇǫᴜɪʀᴇᴅ (/free N ᴛᴏ sᴇᴛ)',
    },
}


async def show_hash_panel(client, query_or_message):
    """Display the hash algorithm selection + verification mode + invite mode + bot access mode panel."""
    current_algo = await db.get_hash_algorithm()
    current_info = ALGORITHMS.get(current_algo, ALGORITHMS["sha256"])
    current_vmode = await db.get_verification_mode()
    vmode_info = VMODE_INFO.get(current_vmode, VMODE_INFO['instant'])
    invite_mode = await db.get_invite_link_mode()
    invite_channel_id = await db.get_invite_channel()
    current_bot_mode = await db.get_bot_mode()
    bot_mode_info = BOT_MODE_INFO.get(current_bot_mode, BOT_MODE_INFO['token'])
    free_limit = await db.get_premium_mode_free_limit()

    # Build invite mode status line for caption
    if invite_mode == "channel":
        if invite_channel_id:
            try:
                ch = await client.get_chat(invite_channel_id)
                ch_label = f"#{ch.title}"
            except Exception:
                ch_label = str(invite_channel_id)
            invite_mode_line = f"🔗 ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ ({ch_label})"
        else:
            invite_mode_line = "🔗 ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ (⚠️ ɴᴏ ᴄʜᴀɴɴᴇʟ sᴇᴛ — ᴜsᴇ /ɪᴄʜᴀɴɴᴇʟ)"
    else:
        invite_mode_line = "🤖 ʙᴏᴛ ʟɪɴᴋ (ᴅᴇꜰᴀᴜʟᴛ)"

    caption = (
        "<blockquote><b>✦ ʜᴀsʜ ᴀʟɢᴏʀɪᴛʜᴍ sᴇᴛᴛɪɴɢs</b></blockquote>\n\n"
        f"<b>• ᴄᴜʀʀᴇɴᴛ ᴀʟɢᴏʀɪᴛʜᴍ:</b> {current_info['icon']} {current_info['name']}\n"
        f"<b>• ᴅᴇsᴄʀɪᴘᴛɪᴏɴ:</b> {current_info['description']}\n"
        f"<b>• ᴏᴜᴛᴘᴜᴛ ʟᴇɴɢᴛʜ:</b> {current_info['output_len']}\n\n"
        "<blockquote><b>≡ sᴇʟᴇᴄᴛ ᴀɴ ᴀʟɢᴏʀɪᴛʜᴍ ʙᴇʟᴏᴡ ᴛᴏ ᴜsᴇ ғᴏʀ ʟɪɴᴋ ᴍᴀsᴋɪɴɢ</b></blockquote>\n\n"
        "<blockquote><b>⚙️ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴍᴏᴅᴇ</b></blockquote>\n"
        f"<b>• ᴄᴜʀʀᴇɴᴛ ᴍᴏᴅᴇ:</b> {vmode_info['label']}\n"
        f"<b>• ɪɴꜰᴏ:</b> {vmode_info['description']}\n\n"
        "<blockquote><b>🔗 ɪɴᴠɪᴛᴇ ʟɪɴᴋ ᴍᴏᴅᴇ</b></blockquote>\n"
        f"<b>• ᴄᴜʀʀᴇɴᴛ:</b> {invite_mode_line}\n\n"
        "<blockquote><b>🚦 ʙᴏᴛ ᴀᴄᴄᴇss ᴍᴏᴅᴇ</b></blockquote>\n"
        f"<b>• ᴄᴜʀʀᴇɴᴛ:</b> {bot_mode_info['label']}\n"
        f"<b>• ɪɴꜰᴏ:</b> {bot_mode_info['description']}\n"
        f"<b>• ꜰʀᴇᴇ ʟɪᴍɪᴛ (ᴘʀᴇᴍɪᴜᴍ ᴍᴏᴅᴇ):</b> {free_limit} ꜰɪʟᴇs (/free N ᴛᴏ ᴄʜᴀɴɢᴇ)"
    )

    # Build algorithm buttons with current selection marked
    buttons = []
    for algo_key, algo_info in ALGORITHMS.items():
        marker = " ✓" if algo_key == current_algo else ""
        buttons.append([
            InlineKeyboardButton(
                f"{algo_info['icon']} {algo_info['name']}{marker}",
                callback_data=f"set_hash_{algo_key}"
            )
        ])

    # Verification mode row — all three options in one row, ✓ on active
    vmode_row = []
    for vkey, vinfo in VMODE_INFO.items():
        marker = " ✓" if vkey == current_vmode else ""
        vmode_row.append(
            InlineKeyboardButton(
                f"{vinfo['label']}{marker}",
                callback_data=f"set_vmode_{vkey}"
            )
        )
    buttons.append(vmode_row)

    # Invite link mode toggle row
    buttons.append([
        InlineKeyboardButton(
            f"🤖 ʙᴏᴛ ʟɪɴᴋ{' ✓' if invite_mode == 'bot' else ''}",
            callback_data="set_invite_mode_bot"
        ),
        InlineKeyboardButton(
            f"🔗 ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ{' ✓' if invite_mode == 'channel' else ''}",
            callback_data="set_invite_mode_channel"
        ),
    ])

    # Bot access mode row — Free / Token / Premium in one row
    bot_mode_row = []
    for mkey, minfo in BOT_MODE_INFO.items():
        marker = " ✓" if mkey == current_bot_mode else ""
        bot_mode_row.append(
            InlineKeyboardButton(
                f"{minfo['label']}{marker}",
                callback_data=f"set_bot_mode_{mkey}"
            )
        )
    buttons.append(bot_mode_row)

    buttons.append([InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data="close")])

    reply_markup = InlineKeyboardMarkup(buttons)

    if hasattr(query_or_message, 'message'):
        # It's a callback query
        await query_or_message.message.edit_media(
            media=InputMediaPhoto(media=HASH_PANEL_PIC, caption=caption),
            reply_markup=reply_markup
        )
    else:
        # It's a direct message
        await query_or_message.reply_photo(
            photo=HASH_PANEL_PIC,
            caption=caption,
            reply_markup=reply_markup
        )


# ======================== CALLBACK HANDLERS ======================== #

@Bot.on_callback_query(filters.regex(r'^set_hash_'))
async def set_hash_callback(client: Client, query: CallbackQuery):
    """Handle algorithm selection button clicks."""
    user_id = query.from_user.id
    if user_id != OWNER_ID and not await db.admin_exist(user_id):
        return await query.answer("⚠️ Only admins can change this setting.", show_alert=True)

    algo_key = query.data.replace("set_hash_", "")
    
    if algo_key not in ALGORITHMS:
        return await query.answer("❌ Invalid algorithm!", show_alert=True)

    # Save to database
    await db.set_hash_algorithm(algo_key)
    
    algo_info = ALGORITHMS[algo_key]
    await query.answer(
        f"✅ Algorithm set to {algo_info['name']}!",
        show_alert=True
    )

    # Refresh the panel
    await show_hash_panel(client, query)


@Bot.on_callback_query(filters.regex(r'^set_vmode_'))
async def set_vmode_callback(client: Client, query: CallbackQuery):
    """Handle verification mode selection button clicks."""
    user_id = query.from_user.id
    if user_id != OWNER_ID and not await db.admin_exist(user_id):
        return await query.answer("⚠️ Only admins can change this setting.", show_alert=True)

    mode_key = query.data.replace("set_vmode_", "")

    if mode_key not in VMODE_INFO:
        return await query.answer("❌ Invalid mode!", show_alert=True)

    await db.set_verification_mode(mode_key)

    vinfo = VMODE_INFO[mode_key]
    await query.answer(
        f"✅ Verification mode set to {vinfo['label']}!",
        show_alert=True
    )

    await show_hash_panel(client, query)


@Bot.on_callback_query(filters.regex(r'^set_invite_mode_'))
async def set_invite_mode_callback(client: Client, query: CallbackQuery):
    """Handle invite link mode toggle — bot link vs channel link."""
    user_id = query.from_user.id
    if user_id != OWNER_ID and not await db.admin_exist(user_id):
        return await query.answer("⚠️ Only admins can change this setting.", show_alert=True)

    mode = query.data.replace("set_invite_mode_", "")   # "bot" or "channel"

    if mode not in ("bot", "channel"):
        return await query.answer("❌ Unknown mode.", show_alert=True)

    await db.set_invite_link_mode(mode)

    if mode == "channel":
        channel_id = await db.get_invite_channel()
        if not channel_id:
            await query.answer(
                "✅ Mode set to Channel Link.\n\n"
                "⚠️ No invite channel configured yet!\n"
                "Use /ichannel <channel_id> to set one.",
                show_alert=True
            )
        else:
            await query.answer("✅ Invite mode set to Channel Link!", show_alert=False)
    else:
        await query.answer("✅ Invite mode set to Bot Link!", show_alert=False)

    await show_hash_panel(client, query)


@Bot.on_callback_query(filters.regex(r'^set_bot_mode_'))
async def set_bot_mode_callback(client: Client, query: CallbackQuery):
    """Handle bot access mode selection — Free / Token / Premium."""
    user_id = query.from_user.id
    if user_id != OWNER_ID and not await db.admin_exist(user_id):
        return await query.answer("⚠️ Only admins can change this setting.", show_alert=True)

    mode = query.data.replace("set_bot_mode_", "")

    if mode not in BOT_MODE_INFO:
        return await query.answer("❌ Invalid mode!", show_alert=True)

    await db.set_bot_mode(mode)

    minfo = BOT_MODE_INFO[mode]
    await query.answer(f"✅ Bot mode set to {minfo['label']}!", show_alert=True)
    await show_hash_panel(client, query)


@Bot.on_message(filters.command('free') & filters.private & admin)
async def set_free_limit_cmd(client: Client, message: Message):
    """Admin command: /free <N> — set the free access limit for Premium Mode."""
    try:
        limit = int(message.command[1])
        if limit < 1:
            raise ValueError("Limit must be ≥ 1")
        await db.set_premium_mode_free_limit(limit)
        await message.reply(
            f"<blockquote>✅ ꜰʀᴇᴇ ᴀᴄᴄᴇss ʟɪᴍɪᴛ sᴇᴛ ᴛᴏ <b>{limit}</b> ꜰɪʟᴇs ᴘᴇʀ ᴜsᴇʀ.</blockquote>\n"
            f"<blockquote>ᴛʜɪs ᴀᴘᴘʟɪᴇs ᴡʜᴇɴ ʙᴏᴛ ᴍᴏᴅᴇ ɪs 💎 ᴘʀᴇᴍɪᴜᴍ.</blockquote>"
        )
    except (IndexError, ValueError):
        current = await db.get_premium_mode_free_limit()
        await message.reply(
            f"<blockquote>📋 <b>ᴜsᴀɢᴇ:</b> <code>/free &lt;ɴᴜᴍʙᴇʀ&gt;</code></blockquote>\n"
            f"<blockquote>ᴄᴜʀʀᴇɴᴛ ʟɪᴍɪᴛ: <b>{current}</b> ꜰɪʟᴇs ᴘᴇʀ ᴜsᴇʀ</blockquote>"
        )
