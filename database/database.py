# Codeflix_Botz
# rohit_1888 on Tg

import motor, asyncio
import motor.motor_asyncio
import time
import pymongo, os
from config import DB_URI, DB_NAME
import logging
from datetime import datetime, timedelta

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]

logging.basicConfig(level=logging.INFO)

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

SHORTENER_COOLDOWN_SECONDS = 86400  # 24 hours


def new_user(id):
    return {
        '_id': id,
        'verify_status': {
            'is_verified': False,
            'verified_time': "",
            'verify_token': "",
            'link': ""
        }
    }


class Rohit:

    def __init__(self, DB_URI, DB_NAME):
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
        self.database = self.dbclient[DB_NAME]

        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.user_data = self.database['users']
        self.sex_data = self.database['sex']
        self.banned_user_data = self.database['banned_user']
        self.autho_user_data = self.database['autho_user']
        self.del_timer_data = self.database['del_timer']
        self.fsub_data = self.database['fsub']
        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.hash_settings = self.database['hash_settings']
        self.masked_links = self.database['masked_links']
        self.fingerprint_tokens = self.database['fingerprint_tokens']
        # Per-user shortener usage tracker (time-based rotation)
        self.shortener_tracker = self.database['shortener_tracker']

    # USER DATA
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id})
        return

    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in user_docs]
        return user_ids

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})
        return

    # ADMIN DATA
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})
            return

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})
            return

    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids

    # BAN USER DATA
    async def ban_user_exist(self, user_id: int):
        found = await self.banned_user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_ban_user(self, user_id: int):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id})
            return

    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})
            return

    async def get_ban_users(self):
        users_docs = await self.banned_user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids

    # AUTO DELETE TIMER SETTINGS
    async def set_del_timer(self, value: int):
        existing = await self.del_timer_data.find_one({})
        if existing:
            await self.del_timer_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.del_timer_data.insert_one({'value': value})

    async def get_del_timer(self):
        data = await self.del_timer_data.find_one({})
        if data:
            return data.get('value', 600)
        return 0

    # CHANNEL MANAGEMENT
    async def channel_exist(self, channel_id: int):
        found = await self.fsub_data.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.fsub_data.insert_one({'_id': channel_id})
            return

    async def rem_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.fsub_data.delete_one({'_id': channel_id})
            return

    async def show_channels(self):
        channel_docs = await self.fsub_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    async def get_channel_mode(self, channel_id: int):
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # REQUEST FORCE-SUB MANAGEMENT
    async def req_user(self, channel_id: int, user_id: int):
        try:
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            print(f"[DB ERROR] Failed to add user to request list: {e}")

    async def del_req_user(self, channel_id: int, user_id: int):
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id},
            {'$pull': {'user_ids': user_id}}
        )

    async def req_user_exist(self, channel_id: int, user_id: int):
        try:
            found = await self.rqst_fsub_Channel_data.find_one({
                '_id': int(channel_id),
                'user_ids': int(user_id)
            })
            return bool(found)
        except Exception as e:
            print(f"[DB ERROR] Failed to check request list: {e}")
            return False

    async def reqChannel_exist(self, channel_id: int):
        channel_ids = await self.show_channels()
        return channel_id in channel_ids

    # VERIFICATION MANAGEMENT
    async def db_verify_status(self, user_id):
        user = await self.user_data.find_one({'_id': user_id})
        if user:
            return user.get('verify_status', default_verify)
        return default_verify

    async def db_update_verify_status(self, user_id, verify):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

    async def get_verify_status(self, user_id):
        verify = await self.db_verify_status(user_id)
        return verify

    async def update_verify_status(self, user_id, verify_token="", is_verified=False, verified_time=0, link=""):
        current = await self.db_verify_status(user_id)
        current['verify_token'] = verify_token
        current['is_verified'] = is_verified
        current['verified_time'] = verified_time
        current['link'] = link
        await self.db_update_verify_status(user_id, current)

    async def set_verify_count(self, user_id: int, count: int):
        await self.sex_data.update_one({'_id': user_id}, {'$set': {'verify_count': count}}, upsert=True)

    async def get_verify_count(self, user_id: int):
        user = await self.sex_data.find_one({'_id': user_id})
        if user:
            return user.get('verify_count', 0)
        return 0

    async def reset_all_verify_counts(self):
        await self.sex_data.update_many({}, {'$set': {'verify_count': 0}})

    async def get_total_verify_count(self):
        pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$verify_count"}}}
        ]
        result = await self.sex_data.aggregate(pipeline).to_list(length=1)
        return result[0]["total"] if result else 0

    # HASH ALGORITHM SETTINGS
    async def set_hash_algorithm(self, algo: str):
        await self.hash_settings.update_one(
            {'_id': 'current_algo'},
            {'$set': {'value': algo}},
            upsert=True
        )

    async def get_hash_algorithm(self):
        data = await self.hash_settings.find_one({'_id': 'current_algo'})
        if data:
            return data.get('value', 'sha256')
        return 'sha256'

    # MASKED LINKS
    async def store_masked_link(self, hash_id: str, target: str, algorithm: str):
        await self.masked_links.insert_one({
            '_id': hash_id,
            'target': target,
            'algorithm': algorithm,
            'created_at': time.time()
        })

    async def get_masked_link(self, hash_id: str):
        return await self.masked_links.find_one({'_id': hash_id})

    async def mark_link_used(self, hash_id: str):
        await self.masked_links.update_one(
            {'_id': hash_id},
            {'$set': {'used': True, 'used_at': time.time()}}
        )

    # FINGERPRINT TOKENS
    async def store_fp_token(self, token: str, hash_id: str, expires: float):
        await self.fingerprint_tokens.insert_one({
            '_id': token,
            'hash_id': hash_id,
            'expires': expires,
            'used': False
        })

    async def validate_fp_token(self, token: str, hash_id: str):
        doc = await self.fingerprint_tokens.find_one({'_id': token})
        if not doc:
            return False
        if doc['hash_id'] != hash_id:
            return False
        if doc.get('used', False):
            return False
        if time.time() > doc['expires']:
            await self.fingerprint_tokens.delete_one({'_id': token})
            return False
        await self.fingerprint_tokens.update_one(
            {'_id': token},
            {'$set': {'used': True}}
        )
        return True

    # ================================================================
    # PER-USER SHORTENER ROTATION — TIME-BASED (24-hour cooldown)
    #
    # Each user gets a rotating slot through all active shorteners.
    # Once a shortener is used for a user, it is locked for 24 hours
    # for that specific user, so the shortener never gets repeated
    # impressions from the same person within a single day.
    #
    # DB document shape (one per user):
    # {
    #   _id: user_id,
    #   last_used_idx: 0,          # index that was last served
    #   times: {
    #     "0": 1700000000.0,        # unix timestamp of last use for slot 0
    #     "1": 0.0,                 # 0 means never used
    #     ...
    #   }
    # }
    # ================================================================

    async def _get_tracker_doc(self, user_id: int) -> dict:
        doc = await self.shortener_tracker.find_one({'_id': user_id})
        return doc or {}

    async def pick_shortener_for_user(self, user_id: int, total_providers: int) -> int:
        """
        Return the index of the best shortener to use for this user right now.

        Selection logic:
        1. Start from the slot AFTER the one last served (round-robin starting point).
        2. Walk through all slots and pick the FIRST one whose last-use timestamp
           is either 0 (never used) or older than 24 hours.
        3. If ALL slots are within the 24-hour window (extremely rare — would require
           the same user going through every shortener in under a day), fall back to
           the slot with the OLDEST timestamp so the gap is still maximised.

        This guarantees a 24-hour gap between successive uses of the same shortener
        for the same user, so each shortener gets a unique impression count.
        """
        now = time.time()
        doc = await self._get_tracker_doc(user_id)
        last_idx = doc.get('last_used_idx', -1)
        times = doc.get('times', {})

        # Build a list of (candidate_index, last_used_timestamp) in rotation order
        # starting right after the last served slot.
        candidates = []
        for offset in range(total_providers):
            idx = (last_idx + 1 + offset) % total_providers
            last_used = times.get(str(idx), 0.0)
            candidates.append((idx, last_used))

        # Prefer first slot that is available (never used or 24h+ ago)
        for idx, last_used in candidates:
            if last_used == 0.0 or (now - last_used) >= SHORTENER_COOLDOWN_SECONDS:
                return idx

        # All slots are within 24h — return the one used longest ago (minimum wait)
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    async def mark_shortener_used(self, user_id: int, idx: int):
        """Record that shortener `idx` was just served to `user_id`."""
        now = time.time()
        await self.shortener_tracker.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'last_used_idx': idx,
                    f'times.{idx}': now,
                }
            },
            upsert=True
        )


db = Rohit(DB_URI, DB_NAME)
