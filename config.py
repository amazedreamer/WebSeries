
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
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "8502483522:AAHTX_tMpgow7G84dAXZ-TrHT2-br_3ciX0")
APP_ID = int(os.environ.get("APP_ID", "27570787"))  # Your API ID from my.telegram.org
API_HASH = os.environ.get("API_HASH", "f5e4d37759af94d4efc2dfb58b30af39")  # Your API Hash from my.telegram.org
# --------------------------------------------

CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003732812304"))  # Your db channel Id
OWNER = os.environ.get("OWNER", "sakxxii")  # Owner username without @
OWNER_ID = int(os.environ.get("OWNER_ID", "8584220782"))  # Owner id
# --------------------------------------------
PORT = os.environ.get("PORT", "8001")
BASE_URL = os.environ.get("BASE_URL", "")  # e.g. https://your-domain.com
# --------------------------------------------
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://Test:aloksingh@cluster0.iomykdc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = os.environ.get("DATABASE_NAME", "NewUpdate")
# --------------------------------------------
FSUB_LINK_EXPIRY = int(os.getenv("FSUB_LINK_EXPIRY", "150"))  # 0 means no expiry
BAN_SUPPORT = os.environ.get("BAN_SUPPORT", "https://t.me/OfficialAdminDMRoBot")
TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "200"))
# --------------------------------------------
START_PIC = os.environ.get("START_PIC", "https://api.aniwallpaper.workers.dev/random?type=cute")
FORCE_PIC = os.environ.get("FORCE_PIC", "https://api.aniwallpaper.workers.dev/i/a77d7c")

# --------------------------------------------
# =============================================
# MULTIPLE URL SHORTENERS — rotation per user
# Add up to 6 shorteners. Leave URL/API empty to disable that slot.
# The bot will rotate each user through active shorteners in order:
# Shortener 1 → Shortener 2 → ... → Shortener N → back to Shortener 1
# =============================================

# Shortener 1 (primary / existing)
SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "arolinks.com")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "3c41df8026a8c7adff4a7f801b47da074ff992cb")

# Shortener 2
SHORTLINK_URL_2 = os.environ.get("SHORTLINK_URL_2", "get2short.com")
SHORTLINK_API_2 = os.environ.get("SHORTLINK_API_2", "20a4eff7f94bf5fb5d83e98eeab5616f868bb4dc")

# Shortener 3
SHORTLINK_URL_3 = os.environ.get("SHORTLINK_URL_3", "cpmshort.com")
SHORTLINK_API_3 = os.environ.get("SHORTLINK_API_3", "0830a2118d5a130ea4d756b07d984252c1adc26b")

# Shortener 4
SHORTLINK_URL_4 = os.environ.get("SHORTLINK_URL_4", "nowshort.com")
SHORTLINK_API_4 = os.environ.get("SHORTLINK_API_4", "2778c1f0ee5be3c70fa8c84f026d1794a57fcf2b")

# Shortener 5
SHORTLINK_URL_5 = os.environ.get("SHORTLINK_URL_5", "vplink.in")
SHORTLINK_API_5 = os.environ.get("SHORTLINK_API_5", "363faa03debfedecf6f42b7d9739ad0ea5bbf48f")

# Shortener 6
SHORTLINK_URL_6 = os.environ.get("SHORTLINK_URL_6", "alpha-links.in")
SHORTLINK_API_6 = os.environ.get("SHORTLINK_API_6", "483cba84c70761bfb95ec7a528478b00c348c41f")

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

TUT_VID = os.environ.get("TUT_VID", "https://t.me/DDNationalOfficial/9")
SHORT_MSG = "<b><blockquote>⌯ ʜᴇʀᴇ ɪꜱ ʏᴏᴜʀ ʟɪɴᴋ, ɪꜰ ʏᴏᴜ ᴀʀᴇ ɴᴇᴡ ʜᴇʀᴇ ᴛʜᴇɴ ʏᴏᴜ ᴍᴜꜱᴛ ᴡᴀᴛᴄʜ ᴛᴜᴛᴏʀɪᴀʟ ʙᴇꜰᴏʀᴇ ᴄʟɪᴄᴋɪɴɢ ᴏɴ ᴅᴏᴡɴʟᴏᴀᴅ...</blockquote></b>"

SHORTENER_PIC = os.environ.get("SHORTENER_PIC", "https://i.ibb.co/LD7Nsqm0/Ani-Wallpaper-dfc7d4-hd-Blaze-update-Z.jpg")
# --------------------------------------------

# --------------------------------------------
HELP_TXT = "<b><blockquote>ɪ ᴀᴍ ᴀ ʙᴏᴛ ᴡᴏʀᴋ ғᴏʀ @TheEroticBhabhiOfficial\n\n❏ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs\n├/start : sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\n├/about : ᴏᴜʀ Iɴғᴏʀᴍᴀᴛɪᴏɴ\n└/help : ʜᴇʟᴘ ʀᴇʟᴀᴛᴇᴅ ʙᴏᴛ\n\n sɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴏɴ ʟɪɴᴋ ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴊᴏɪɴ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴛʜᴀᴛs ɪᴛ.....!\n\n ᴅᴇᴠᴇʟᴏᴘᴇᴅ ʙʏ <a href=https://t.me/TheEroticBhabhiOfficial>TheEroticBhabhi</a></blockquote></b>"
ABOUT_TXT = (
    f"<blockquote>ℹ️ <b>{small_caps('sʏsᴛᴇᴍ ɪɴғᴏʀᴍᴀᴛɪᴏɴ')}</b></blockquote>\n\n"
    f"<blockquote>{small_caps('ᴀᴅᴠᴀɴᴄᴇᴅ ᴄᴏɴᴛᴇɴᴛ ᴅᴇʟɪᴠᴇʀʏ sʏsᴛᴇᴍ ᴏᴘᴇʀᴀᴛɪɴɢ ғᴏʀ')} @DDNationalFreeDish</blockquote>\n\n"
    f"<blockquote>👑 <b>{small_caps('ᴅᴇᴠᴇʟᴏᴘᴇʀ')}</b> — <a href='https://t.me/OfficialAdminDMRoBot'>{small_caps('ᴀᴅᴍɪɴ sᴜᴘᴘᴏʀᴛ')}</a></blockquote>"
)
# --------------------------------------------
# --------------------------------------------
START_MSG = (
    f"<blockquote>👤 <b>{small_caps('ᴡᴇʟᴄᴏᴍᴇ')}</b></blockquote>\n\n"
    f"<blockquote>{small_caps('ʜɪ')} {{mention}}, {small_caps('ɪ ᴀᴍ ᴛʜᴇ ᴏғғɪᴄɪᴀʟ ᴀssɪsᴛᴀɴᴛ ғᴏʀ')} @DDNationalFreeDish</blockquote>\n"
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
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "<b>• ʙʏ @DDNationalFreeDish</b>")
PROTECT_CONTENT = True if os.environ.get('PROTECT_CONTENT', "True") == "True" else False
# --------------------------------------------
DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", None) == 'True'
# --------------------------------------------
BOT_STATS_TEXT = f"<blockquote>⏳ <b>{small_caps('sʏsᴛᴇᴍ ᴜᴘᴛɪᴍᴇ')}</b>\n{{uptime}}</blockquote>"
USER_REPLY_TEXT = f"<blockquote>⛔ <b>{small_caps('ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ')}</b>\n{small_caps('ᴀᴅᴍɪɴ ᴘʀɪᴠɪʟᴇɢᴇs ʀᴇǫᴜɪʀᴇᴅ.')}</blockquote>"

# ==========================(BUY PREMIUM)====================#

OWNER_TAG = os.environ.get("OWNER_TAG", "OfficialAdminDMRoBot")
UPI_ID = os.environ.get("UPI_ID", "uneven@ikwik")
QR_PIC = os.environ.get("QR_PIC", "https://i.ibb.co/ZR2x7YSJ/photo-2026-01-03-23-54-09.jpg")
SCREENSHOT_URL = os.environ.get("SCREENSHOT_URL", f"t.me/OfficialAdminDMRoBot")
# --------------------------------------------
# Time and its price
# 7 Days
PRICE1 = os.environ.get("PRICE1", "₹ 60")
# 1 Month
PRICE2 = os.environ.get("PRICE2", "₹ 110")
# 3 Month
PRICE3 = os.environ.get("PRICE3", "₹ 260")
# 6 Month
PRICE4 = os.environ.get("PRICE4", "₹ 500")
# 1 Year
PRICE5 = os.environ.get("PRICE5", "₹ 900")

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
