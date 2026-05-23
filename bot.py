
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

from aiohttp import web
from plugins import web_server
import asyncio
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.types import BotCommand
import sys
import pytz
from datetime import datetime
from config import *
from database.db_premium import *
from database.database import *
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

logging.getLogger("apscheduler").setLevel(logging.WARNING)

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
scheduler.add_job(remove_expired_users, "interval", seconds=10)


# Daily reset at 00:00 IST — counters only, not bans or cooldowns
async def daily_reset_task():
    try:
        await db.reset_all_verify_counts()
    except Exception:
        pass
    try:
        await db.reset_all_daily_stats()
    except Exception:
        pass


scheduler.add_job(daily_reset_task, "cron", hour=0, minute=0)


# Monthly referral reset — runs on the 1st of every month at 00:01 IST
# Clears monthly invite/validate counts so milestones are fresh for the new month.
# All-time invited lists (for de-dup) are preserved.
async def monthly_referral_reset_task():
    try:
        await db.reset_monthly_referral_stats()
        LOGGER(__name__).info("Monthly referral stats reset completed.")
    except Exception as e:
        LOGGER(__name__).warning(f"Monthly referral reset failed: {e}")


scheduler.add_job(monthly_referral_reset_task, "cron", day=1, hour=0, minute=1)


def get_indian_time():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)


BOT_COMMANDS = [
    BotCommand("start",          "ꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ / ꜰᴇᴛᴄʜ ᴀ ꜰɪʟᴇ"),
    BotCommand("myplan",         "ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ꜱᴛᴀᴛᴜꜱ"),
    BotCommand("count",          "(ᴀᴅᴍɪɴ) ᴅᴀɪʟʏ ᴄᴏᴜɴᴛꜱ ᴅᴀꜱʜʙᴏᴀʀᴅ"),
    BotCommand("stats",          "(ᴀᴅᴍɪɴ) ʙᴏᴛ ᴜᴘᴛɪᴍᴇ"),
    BotCommand("users",          "(ᴀᴅᴍɪɴ) ᴛᴏᴛᴀʟ ᴜꜱᴇʀ ᴄᴏᴜɴᴛ"),
    BotCommand("broadcast",      "(ᴀᴅᴍɪɴ) ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀꜱ"),
    BotCommand("dbroadcast",     "(ᴀᴅᴍɪɴ) ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ʙʀᴏᴀᴅᴄᴀꜱᴛ"),
    BotCommand("pbroadcast",     "(ᴀᴅᴍɪɴ) ᴘɪɴ ʙʀᴏᴀᴅᴄᴀꜱᴛ"),
    BotCommand("batch",          "(ᴀᴅᴍɪɴ) ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʙᴀᴛᴄʜ ʟɪɴᴋ"),
    BotCommand("genlink",        "(ᴀᴅᴍɪɴ) ɢᴇɴᴇʀᴀᴛᴇ ᴀ ꜱɪɴɢʟᴇ ʟɪɴᴋ"),
    BotCommand("custom_batch",   "(ᴀᴅᴍɪɴ) ᴄᴜꜱᴛᴏᴍ ʙᴀᴛᴄʜ ʟɪɴᴋ"),
    BotCommand("dlt_time",       "(ᴀᴅᴍɪɴ) ꜱᴇᴛ ꜰɪʟᴇ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ"),
    BotCommand("check_dlt_time", "(ᴀᴅᴍɪɴ) ᴄʜᴇᴄᴋ ᴄᴜʀʀᴇɴᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ"),
    BotCommand("ban",            "(ᴀᴅᴍɪɴ) ʙᴀɴ ᴀ ᴜꜱᴇʀ"),
    BotCommand("unban",          "(ᴀᴅᴍɪɴ) ᴜɴʙᴀɴ ᴀ ᴜꜱᴇʀ"),
    BotCommand("banlist",        "(ᴀᴅᴍɪɴ) ʟɪꜱᴛ ʙᴀɴɴᴇᴅ ᴜꜱᴇʀꜱ"),
    BotCommand("addchnl",        "(ᴀᴅᴍɪɴ) ᴀᴅᴅ ꜰᴏʀᴄᴇ-ꜱᴜʙ ᴄʜᴀɴɴᴇʟ"),
    BotCommand("delchnl",        "(ᴀᴅᴍɪɴ) ʀᴇᴍᴏᴠᴇ ꜰᴏʀᴄᴇ-ꜱᴜʙ ᴄʜᴀɴɴᴇʟ"),
    BotCommand("listchnl",       "(ᴀᴅᴍɪɴ) ʟɪꜱᴛ ꜰᴏʀᴄᴇ-ꜱᴜʙ ᴄʜᴀɴɴᴇʟꜱ"),
    BotCommand("fsub_mode",      "(ᴀᴅᴍɪɴ) ᴛᴏɢɢʟᴇ ʀᴇQᴜᴇꜱᴛ-ꜰꜱᴜʙ ᴍᴏᴅᴇ"),
    BotCommand("delreq",         "(ᴀᴅᴍɪɴ) ᴅᴇʟᴇᴛᴇ ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛꜱ"),
    BotCommand("addpremium",     "(ᴀᴅᴍɪɴ) ɢʀᴀɴᴛ ᴘʀᴇᴍɪᴜᴍ"),
    BotCommand("remove_premium", "(ᴀᴅᴍɪɴ) ʀᴇᴠᴏᴋᴇ ᴘʀᴇᴍɪᴜᴍ"),
    BotCommand("premium_users",  "(ᴀᴅᴍɪɴ) ʟɪꜱᴛ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ"),
    BotCommand("add_admin",      "(ᴏᴡɴᴇʀ) ᴀᴅᴅ ᴀ ʙᴏᴛ ᴀᴅᴍɪɴ"),
    BotCommand("deladmin",       "(ᴏᴡɴᴇʀ) ʀᴇᴍᴏᴠᴇ ᴀ ʙᴏᴛ ᴀᴅᴍɪɴ"),
    BotCommand("admins",         "(ᴀᴅᴍɪɴ) ʟɪꜱᴛ ʙᴏᴛ ᴀᴅᴍɪɴꜱ"),
    BotCommand("hash",           "(ᴀᴅᴍɪɴ) ʜᴀꜱʜ ꜱᴇᴛᴛɪɴɢꜱ"),
]


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        scheduler.start()
        usr_bot_me = await self.get_me()
        self.uptime = get_indian_time()

        try:
            await self.set_bot_commands(BOT_COMMANDS)
            self.LOGGER(__name__).info(
                f"Registered {len(BOT_COMMANDS)} bot commands via setMyCommands."
            )
        except Exception as e:
            self.LOGGER(__name__).warning(f"setMyCommands failed: {e}")

        try:
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
            test = await self.send_message(chat_id=db_channel.id, text="Test Message")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(
                f"Make Sure bot is Admin in DB Channel, and Double check the CHANNEL_ID Value, "
                f"Current Value {CHANNEL_ID}"
            )
            self.LOGGER(__name__).info("\nBot Stopped.")
            sys.exit()

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username
        self.LOGGER(__name__).info(f"Bot Running..!")
        self.LOGGER(__name__).info("""

  ___ ___  ___  ___ ___ _    _____  _____  ___ _____ ___ 
 / __/ _ \\|   \\| __| __| |  |_ _\\ \\/ / _ \\/ _ \\_   _/ __|
| (_| (_) | |) | _|| _|| |__ | | >  <| _ \\ (_) || | \\__ \\
 \\___\\___/|___/|___|_| |____|___/_/\\_\\___/\\___/ |_| |___/
                                                         
        """)

        # Start Web Server
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        try:
            await self.send_message(OWNER_ID, text="<b><blockquote> ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ ⛈️</blockquote></b>")
        except Exception:
            pass

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        self.LOGGER(__name__).info("Bot is now running. Thanks to @rohit_1888")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Shutting down...")
        finally:
            loop.run_until_complete(self.stop())


#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
