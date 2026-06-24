
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

import os
from os import environ, getenv
import logging
from logging.handlers import RotatingFileHandler


def small_caps(text):
    trans_table = str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    )
    return text.translate(trans_table)


# rohit_1888 on Tg
# --------------------------------------------
# Bot token @Botfather
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "8518449457:AAFUAqJV2g---IYPrTjEDSX209g24E0Y4qc")
APP_ID = int(os.environ.get("APP_ID", "30279772"))  # Your API ID from my.telegram.org
API_HASH = os.environ.get("API_HASH", "39170e11beedd62bb1534a55bfc53ea2")  # Your API Hash from my.telegram.org
# --------------------------------------------

CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003957454989"))  # Your db channel Id
OWNER = os.environ.get("OWNER", "SATYAM_SELLER")  # Owner username without @
OWNER_ID = int(os.environ.get("OWNER_ID", "7445966907"))  # Owner id
# --------------------------------------------
PORT = os.environ.get("PORT", "8001")
BASE_URL = os.environ.get("BASE_URL", "")  # e.g. https://your-domain.com
# --------------------------------------------
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://urvashiix:dThGnaimQESSvwFT@urvashiix.evuqrai.mongodb.net/?appName=urvashiix")
DB_NAME = os.environ.get("DATABASE_NAME", "PromoCHBot")
# --------------------------------------------
FSUB_LINK_EXPIRY = int(os.getenv("FSUB_LINK_EXPIRY", "300"))  # 0 means no expiry
BAN_SUPPORT = os.environ.get("BAN_SUPPORT", "https://t.me/SATYAM_SELLER")
TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "200"))
# --------------------------------------------
START_PIC = os.environ.get("START_PIC", "https://i.ibb.co/yn8JySKM/Gemini-Generated-Image-cxcl4hcxcl4hcxcl.png")
FORCE_PIC = os.environ.get("FORCE_PIC", "https://i.ibb.co/TD4nhdzR/Gemini-Generated-Image-qaxp7vqaxp7vqaxp.png")

# --------------------------------------------
# =============================================
# MULTIPLE URL SHORTENERS — rotation per user
# Add up to 6 shorteners. Leave URL/API empty to disable that slot.
# The bot will rotate each user through active shorteners in order:
# Shortener 1 → Shortener 2 → ... → Shortener N → back to Shortener 1
# =============================================

# Shortener 1 (primary / existing)
SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "vplink.in")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "043e0ff560fd252f517f02e3e0b11d399b598eb9")

# Shortener 2
SHORTLINK_URL_2 = os.environ.get("SHORTLINK_URL_2", "")
SHORTLINK_API_2 = os.environ.get("SHORTLINK_API_2", "")

# Shortener 3
SHORTLINK_URL_3 = os.environ.get("SHORTLINK_URL_3", "")
SHORTLINK_API_3 = os.environ.get("SHORTLINK_API_3", "")

# Shortener 4
SHORTLINK_URL_4 = os.environ.get("SHORTLINK_URL_4", "")
SHORTLINK_API_4 = os.environ.get("SHORTLINK_API_4", "")

# Shortener 5
SHORTLINK_URL_5 = os.environ.get("SHORTLINK_URL_5", "")
SHORTLINK_API_5 = os.environ.get("SHORTLINK_API_5", "")

# Shortener 6
SHORTLINK_URL_6 = os.environ.get("SHORTLINK_URL_6", "")
SHORTLINK_API_6 = os.environ.get("SHORTLINK_API_6", "")

# Build list of active shorteners (those where both URL and API are non-empty)
SHORTLINK_PROVIDERS = []
_raw_providers = [
    (SHORTLINK_URL,   SHORTLINK_API),
    (SHORTLINK_URL_2, SHORTLINK_API_2),
    (SHORTLINK_URL_3, SHORTLINK_API_3),
    (SHORTLINK_URL_4, SHORTLINK_API_4),
    (SHORTLINK_URL_5, SHORTLINK_API_5),
    (SHORTLINK_URL_6, SHORTLINK_API_6),
]
for _url, _api in _raw_providers:
    if _url and _api:
        SHORTLINK_PROVIDERS.append({"url": _url, "api": _api})

# Fallback: ensure at least the primary shortener is always present even if API is blank
if not SHORTLINK_PROVIDERS and SHORTLINK_URL:
    SHORTLINK_PROVIDERS.append({"url": SHORTLINK_URL, "api": SHORTLINK_API})

# --------------------------------------------
# === BYPASS PROTECTION ======================================================
# Minimum seconds a user must spend on the shortener before returning via the
# verification link. If they come back faster than this, the bot treats it as
# a bypass attempt: warns first time, then 12h ban, then 24h ban, then perma.
BYPASS_PROTECTION_SECONDS = int(os.environ.get("BYPASS_PROTECTION_SECONDS", "90"))

# === MESSAGE AUTO-EXPIRY ====================================================
# Short-link messages and the buy-premium QR/payment message both auto-delete
# this many seconds after being sent (if not already cleaned up by the user
# requesting a new file or completing the verification).
SHORT_MSG_AUTO_DELETE_SECONDS   = int(os.environ.get("SHORT_MSG_AUTO_DELETE_SECONDS",   "1200"))  # 20 min
PREMIUM_MSG_AUTO_DELETE_SECONDS = int(os.environ.get("PREMIUM_MSG_AUTO_DELETE_SECONDS", "1200"))  # 20 min
# ============================================================================

TUT_VID = os.environ.get("TUT_VID", "https://t.me/TEAM_EXCLUSIVE_ONLY/3")
SHORT_MSG = (
    f"<blockquote>✨ <b>{small_caps('ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ')}</b></blockquote>\n\n"
    f"<blockquote>{small_caps('ɪꜰ ɪᴛꜱ ʏᴏᴜʀ ꜰɪʀꜱᴛ ᴛɪᴍᴇ ʜᴇʀᴇ, ᴋɪɴᴅʟʏ ᴡᴀᴛᴄʜ ᴛʜᴇ ᴛᴜᴛᴏʀɪᴀʟ ʙᴇꜰᴏʀᴇ ᴘʀᴏᴄᴇᴇᴅɪɴɢ.')}</blockquote>"
)

SHORTENER_PIC = os.environ.get("SHORTENER_PIC", "https://i.ibb.co/8ggPBWDS/Gemini-Generated-Image-6ow8rn6ow8rn6ow8.png")
# --------------------------------------------

# --------------------------------------------
HELP_TXT = "<b><blockquote>ɪ ᴀᴍ ᴀ ʙᴏᴛ ᴡᴏʀᴋ ғᴏʀ @SATYAM_SELLER\n\n❏ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs\n├/start : sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\n├/about : ᴏᴜʀ Iɴғᴏʀᴍᴀᴛɪᴏɴ\n└/help : ʜᴇʟᴘ ʀᴇʟᴀᴛᴇᴅ ʙᴏᴛ\n\n sɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴏɴ ʟɪɴᴋ ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴊᴏɪɴ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴛʜᴀᴛs ɪᴛ.....!\n\n ᴅᴇᴠᴇʟᴏᴘᴇᴅ ʙʏ <a href=https://t.me/TheToxicMeme>The Toxic Meme</a></blockquote></b>"
ABOUT_TXT = (
    f"<blockquote>ℹ️ <b>{small_caps('sʏsᴛᴇᴍ ɪɴғᴏʀᴍᴀᴛɪᴏɴ')}</b></blockquote>\n\n"
    f"<blockquote>{small_caps('ᴀᴅᴠᴀɴᴄᴇᴅ ᴄᴏɴᴛᴇɴᴛ ᴅᴇʟɪᴠᴇʀʏ sʏsᴛᴇᴍ ᴏᴘᴇʀᴀᴛɪɴɢ ғᴏʀ')} @SATYAM_SELLER</blockquote>\n\n"
    f"<blockquote>👑 <b>{small_caps('ᴅᴇᴠᴇʟᴏᴘᴇʀ')}</b> — <a href='https://t.me/Ebadmindmbot'>{small_caps('ᴀᴅᴍɪɴ sᴜᴘᴘᴏʀᴛ')}</a></blockquote>"
)
# --------------------------------------------
# --------------------------------------------
START_MSG = (
    f"<blockquote>👤 <b>{small_caps('ᴡᴇʟᴄᴏᴍᴇ')}</b></blockquote>\n\n"
    f"<blockquote>{small_caps('ʜɪ')} {{mention}}, {small_caps('ɪ ᴀᴍ ᴛʜᴇ ᴏғғɪᴄɪᴀʟ ᴀssɪsᴛᴀɴᴛ ғᴏʀ')} @SATYAM_SELLER</blockquote>\n"
    f"<blockquote>{small_caps('ᴜsᴇ ᴛʜᴇ ᴍᴇɴᴜ ʙᴇʟᴏᴡ ᴛᴏ ᴇxᴘʟᴏʀᴇ ᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ.')}</blockquote>"
)

FORCE_MSG = (
    f"<blockquote>🔒 <b>{small_caps('ᴀᴄᴄᴇss ʀᴇsᴛʀɪᴄᴛᴇᴅ')}</b></blockquote>\n\n"
    f"<blockquote>{small_caps('ʜᴇʟʟᴏ')} {{mention}}, {small_caps('ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ʙᴇʟᴏᴡ ᴛᴏ ᴜɴʟᴏᴄᴋ ᴄᴏɴᴛᴇɴᴛ.')}</blockquote>\n"
    f"<blockquote>{small_caps('ᴛᴀᴘ ʀᴇʟᴏᴀᴅ ᴏɴᴄᴇ ʏᴏᴜ ʜᴀᴠᴇ ᴊᴏɪɴᴇᴅ.')}</blockquote>"
)

CMD_TXT = """<blockquote><b>» ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:</b></blockquote>

<b>›› /dlt_time :</b> sᴇᴛ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ
<b>›› /check_dlt_time :</b> ᴄʜᴇᴄᴋ ᴄᴜʀʀᴇɴᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ
<b>›› /dbroadcast :</b> ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏᴄᴜᴍᴇɴᴛ / ᴠɪᴅᴇᴏ
<b>›› /ban :</b> ʙᴀɴ ᴀ ᴜꜱᴇʀ
<b>›› /unban :</b> ᴜɴʙᴀɴ ᴀ ᴜꜱᴇʀ
<b>›› /banlist :</b> ɢᴇᴛ ʟɪsᴛ ᴏꜰ ʙᴀɴɴᴇᴅ ᴜꜱᴇʀs
<b>›› /addchnl :</b> ᴀᴅᴅ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ
<b>›› /delchnl :</b> ʀᴇᴍᴏᴠᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ
<b>›› /listchnl :</b> ᴠɪᴇᴡ ᴀᴅᴅᴇᴅ ᴄʜᴀɴɴᴇʟs
<b>›› /fsub_mode :</b> ᴛᴏɢɢʟᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴍᴏᴅᴇ
<b>›› /pbroadcast :</b> sᴇɴᴅ ᴘʜᴏᴛᴏ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀs
<b>›› /add_admin :</b> ᴀᴅᴅ ᴀɴ ᴀᴅᴍɪɴ
<b>›› /deladmin :</b> ʀᴇᴍᴏᴠᴇ ᴀɴ ᴀᴅᴍɪɴ
<b>›› /admins :</b> ɢᴇᴛ ʟɪsᴛ ᴏꜰ ᴀᴅᴍɪɴs
<b>›› /addpremium :</b> ᴀᴅᴅ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ
<b>›› /premium_users :</b> ʟɪsᴛ ᴀʟʟ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀs
<b>›› /remove_premium :</b> ʀᴇᴍᴏᴠᴇ ᴘʀᴇᴍɪᴜᴍ ꜰʀᴏᴍ ᴀ ᴜꜱᴇʀ
<b>›› /myplan :</b> ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ sᴛᴀᴛᴜs
<b>›› /count :</b> ᴄᴏᴜɴᴛ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴs
<b>›› /delreq :</b> Rᴇᴍᴏᴠᴇᴅ ʟᴇғᴛᴏᴠᴇʀ ɴᴏɴ-ʀᴇǫᴜᴇsᴛ ᴜsᴇʀs
"""
# --------------------------------------------
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "<b>• powerd by @TEAMxGODS</b>")
PROTECT_CONTENT = True if os.environ.get('PROTECT_CONTENT', "True") == "True" else False
# --------------------------------------------
DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", None) == 'False'
# --------------------------------------------
BOT_STATS_TEXT = f"<blockquote>⏳ <b>{small_caps('sʏsᴛᴇᴍ ᴜᴘᴛɪᴍᴇ')}</b>\n{{uptime}}</blockquote>"
USER_REPLY_TEXT = f"<blockquote>⛔ <b>{small_caps('ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ')}</b>\n{small_caps('ᴀᴅᴍɪɴ ᴘʀɪᴠɪʟᴇɢᴇs ʀᴇǫᴜɪʀᴇᴅ.')}</blockquote>"

# ==========================(BUY PREMIUM)====================#

OWNER_TAG = os.environ.get("OWNER_TAG", "SATYAM_SELLER")
UPI_ID = os.environ.get("UPI_ID", "technogamerzs151@oksbi")
UPI_PAYEE_NAME = os.environ.get("UPI_PAYEE_NAME", "Sultana")
QR_PIC = os.environ.get("QR_PIC", "https://i.ibb.co/rKzgNX5r/photo-2026-06-24-11-10-49.jpg")
SCREENSHOT_URL = os.environ.get("SCREENSHOT_URL", f"t.me/SATYAM_SELLER")
# --------------------------------------------
# Time and its price
# 10 Days
PRICE1 = os.environ.get("PRICE1", "10 rs")
# 1 Month
PRICE2 = os.environ.get("PRICE2", "99 rs")
# 3 Month
PRICE3 = os.environ.get("PRICE3", "199 rs")
# 6 Month
PRICE4 = os.environ.get("PRICE4", "299")

# Super Premium Prices
PRICE_SP_1 = os.environ.get("PRICE_SP_1", "20 rs")
PRICE_SP_2 = os.environ.get("PRICE_SP_2", "149 rs")
PRICE_SP_3 = os.environ.get("PRICE_SP_3", "299 rs")
PRICE_SP_4 = os.environ.get("PRICE_SP_4", "499 rs")

# Plan definitions (used by buy-premium flow to generate QR + buttons)
# key format: np_<id> for normal, sp_<id> for super
NORMAL_PLANS = [
    {"key": "np_0", "label": "𝟷 ᴅᴀʏ",    "days": 1,  "price_str": PRICE1},
    {"key": "np_1", "label": "15 ᴅᴀʏs",   "days": 15,  "price_str": PRICE2},
    {"key": "np_2", "label": "𝟶1 ᴍᴏɴᴛʜ",  "days": 30,  "price_str": PRICE3},
    {"key": "np_3", "label": "𝟶2 ᴍᴏɴᴛʜs",  "days": 60, "price_str": PRICE4},
]
SUPER_PLANS = [
    {"key": "sp_0", "label": "𝟶𝟷 ᴅᴀʏ",   "days": 1,  "price_str": PRICE_SP_2},
    {"key": "sp_1", "label": "15 ᴅᴀʏs",  "days": 15,  "price_str": PRICE_SP_3},
    {"key": "sp_2", "label": "𝟶1 ᴍᴏɴᴛʜ",  "days": 30, "price_str": PRICE_SP_4},
    {"key": "sp_3", "label": "𝟶2 ᴍᴏɴᴛʜs",    "days": 60, "price_str": PRICE_SP_5},
]

ALL_PLANS = {p["key"]: p for p in NORMAL_PLANS + SUPER_PLANS}

# ===================(END)========================#

# ==========================(REFERRAL SYSTEM)====================#
# Milestones: (min_validated_invites, free_days_normal_premium)
REFERRAL_MILESTONES = [
    (3,  2,  "2 ᴅᴀʏs"),
    (10, 7,  "7 ᴅᴀʏs"),
    (40, 30, "1 ᴍᴏɴᴛʜ"),
]
# ===================(END)========================#

LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
