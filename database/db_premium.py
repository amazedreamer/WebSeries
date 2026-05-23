import motor.motor_asyncio
from config import DB_URI, DB_NAME
from pytz import timezone
from datetime import datetime, timedelta

dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]
collection = database['premium-users']
sp_collection = database['super-premium-users']


async def is_premium_user(user_id):
    user = await collection.find_one({"user_id": user_id})
    return user is not None


async def remove_premium(user_id):
    await collection.delete_one({"user_id": user_id})


async def remove_expired_users():
    ist = timezone("Asia/Kolkata")
    current_time = datetime.now(ist)
    async for user in collection.find({}):
        expiration = user.get("expiration_timestamp")
        if not expiration:
            continue
        try:
            expiration_time = datetime.fromisoformat(expiration).astimezone(ist)
            if expiration_time <= current_time:
                await collection.delete_one({"user_id": user["user_id"]})
        except Exception as e:
            print(f"Error removing user {user.get('user_id')}: {e}")


async def list_premium_users():
    ist = timezone("Asia/Kolkata")
    premium_users = collection.find({})
    premium_user_list = []
    async for user in premium_users:
        user_id = user["user_id"]
        expiration_timestamp = user["expiration_timestamp"]
        expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
        remaining_time = expiration_time - datetime.now(ist)
        if remaining_time.total_seconds() > 0:
            days, hours, minutes, seconds = (
                remaining_time.days,
                remaining_time.seconds // 3600,
                (remaining_time.seconds // 60) % 60,
                remaining_time.seconds % 60,
            )
            expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"
            formatted_expiry_time = expiration_time.strftime('%Y-%m-%d %H:%M:%S %p IST')
            premium_user_list.append(
                f"UserID: {user_id} - Expiry: {expiry_info} (Expires at {formatted_expiry_time})"
            )
    return premium_user_list


async def add_premium(user_id, time_value, time_unit):
    """
    Add a premium user for a specific duration.
    time_unit: 's'=seconds, 'm'=minutes, 'h'=hours, 'd'=days, 'y'=years.
    """
    time_unit = time_unit.lower()
    ist = timezone("Asia/Kolkata")
    now = datetime.now(ist)

    if time_unit == 's':
        expiration_time = now + timedelta(seconds=time_value)
    elif time_unit == 'm':
        expiration_time = now + timedelta(minutes=time_value)
    elif time_unit == 'h':
        expiration_time = now + timedelta(hours=time_value)
    elif time_unit == 'd':
        expiration_time = now + timedelta(days=time_value)
    elif time_unit == 'y':
        expiration_time = now + timedelta(days=365 * time_value)
    else:
        raise ValueError("Invalid time unit. Use 's', 'm', 'h', 'd', or 'y'.")

    premium_data = {
        "user_id": user_id,
        "expiration_timestamp": expiration_time.isoformat(),
    }
    await collection.update_one(
        {"user_id": user_id},
        {"$set": premium_data},
        upsert=True
    )
    return expiration_time.strftime('%Y-%m-%d %H:%M:%S %p IST')


# ═══════════════════════════════════════════════════════════
# SUPER PREMIUM
# ═══════════════════════════════════════════════════════════

async def is_super_premium_user(user_id) -> bool:
    user = await sp_collection.find_one({"user_id": user_id})
    if not user:
        return False
    expiration_timestamp = user.get("expiration_timestamp")
    if not expiration_timestamp:
        return False
    try:
        ist = timezone("Asia/Kolkata")
        expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
        return expiration_time > datetime.now(ist)
    except Exception:
        return False


async def add_super_premium(user_id: int, days: int) -> str:
    ist = timezone("Asia/Kolkata")
    now = datetime.now(ist)
    expiration_time = now + timedelta(days=int(days))
    await sp_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "expiration_timestamp": expiration_time.isoformat(),
        }},
        upsert=True
    )
    return expiration_time.strftime('%Y-%m-%d %H:%M:%S IST')


async def remove_super_premium(user_id: int):
    await sp_collection.delete_one({"user_id": user_id})


async def list_super_premium_users() -> list:
    ist = timezone("Asia/Kolkata")
    result = []
    async for user in sp_collection.find({}):
        user_id = user.get("user_id")
        ts = user.get("expiration_timestamp")
        if not ts:
            continue
        try:
            exp = datetime.fromisoformat(ts).astimezone(ist)
            remaining = exp - datetime.now(ist)
            if remaining.total_seconds() <= 0:
                continue
            d, h, m, s = (
                remaining.days,
                remaining.seconds // 3600,
                (remaining.seconds // 60) % 60,
                remaining.seconds % 60,
            )
            result.append(
                f"UserID: {user_id} — {d}d {h}h {m}m left "
                f"(Expires {exp.strftime('%Y-%m-%d %H:%M IST')})"
            )
        except Exception:
            continue
    return result


async def check_super_premium_plan(user_id: int) -> str:
    user = await sp_collection.find_one({"user_id": user_id})
    if not user:
        return "ʏᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴀ sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ."
    ts = user.get("expiration_timestamp")
    if not ts:
        return "ʏᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴀ sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ."
    try:
        ist = timezone("Asia/Kolkata")
        exp = datetime.fromisoformat(ts).astimezone(ist)
        remaining = exp - datetime.now(ist)
        if remaining.total_seconds() <= 0:
            return "ʏᴏᴜʀ sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ʜᴀs ᴇxᴘɪʀᴇᴅ."
        d, h, m, s = (
            remaining.days,
            remaining.seconds // 3600,
            (remaining.seconds // 60) % 60,
            remaining.seconds % 60,
        )
        return (
            f"🚀 sᴜᴘᴇʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴇ — {d}d {h}h {m}m {s}s ʀᴇᴍᴀɪɴɪɴɢ.\n"
            f"ᴇxᴘɪʀᴇs: {exp.strftime('%Y-%m-%d %H:%M:%S IST')}"
        )
    except Exception as e:
        return f"ᴇʀʀᴏʀ ᴄʜᴇᴄᴋɪɴɢ ᴘʟᴀɴ: {e}"


async def remove_expired_super_premium_users():
    ist = timezone("Asia/Kolkata")
    now = datetime.now(ist)
    async for user in sp_collection.find({}):
        ts = user.get("expiration_timestamp")
        if not ts:
            await sp_collection.delete_one({"user_id": user.get("user_id")})
            continue
        try:
            exp = datetime.fromisoformat(ts).astimezone(ist)
            if exp <= now:
                await sp_collection.delete_one({"user_id": user.get("user_id")})
        except Exception:
            pass


async def check_user_plan(user_id):
    user = await collection.find_one({"user_id": user_id})
    if user:
        expiration_timestamp = user["expiration_timestamp"]
        expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(timezone("Asia/Kolkata"))
        remaining_time = expiration_time - datetime.now(timezone("Asia/Kolkata"))
        if remaining_time.total_seconds() > 0:
            days, hours, minutes, seconds = (
                remaining_time.days,
                remaining_time.seconds // 3600,
                (remaining_time.seconds // 60) % 60,
                remaining_time.seconds % 60,
            )
            return f"ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ɪs ᴀᴄᴛɪᴠᴇ. {days}d {hours}h {minutes}m {seconds}s ʟᴇꜰᴛ."
        else:
            return "ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ʜᴀs ᴇxᴘɪʀᴇᴅ."
    else:
        return "ʏᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ."
