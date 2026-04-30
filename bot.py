
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
#rohit_1888 on Tg
from config import *
from database.db_premium import *
from database.database import *
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

# Suppress APScheduler logs below WARNING level
logging.getLogger("apscheduler").setLevel(logging.WARNING)

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
scheduler.add_job(remove_expired_users, "interval", seconds=10)

# Reset every daily counter (verify counts, per-shortener counts, premium
# access records, sequential shortener progress) at 00:00 IST.
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


def get_indian_time():
    """Returns the current time in IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)


name = """
 BY CODEFLIX BOTS
"""

# ---------------------------------------------------------------------------
# Telegram bot command menu (auto-registered on every startup via setMyCommands)
# Order roughly mirrors the existing CMD_TXT help screen.
# ---------------------------------------------------------------------------
BOT_COMMANDS = [
    BotCommand("start",          "Start the bot / fetch a file"),
    BotCommand("myplan",         "Check your premium plan status"),
    BotCommand("count",          "(Admin) daily counts dashboard"),
    BotCommand("stats",          "(Admin) bot uptime"),
    BotCommand("users",          "(Admin) total user count"),
    BotCommand("broadcast",      "(Admin) broadcast to all users"),
    BotCommand("dbroadcast",     "(Admin) auto-delete broadcast"),
    BotCommand("pbroadcast",     "(Admin) pin broadcast"),
    BotCommand("batch",          "(Admin) generate a batch link"),
    BotCommand("genlink",        "(Admin) generate a single link"),
    BotCommand("custom_batch",   "(Admin) custom batch link"),
    BotCommand("dlt_time",       "(Admin) set file auto-delete timer"),
    BotCommand("check_dlt_time", "(Admin) check current delete timer"),
    BotCommand("ban",            "(Admin) ban a user"),
    BotCommand("unban",          "(Admin) unban a user"),
    BotCommand("banlist",        "(Admin) list banned users"),
    BotCommand("addchnl",        "(Admin) add force-sub channel"),
    BotCommand("delchnl",        "(Admin) remove force-sub channel"),
    BotCommand("listchnl",       "(Admin) list force-sub channels"),
    BotCommand("fsub_mode",      "(Admin) toggle request-fsub mode"),
    BotCommand("delreq",         "(Admin) delete pending join requests"),
    BotCommand("addpremium",     "(Admin) grant premium to a user"),
    BotCommand("remove_premium", "(Admin) revoke premium from a user"),
    BotCommand("premium_users",  "(Admin) list premium users"),
    BotCommand("add_admin",      "(Owner) add a bot admin"),
    BotCommand("deladmin",       "(Owner) remove a bot admin"),
    BotCommand("admins",         "(Admin) list bot admins"),
    BotCommand("hash",           "(Admin) hash settings"),
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

        # Register the bot's command menu with Telegram on every startup so
        # the suggestion list users see in the input box always matches the
        # handlers actually wired up below.
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
            test = await self.send_message(chat_id = db_channel.id, text = "Test Message")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(f"Make Sure bot is Admin in DB Channel, and Double check the CHANNEL_ID Value, Current Value {CHANNEL_ID}")
            self.LOGGER(__name__).info("\nBot Stopped.")
            sys.exit()

        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Bot Running..!")
        self.LOGGER(__name__).info(f"""       


  ___ ___  ___  ___ ___ _    _____  _____  ___ _____ ___ 
 / __/ _ \|   \| __| __| |  |_ _\ \/ / _ )/ _ \_   _/ __|
| (_| (_) | |) | _|| _|| |__ | | >  <| _ \ (_) || | \__ \
 \___\___/|___/|___|_| |____|___/_/\_\___/\___/ |_| |___/
                                                         
 
                                          """)

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username
        self.LOGGER(__name__).info(f"Bot Running..!")   

        # Start Web Server
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()


        try: await self.send_message(OWNER_ID, text = f"<b><blockquote> Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ ⛈️</blockquote></b>")
        except: pass

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        """Run the bot."""
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
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.
