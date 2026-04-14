# (©)CodeFlix_Bots
# rohit_1888 on Tg #Dont remove this line

import base64
import re
import asyncio
import time
import random
import string
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import *
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from shortzy import Shortzy
from pyrogram.errors import FloodWait
from database.database import *


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

async def check_admin(filter, client, update):
    try:
        user_id = update.from_user.id
        return any([user_id == OWNER_ID, await db.admin_exist(user_id)])
    except Exception as e:
        print(f"! Exception in check_admin: {e}")
        return False


async def is_subscribed(client, user_id):
    channel_ids = await db.show_channels()

    if not channel_ids:
        return True

    if user_id == OWNER_ID:
        return True

    for cid in channel_ids:
        if not await is_sub(client, user_id, cid):
            mode = await db.get_channel_mode(cid)
            if mode == "on":
                await asyncio.sleep(2)
                if await is_sub(client, user_id, cid):
                    continue
            return False

    return True


async def is_sub(client, user_id, channel_id):
    try:
        member = await client.get_chat_member(channel_id, user_id)
        status = member.status
        return status in {
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        }

    except UserNotParticipant:
        mode = await db.get_channel_mode(channel_id)
        if mode == "on":
            exists = await db.req_user_exist(channel_id, user_id)
            return exists
        return False

    except Exception as e:
        print(f"[!] Error in is_sub(): {e}")
        return False


async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string


async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    string = string_bytes.decode("ascii")
    return string


async def get_messages(client, message_ids):
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temb_ids = message_ids[total_messages:total_messages + 200]
        try:
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temb_ids
            )
        except FloodWait as e:
            await asyncio.sleep(e.x)
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temb_ids
            )
        except:
            pass
        total_messages += len(temb_ids)
        messages.extend(msgs)
    return messages


async def get_message_id(client, message):
    if message.forward_from_chat:
        if message.forward_from_chat.id == client.db_channel.id:
            return message.forward_from_message_id
        else:
            return 0
    elif message.forward_sender_name:
        return 0
    elif message.text:
        pattern = "https://t.me/(?:c/)?(.*)/(\d+)"
        matches = re.match(pattern, message.text)
        if not matches:
            return 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit():
            if f"-100{channel_id}" == str(client.db_channel.id):
                return msg_id
        else:
            if channel_id == client.db_channel.username:
                return msg_id
    else:
        return 0


def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time


def get_exp_time(seconds):
    periods = [('days', 86400), ('hours', 3600), ('mins', 60), ('secs', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)} {period_name}'
    return result


def _generate_alias(length: int = 8) -> str:
    """
    Generate an alias in the format  __XxXxXxXx__  (e.g. __bQwxVU0T__).

    The double-underscore wrapping is intentional:
    - As an inline-button URL the full link works perfectly (buttons are never
      markdown-parsed by Telegram).
    - If a user copies the URL text and pastes it into any Telegram chat or
      bot, Telegram's markdown parser treats __...__ as italic formatting,
      which corrupts the URL and defeats any copy-paste bypass attempt.

    The inner random part uses mixed-case letters + digits so it matches
    the appearance of a normal shortener token (e.g. bQwxVU0T).
    """
    chars = string.ascii_letters + string.digits
    inner = ''.join(random.choices(chars, k=length))
    return f"__{inner}__"


async def get_shortlink(url, api, link):
    shortzy = Shortzy(api_key=api, base_site=url)
    alias = _generate_alias()
    link = await shortzy.convert(link, alias=alias)
    return link


async def get_shortlink_for_user(user_id: int, long_url: str):
    """
    Pick the best shortener for this user using a 24-hour time-based rotation.

    Returns:
        (short_url: str, 0)            — a working shortened URL is ready.
        (None, wait_seconds: int)      — all shorteners are on cooldown;
                                         wait_seconds until the earliest one frees up.

    How it works:
    - Each user has a record of when they last used each shortener slot.
    - The bot picks the next slot in rotation order that is either:
        a) Never used by this user, OR
        b) Was used more than 24 hours ago by this user.
    - If ALL slots are within the 24-hour window the function returns
      (None, wait_seconds) so the caller can show a "come back later /
       buy premium" message instead of silently reusing a spent slot.
    - After a slot is picked it is timestamped immediately so the 24-hour
      cooldown starts from this exact moment.

    If only one shortener is configured it is used directly (original behaviour)
    and exhaustion is never signalled for single-provider setups.
    """
    providers = SHORTLINK_PROVIDERS
    total = len(providers)

    if total == 0:
        return (long_url, 0)  # no shortener configured — return as-is

    if total == 1:
        # Single provider — always use it (original behaviour, no exhaustion logic)
        provider = providers[0]
        short = await get_shortlink(provider["url"], provider["api"], long_url)
        return (short, 0)

    # Time-based pick — returns (idx, is_available, wait_seconds)
    idx, is_available, wait_seconds = await db.pick_shortener_for_user(user_id, total)

    if not is_available:
        # All shorteners are within their 24-hour cooldown for this user
        return (None, wait_seconds)

    provider = providers[idx]

    # Record this use BEFORE shortening (so the slot advances even on API error)
    await db.mark_shortener_used(user_id, idx)

    short = await get_shortlink(provider["url"], provider["api"], long_url)
    return (short, 0)


async def create_masked_link(target_url: str) -> str:
    """Generate a hashed masked link for the given target URL."""
    from plugins.crypto_hash import generate_hash_id
    from config import BASE_URL, LOGGER

    try:
        algorithm = await db.get_hash_algorithm()
        hash_id = generate_hash_id(algorithm, target_url)
        await db.store_masked_link(hash_id, target_url, algorithm)

        base = BASE_URL.rstrip('/') if BASE_URL else ""
        if not base:
            LOGGER(__name__).warning("BASE_URL is not set! Masked link will not work.")
            return target_url
        if not base.startswith("http"):
            base = f"https://{base}"

        return f"{base}/r/{hash_id}"

    except Exception as e:
        LOGGER(__name__).error(f"Masking Error: {e}")
        return target_url


subscribed = filters.create(is_subscribed)
admin = filters.create(check_admin)

# rohit_1888 on Tg :

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
