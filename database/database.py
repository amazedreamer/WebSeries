# Codeflix_Botz
# rohit_1888 on Tg

import motor, asyncio
import motor.motor_asyncio
import time
import pymongo, os
from config import DB_URI, DB_NAME
import logging
from datetime import datetime, timedelta
from pytz import timezone as _tz

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]

logging.basicConfig(level=logging.INFO)

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}


def _today_ist() -> str:
    return datetime.now(_tz("Asia/Kolkata")).strftime("%Y-%m-%d")


def _current_month_ist() -> str:
    return datetime.now(_tz("Asia/Kolkata")).strftime("%Y-%m")


def new_user(id):
    return {
        '_id': id,
        'verify_status': {
            'is_verified': False,
            'verified_time': 0,
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
        self.shortener_progress = self.database['shortener_progress']
        self.daily_stats = self.database['daily_stats']
        self.premium_access = self.database['premium_access']
        self.pending_shortener = self.database['pending_shortener']
        self.shortener_cooldowns = self.database['shortener_cooldowns']
        self.bypass_bans = self.database['bypass_bans']
        self.shortener_access = self.database['shortener_access']

        # ── Referral system ──────────────────────────────────────────────────
        # referrals: { _id: referrer_id,
        #              invite_code: "ref<user_id>",
        #              all_time_invited: [invitee_id, ...],  # ever joined via this link
        #              monthly: { "YYYY-MM": { invited: [ids], validated: [ids] } }
        #              rewards_given: { "YYYY-MM": [3, 10, 40] }  # milestones rewarded this month
        #            }
        self.referrals = self.database['referrals']

        # ── Paytm auto-payment orders ─────────────────────────────────────────
        # paytm_orders: { order_id: str (PK), user_id, amount, days,
        #                 plan_key, plan_type, status: pending/success/expired/cancelled,
        #                 created_at, txn_id (on success) }
        self.orders = self.database['paytm_orders']

        # referral_joins: { _id: invitee_id,
        #                   referrer_id: int,
        #                   joined_at: ts,
        #                   validated: bool,
        #                   plan_bought: bool }
        self.referral_joins = self.database['referral_joins']

        # invite_channel_settings: { _id: "settings", channel_id: int, mode: "bot"|"channel" }
        self.invite_channel_settings = self.database['invite_channel_settings']

        # user_channel_invites: { _id: user_id (referrer),
        #                         channel_id: int,
        #                         invite_link: str,   ← unique link created per user
        #                         created_at: float,
        #                         joined_users: [invitee_id, ...] }
        # Queried both by _id (user→link) and invite_link field (link→user)
        self.user_channel_invites = self.database['user_channel_invites']

        # payment_requests: { _id: user_id,
        #                     plan_key: str, plan_type: str, days: int, amount: int,
        #                     status: "pending"|"approved"|"rejected",
        #                     requested_at: ts,
        #                     admin_msg_ids: [(admin_id, msg_id), ...] }
        self.payment_requests = self.database['payment_requests']

        # bot_mode_settings: { _id: 'bot_mode', mode: 'free'|'token'|'premium' }
        #                     { _id: 'premium_free_limit', limit: int }
        self.bot_mode_settings = self.database['bot_mode_settings']

        # user_free_access: { _id: user_id, count: int }
        # Tracks how many free files a user has accessed in Premium Mode
        self.user_free_access = self.database['user_free_access']

    # ═══════════════════════════════════════════════════════════
    # USER DATA
    # ═══════════════════════════════════════════════════════════
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id})

    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        return [doc['_id'] for doc in user_docs]

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})

    # ═══════════════════════════════════════════════════════════
    # ADMIN DATA
    # ═══════════════════════════════════════════════════════════
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})

    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        return [doc['_id'] for doc in users_docs]

    # ═══════════════════════════════════════════════════════════
    # BAN USER DATA
    # ═══════════════════════════════════════════════════════════
    async def ban_user_exist(self, user_id: int):
        found = await self.banned_user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_ban_user(self, user_id: int):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id})

    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})

    async def get_ban_users(self):
        users_docs = await self.banned_user_data.find().to_list(length=None)
        return [doc['_id'] for doc in users_docs]

    # ── Full unban: clear both ban lists + bypass bans ───────────────────────
    async def full_unban_user(self, user_id: int):
        """Remove a user from ALL ban stores: manual ban list + bypass-protection bans."""
        await self.banned_user_data.delete_one({'_id': user_id})
        await self.bypass_bans.delete_one({'_id': user_id})

    async def get_all_bypass_bans(self) -> list:
        """Return all active bypass-protection bans (permanent + non-expired timed bans)."""
        now = time.time()
        docs = await self.bypass_bans.find({
            '$or': [
                {'permanent': True},
                {'banned_until': {'$gt': now}}
            ]
        }).to_list(length=None)
        return docs

    async def is_any_banned(self, user_id: int) -> bool:
        """Return True if the user is in EITHER the manual ban list OR an active bypass ban."""
        if await self.ban_user_exist(user_id):
            return True
        bypass = await self.get_bypass_ban(user_id)
        return bypass is not None

    # ═══════════════════════════════════════════════════════════
    # AUTO DELETE TIMER SETTINGS
    # ═══════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════
    # CHANNEL MANAGEMENT
    # ═══════════════════════════════════════════════════════════
    async def channel_exist(self, channel_id: int):
        found = await self.fsub_data.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.fsub_data.insert_one({'_id': channel_id})

    async def rem_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.fsub_data.delete_one({'_id': channel_id})

    async def del_channel(self, channel_id: int):
        await self.rem_channel(channel_id)

    async def show_channels(self):
        channel_docs = await self.fsub_data.find().to_list(length=None)
        return [doc['_id'] for doc in channel_docs]

    async def get_channel_mode(self, channel_id: int):
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # ═══════════════════════════════════════════════════════════
    # REQUEST FORCE-SUB MANAGEMENT
    # ═══════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════
    # VERIFICATION MANAGEMENT
    # ═══════════════════════════════════════════════════════════
    async def db_verify_status(self, user_id):
        user = await self.user_data.find_one({'_id': user_id})
        if user:
            return user.get('verify_status', default_verify)
        return default_verify

    async def db_update_verify_status(self, user_id, verify):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

    async def get_verify_status(self, user_id):
        return await self.db_verify_status(user_id)

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
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$verify_count"}}}]
        result = await self.sex_data.aggregate(pipeline).to_list(length=1)
        return result[0]["total"] if result else 0

    # ═══════════════════════════════════════════════════════════
    # HASH ALGORITHM SETTINGS
    # ═══════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════
    # VERIFICATION MODE SETTINGS
    # ═══════════════════════════════════════════════════════════
    async def set_verification_mode(self, mode: str):
        if mode not in ('instant', '12h', '24h'):
            mode = 'instant'
        await self.hash_settings.update_one(
            {'_id': 'verification_mode'},
            {'$set': {'value': mode}},
            upsert=True
        )

    async def get_verification_mode(self) -> str:
        data = await self.hash_settings.find_one({'_id': 'verification_mode'})
        if data:
            return data.get('value', 'instant')
        return 'instant'

    # ═══════════════════════════════════════════════════════════
    # PER-USER TIME-BASED ACCESS GRANTS (12h / 24h mode)
    # ═══════════════════════════════════════════════════════════
    async def grant_shortener_access(self, user_id: int, hours: int):
        granted_until = time.time() + (int(hours) * 3600)
        await self.shortener_access.update_one(
            {'_id': int(user_id)},
            {'$set': {'granted_until': float(granted_until)}},
            upsert=True
        )

    async def check_shortener_access(self, user_id: int) -> tuple:
        doc = await self.shortener_access.find_one({'_id': int(user_id)})
        if not doc:
            return (False, 0)
        until = float(doc.get('granted_until', 0))
        remaining = until - time.time()
        if remaining > 0:
            return (True, int(remaining))
        return (False, 0)

    # ═══════════════════════════════════════════════════════════
    # MASKED LINKS
    # ═══════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════
    # FINGERPRINT TOKENS
    # ═══════════════════════════════════════════════════════════
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
        await self.fingerprint_tokens.update_one({'_id': token}, {'$set': {'used': True}})
        return True

    # ═══════════════════════════════════════════════════════════
    # PER-USER SEQUENTIAL SHORTENER PROGRESS
    # ═══════════════════════════════════════════════════════════
    async def _get_progress_doc(self, user_id: int) -> dict:
        doc = await self.shortener_progress.find_one({'_id': user_id})
        return doc or {}

    async def _ensure_today(self, user_id: int) -> dict:
        today = _today_ist()
        doc = await self._get_progress_doc(user_id)
        if not doc or doc.get('date') != today:
            doc = {'_id': user_id, 'current_idx': 0, 'pending_idx': -1, 'date': today}
            await self.shortener_progress.update_one(
                {'_id': user_id},
                {'$set': {'current_idx': 0, 'pending_idx': -1, 'date': today}},
                upsert=True
            )
        return doc

    async def pick_sequential_shortener(self, user_id: int, total_providers: int) -> tuple:
        doc = await self._ensure_today(user_id)
        cooldowns = await self.get_shortener_cooldowns(user_id)

        pending = doc.get('pending_idx', -1)
        if pending is not None and pending >= 0 and pending < total_providers:
            if pending not in cooldowns:
                return (pending, True)
            await self.shortener_progress.update_one(
                {'_id': user_id}, {'$set': {'pending_idx': -1}}, upsert=True
            )

        current = doc.get('current_idx', 0)
        i = current
        while i < total_providers and i in cooldowns:
            i += 1

        if i >= total_providers:
            return (-1, False)

        await self.shortener_progress.update_one(
            {'_id': user_id},
            {'$set': {'current_idx': i, 'pending_idx': i}},
            upsert=True
        )
        return (i, True)

    async def consume_shortener_success(self, user_id: int) -> int:
        doc = await self._ensure_today(user_id)
        pending = doc.get('pending_idx', -1)
        if pending is None or pending < 0:
            return -1

        new_current = max(doc.get('current_idx', 0), pending + 1)
        await self.shortener_progress.update_one(
            {'_id': user_id},
            {'$set': {'current_idx': new_current, 'pending_idx': -1}},
            upsert=True
        )
        return pending

    async def seconds_until_daily_reset(self) -> int:
        now = datetime.now(_tz("Asia/Kolkata"))
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return max(0, int((tomorrow - now).total_seconds()))

    # ═══════════════════════════════════════════════════════════
    # PER-USER 24-HOUR PER-SHORTENER COOLDOWN
    # ═══════════════════════════════════════════════════════════
    async def mark_shortener_used(self, user_id: int, slot_idx: int, hours: int = 24):
        if slot_idx is None or slot_idx < 0:
            return
        until = time.time() + (int(hours) * 3600)
        await self.shortener_cooldowns.update_one(
            {'_id': int(user_id)},
            {'$set': {f'cooldowns.{int(slot_idx)}': float(until)}},
            upsert=True
        )

    async def get_shortener_cooldowns(self, user_id: int) -> dict:
        doc = await self.shortener_cooldowns.find_one({'_id': int(user_id)})
        if not doc:
            return {}
        raw = doc.get('cooldowns', {}) or {}
        now = time.time()
        active: dict = {}
        expired_keys = []
        for k, v in raw.items():
            try:
                until = float(v)
            except (TypeError, ValueError):
                expired_keys.append(k)
                continue
            if until > now:
                try:
                    active[int(k)] = until
                except (TypeError, ValueError):
                    pass
            else:
                expired_keys.append(k)
        if expired_keys:
            unset = {f'cooldowns.{k}': "" for k in expired_keys}
            try:
                await self.shortener_cooldowns.update_one(
                    {'_id': int(user_id)}, {'$unset': unset}
                )
            except Exception:
                pass
        return active

    async def next_shortener_unlock_seconds(self, user_id: int, total_providers: int) -> int:
        cooldowns = await self.get_shortener_cooldowns(user_id)
        if total_providers <= 0:
            return await self.seconds_until_daily_reset() or 1
        now = time.time()
        slot_unlocks = [cooldowns[i] for i in range(total_providers) if i in cooldowns]
        if not slot_unlocks:
            return max(1, await self.seconds_until_daily_reset())
        earliest_slot_unlock = min(slot_unlocks) - now
        daily_reset = await self.seconds_until_daily_reset()
        return max(1, int(max(earliest_slot_unlock, daily_reset)))

    # ═══════════════════════════════════════════════════════════
    # DAILY COUNTERS for /count  (auto-reset at 00:00 IST)
    # ═══════════════════════════════════════════════════════════
    async def _today_stats_doc(self):
        today = _today_ist()
        doc = await self.daily_stats.find_one({'_id': today})
        return doc or {'_id': today}

    async def increment_shortener_success(self, slot_idx: int):
        today = _today_ist()
        await self.daily_stats.update_one(
            {'_id': today},
            {'$inc': {f'shortener_success.{slot_idx}': 1, 'total_success': 1}},
            upsert=True
        )

    async def record_new_channel_join(self, user_id: int):
        """Called when a user successfully passes force-sub check for the first time today."""
        today = _today_ist()
        await self.daily_stats.update_one(
            {'_id': today},
            {'$addToSet': {'channel_joined_today': int(user_id)}},
            upsert=True
        )

    async def record_premium_access(self, user_id: int, link_payload: str) -> bool:
        today = _today_ist()
        try:
            await self.premium_access.insert_one({
                'user_id': int(user_id),
                'link': str(link_payload),
                'date': today,
                'ts': time.time(),
            })
            await self.daily_stats.update_one(
                {'_id': today},
                {
                    '$addToSet': {'premium_users': int(user_id)},
                    '$inc': {'premium_unique_link_count': 1},
                },
                upsert=True
            )
            return True
        except Exception:
            return False

    async def get_today_stats(self) -> dict:
        today = _today_ist()
        doc = await self.daily_stats.find_one({'_id': today})
        if not doc:
            return {
                '_id': today,
                'total_success': 0,
                'shortener_success': {},
                'premium_users': [],
                'premium_unique_link_count': 0,
                'bypass_attempts': 0,
                'channel_joined_today': [],
            }
        doc.setdefault('total_success', 0)
        doc.setdefault('shortener_success', {})
        doc.setdefault('premium_users', [])
        doc.setdefault('premium_unique_link_count', 0)
        doc.setdefault('bypass_attempts', 0)
        doc.setdefault('channel_joined_today', [])
        return doc

    async def reset_all_daily_stats(self):
        await self.sex_data.update_many({}, {'$set': {'verify_count': 0}})
        await self.daily_stats.delete_many({})
        await self.premium_access.delete_many({})
        await self.shortener_progress.delete_many({})
        await self.pending_shortener.delete_many({})

    # ═══════════════════════════════════════════════════════════
    # BYPASS PROTECTION
    # ═══════════════════════════════════════════════════════════
    @staticmethod
    def _pending_id(user_id: int, base64: str) -> str:
        return f"{int(user_id)}:{str(base64)}"

    async def create_pending_shortener(self, user_id: int, base64: str,
                                       chat_id: int, message_id: int) -> float:
        sent_at = time.time()
        await self.pending_shortener.update_one(
            {'_id': self._pending_id(user_id, base64)},
            {'$set': {
                'user_id': int(user_id),
                'base64': str(base64),
                'chat_id': int(chat_id),
                'message_id': int(message_id),
                'sent_at': sent_at,
                'expired': False,
            }},
            upsert=True
        )
        return sent_at

    async def get_pending_shortener(self, user_id: int, base64: str):
        return await self.pending_shortener.find_one(
            {'_id': self._pending_id(user_id, base64)}
        )

    async def find_active_pendings_for_user(self, user_id: int) -> list:
        cursor = self.pending_shortener.find(
            {'user_id': int(user_id), 'expired': {'$ne': True}}
        )
        return [d async for d in cursor]

    async def expire_pending(self, user_id: int, base64: str):
        await self.pending_shortener.update_one(
            {'_id': self._pending_id(user_id, base64)},
            {'$set': {'expired': True}}
        )

    async def delete_pending(self, user_id: int, base64: str):
        await self.pending_shortener.delete_one(
            {'_id': self._pending_id(user_id, base64)}
        )

    async def register_bypass_attempt(self, user_id: int) -> dict:
        now = time.time()
        existing = await self.bypass_bans.find_one({'_id': int(user_id)}) or {}
        new_strikes = int(existing.get('strikes', 0)) + 1

        if new_strikes <= 1:
            action = 'warn'
            banned_until = None
            permanent = False
        elif new_strikes == 2:
            action = 'ban_12h'
            banned_until = now + (12 * 3600)
            permanent = False
        elif new_strikes == 3:
            action = 'ban_24h'
            banned_until = now + (24 * 3600)
            permanent = False
        else:
            action = 'permanent'
            banned_until = None
            permanent = True

        today = _today_ist()
        await self.daily_stats.update_one(
            {'_id': today},
            {'$inc': {'bypass_attempts': 1}},
            upsert=True
        )

        await self.bypass_bans.update_one(
            {'_id': int(user_id)},
            {'$set': {
                'strikes': new_strikes,
                'banned_until': banned_until,
                'permanent': permanent,
                'last_bypass_at': now,
                'last_action': action,
            }},
            upsert=True
        )

        return {
            'strikes': new_strikes,
            'action': action,
            'banned_until': banned_until,
            'permanent': permanent,
        }

    async def get_bypass_ban(self, user_id: int):
        doc = await self.bypass_bans.find_one({'_id': int(user_id)})
        if not doc:
            return None
        if doc.get('permanent'):
            return doc
        until = doc.get('banned_until')
        if until and time.time() < float(until):
            return doc
        return None

    async def count_active_bypass_bans(self) -> dict:
        now = time.time()
        timed = await self.bypass_bans.count_documents({
            'permanent': {'$ne': True},
            'banned_until': {'$gt': now},
        })
        permanent = await self.bypass_bans.count_documents({'permanent': True})
        return {'timed': int(timed), 'permanent': int(permanent),
                'total': int(timed) + int(permanent)}

    # ═══════════════════════════════════════════════════════════
    # REFERRAL SYSTEM
    # ═══════════════════════════════════════════════════════════

    async def get_or_create_invite_code(self, user_id: int) -> str:
        """Return the user's unique invite code (creates one if it doesn't exist)."""
        doc = await self.referrals.find_one({'_id': int(user_id)})
        if doc and doc.get('invite_code'):
            return doc['invite_code']
        code = f"ref{int(user_id)}"
        await self.referrals.update_one(
            {'_id': int(user_id)},
            {'$set': {
                'invite_code': code,
                'all_time_invited': [],
                'monthly': {},
                'rewards_given': {},
            }},
            upsert=True
        )
        return code

    async def get_referrer_of(self, invitee_id: int):
        """Return the referrer's user_id for an invitee, or None."""
        doc = await self.referral_joins.find_one({'_id': int(invitee_id)})
        return doc.get('referrer_id') if doc else None

    async def record_referral_join(self, invitee_id: int, referrer_id: int) -> bool:
        """
        Record that invitee_id joined through referrer_id's invite link.
        Returns True if this is a new unique join (not seen before for this referrer),
        False if already recorded (prevents re-counting leave-and-rejoin).
        """
        # Check if this invitee was already counted for this referrer
        existing = await self.referral_joins.find_one({'_id': int(invitee_id)})
        if existing:
            return False  # already recorded — don't double-count

        now = time.time()
        month = _current_month_ist()

        # Record in referral_joins (so we never re-count this invitee)
        await self.referral_joins.insert_one({
            '_id': int(invitee_id),
            'referrer_id': int(referrer_id),
            'joined_at': now,
            'validated': False,
            'plan_bought': False,
        })

        # Update referrer's referral doc — both fields in a SINGLE $addToSet to avoid
        # Python dict key collision (duplicate '$addToSet' keys would silently drop one).
        await self.referrals.update_one(
            {'_id': int(referrer_id)},
            {
                '$addToSet': {
                    'all_time_invited': int(invitee_id),
                    f'monthly.{month}.invited': int(invitee_id),
                },
            },
            upsert=True
        )
        return True

    async def validate_referral(self, invitee_id: int) -> int:
        """
        Mark invitee as validated (completed short link / bought premium).
        Returns referrer_id if there is one and this is a new validation, else -1.
        """
        doc = await self.referral_joins.find_one({'_id': int(invitee_id)})
        if not doc:
            return -1
        if doc.get('validated'):
            return -1  # already validated before
        referrer_id = doc.get('referrer_id')
        if not referrer_id:
            return -1

        month = _current_month_ist()
        await self.referral_joins.update_one(
            {'_id': int(invitee_id)},
            {'$set': {'validated': True}}
        )
        await self.referrals.update_one(
            {'_id': int(referrer_id)},
            {'$addToSet': {f'monthly.{month}.validated': int(invitee_id)}},
            upsert=True
        )
        return int(referrer_id)

    async def mark_referral_plan_bought(self, invitee_id: int) -> int:
        """Mark that the invitee bought a plan (also counts as validated). Returns referrer_id."""
        doc = await self.referral_joins.find_one({'_id': int(invitee_id)})
        if not doc:
            return -1
        referrer_id = doc.get('referrer_id')
        if not referrer_id:
            return -1
        await self.referral_joins.update_one(
            {'_id': int(invitee_id)},
            {'$set': {'plan_bought': True}}
        )
        # If not yet validated, validate now
        if not doc.get('validated'):
            return await self.validate_referral(invitee_id)
        return int(referrer_id)

    async def get_referral_stats(self, user_id: int) -> dict:
        """
        Return referral stats for user:
        {
          invite_code, invite_link,
          month_invited, month_validated,
          total_all_time,
          rewards_given_this_month: [3, 10, 40],
        }
        """
        code = await self.get_or_create_invite_code(user_id)
        doc = await self.referrals.find_one({'_id': int(user_id)}) or {}
        month = _current_month_ist()
        monthly = doc.get('monthly', {}).get(month, {})
        month_invited = len(monthly.get('invited', []))
        month_validated = len(monthly.get('validated', []))
        total_all_time = len(doc.get('all_time_invited', []))
        rewards_this_month = doc.get('rewards_given', {}).get(month, [])
        return {
            'invite_code': code,
            'month_invited': month_invited,
            'month_validated': month_validated,
            'total_all_time': total_all_time,
            'rewards_given_this_month': rewards_this_month,
        }

    async def check_and_get_pending_reward(self, referrer_id: int) -> tuple:
        """
        Check if referrer qualifies for any new reward this month.
        Returns (days_reward: int, label: str) or (0, "") if no new reward.
        """
        from config import REFERRAL_MILESTONES
        doc = await self.referrals.find_one({'_id': int(referrer_id)}) or {}
        month = _current_month_ist()
        monthly = doc.get('monthly', {}).get(month, {})
        month_validated = len(monthly.get('validated', []))
        rewards_given = doc.get('rewards_given', {}).get(month, [])

        best_days = 0
        best_label = ""
        best_milestone = 0
        for (min_inv, days, label) in sorted(REFERRAL_MILESTONES, key=lambda x: x[0], reverse=True):
            if month_validated >= min_inv and min_inv not in rewards_given:
                best_days = days
                best_label = label
                best_milestone = min_inv
                break

        if best_days > 0:
            # Mark reward as given
            await self.referrals.update_one(
                {'_id': int(referrer_id)},
                {'$addToSet': {f'rewards_given.{month}': best_milestone}},
                upsert=True
            )
            return (best_days, best_label)
        return (0, "")

    async def reset_monthly_referral_stats(self):
        """
        Called on the 1st of each month. Resets monthly invite/validated counts
        but keeps all_time_invited intact (to prevent double-counting).
        Also resets monthly rewards_given so the new month's milestones are fresh.
        Does NOT delete referral_joins records — those are permanent de-dup records.
        """
        await self.referrals.update_many({}, {'$set': {'monthly': {}, 'rewards_given': {}}})

    # ═══════════════════════════════════════════════════════════
    # PAYMENT REQUESTS
    # ═══════════════════════════════════════════════════════════

    async def create_payment_request(self, user_id: int, plan_key: str,
                                     plan_type: str, days: int, amount: int) -> dict:
        """Create or replace a pending payment request for a user."""
        now = time.time()
        doc = {
            '_id': int(user_id),
            'plan_key': plan_key,
            'plan_type': plan_type,
            'days': days,
            'amount': amount,
            'status': 'pending',
            'requested_at': now,
            'admin_msg_ids': [],
        }
        await self.payment_requests.update_one(
            {'_id': int(user_id)},
            {'$set': doc},
            upsert=True
        )
        return doc

    async def get_payment_request(self, user_id: int):
        return await self.payment_requests.find_one({'_id': int(user_id)})

    async def update_payment_request_status(self, user_id: int, status: str,
                                            approved_by: int = None):
        update = {'$set': {'status': status, 'resolved_at': time.time()}}
        if approved_by:
            update['$set']['approved_by'] = approved_by
        await self.payment_requests.update_one({'_id': int(user_id)}, update)

    async def add_admin_msg_to_payment(self, user_id: int, admin_id: int, msg_id: int):
        await self.payment_requests.update_one(
            {'_id': int(user_id)},
            {'$push': {'admin_msg_ids': [int(admin_id), int(msg_id)]}}
        )

    async def delete_payment_request(self, user_id: int):
        await self.payment_requests.delete_one({'_id': int(user_id)})

    # ═══════════════════════════════════════════════════════════
    # INVITE LINK MODE & CHANNEL SETTINGS
    # ═══════════════════════════════════════════════════════════

    async def set_invite_channel(self, channel_id: int):
        """Set which channel the bot generates per-user invite links for."""
        await self.invite_channel_settings.update_one(
            {'_id': 'settings'},
            {'$set': {'channel_id': int(channel_id)}},
            upsert=True
        )

    async def get_invite_channel(self):
        """Return the configured invite channel ID, or None."""
        doc = await self.invite_channel_settings.find_one({'_id': 'settings'})
        return doc.get('channel_id') if doc else None

    async def set_invite_link_mode(self, mode: str):
        """
        Set invite link generation mode:
          'bot'     — classic bot deep-link  (t.me/bot?start=ref<uid>)
          'channel' — unique per-user channel invite link
        """
        if mode not in ('bot', 'channel'):
            mode = 'bot'
        await self.invite_channel_settings.update_one(
            {'_id': 'settings'},
            {'$set': {'mode': mode}},
            upsert=True
        )

    async def get_invite_link_mode(self) -> str:
        """Return 'bot' (default) or 'channel'."""
        doc = await self.invite_channel_settings.find_one({'_id': 'settings'})
        return (doc.get('mode') or 'bot') if doc else 'bot'

    async def get_or_create_channel_invite(self, user_id: int, channel_id: int, client) -> str:
        """
        Return the saved channel invite link for this user, or create a new one.
        The invite link is permanent, has no member limit, and is named 'ref_<user_id>'
        so admins can visually identify it in the channel invite-links panel.
        REQUIRES: bot must be an admin in that channel with 'Invite Users' permission.
        """
        doc = await self.user_channel_invites.find_one({'_id': int(user_id)})
        if doc and doc.get('invite_link') and doc.get('channel_id') == int(channel_id):
            return doc['invite_link']

        # Create a fresh permanent invite link named after this user
        invite = await client.create_chat_invite_link(
            chat_id=int(channel_id),
            name=f"ref_{user_id}",
        )
        link = invite.invite_link

        await self.user_channel_invites.update_one(
            {'_id': int(user_id)},
            {'$set': {
                'channel_id': int(channel_id),
                'invite_link': link,
                'created_at': time.time(),
                'joined_users': [],
            }},
            upsert=True
        )
        return link

    async def get_invite_link_owner(self, invite_link: str):
        """Look up which user's referral this channel invite link belongs to."""
        doc = await self.user_channel_invites.find_one({'invite_link': invite_link})
        return doc.get('_id') if doc else None

    async def get_invite_link_stats(self, user_id: int) -> dict:
        """Return stats for a user's channel invite link."""
        doc = await self.user_channel_invites.find_one({'_id': int(user_id)})
        if not doc:
            return {'invite_link': None, 'joined_count': 0}
        return {
            'invite_link': doc.get('invite_link'),
            'joined_count': len(doc.get('joined_users', [])),
        }

    # ═══════════════════════════════════════════════════════════════════════
    # Paytm Auto-Payment Order Management
    # ═══════════════════════════════════════════════════════════════════════

    async def create_order(self, order_id: str, user_id: int, amount: float,
                           days: int, plan_key: str, plan_type: str):
        """Create a new pending Paytm order."""
        doc = {
            '_id': order_id,
            'user_id': int(user_id),
            'amount': float(amount),
            'days': int(days),
            'plan_key': plan_key,
            'plan_type': plan_type,   # 'normal' or 'super'
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'txn_id': None,
        }
        try:
            await self.orders.insert_one(doc)
        except Exception:
            pass   # duplicate key on retry — safe to ignore

    async def get_order(self, order_id: str):
        """Fetch a Paytm order by its order_id."""
        return await self.orders.find_one({'_id': order_id})

    async def get_pending_order_for_user(self, user_id: int):
        """Return the most recent pending order for a user, or None."""
        return await self.orders.find_one(
            {'user_id': int(user_id), 'status': 'pending'},
            sort=[('created_at', -1)]
        )

    async def update_order_status(self, order_id: str, status: str, txn_id: str = None):
        """Update order status; optionally record the Paytm transaction ID."""
        update = {'status': status}
        if txn_id:
            update['txn_id'] = txn_id
        # Stamp completion time so /id date filter works correctly
        if status == 'success':
            update['completed_at'] = datetime.utcnow()
        await self.orders.update_one({'_id': order_id}, {'$set': update})

    async def get_orders_by_date(self, start_utc: datetime, end_utc: datetime) -> list:
        """
        Return all successfully paid orders whose completed_at falls in the
        given UTC range.  Used by the /id <date> admin command.
        Falls back to created_at if an old order has no completed_at field.
        """
        cursor = self.orders.find(
            {
                'status': 'success',
                '$or': [
                    {'completed_at': {'$gte': start_utc, '$lt': end_utc}},
                    # fallback for orders created before completed_at was added
                    {'completed_at': {'$exists': False},
                     'created_at':   {'$gte': start_utc, '$lt': end_utc}},
                ],
            },
            sort=[('completed_at', 1), ('created_at', 1)],
        )
        return await cursor.to_list(length=None)

    async def is_txn_id_used(self, txn_id: str) -> bool:
        """Replay-attack protection: check if this Paytm TXN_ID was already honoured."""
        if not txn_id:
            return False
        return bool(await self.orders.find_one({'txn_id': txn_id, 'status': 'success'}))

    # ═══════════════════════════════════════════════════════════
    # BOT ACCESS MODE (Free / Token / Premium)
    # ═══════════════════════════════════════════════════════════

    async def get_bot_mode(self) -> str:
        """Get the current bot access mode: 'free', 'token', or 'premium'."""
        doc = await self.bot_mode_settings.find_one({'_id': 'bot_mode'})
        return doc.get('mode', 'token') if doc else 'token'

    async def set_bot_mode(self, mode: str):
        """Set the bot access mode ('free', 'token', or 'premium')."""
        await self.bot_mode_settings.update_one(
            {'_id': 'bot_mode'},
            {'$set': {'mode': mode}},
            upsert=True
        )

    async def get_premium_mode_free_limit(self) -> int:
        """Get the free file access limit per user in Premium Mode (default 3)."""
        doc = await self.bot_mode_settings.find_one({'_id': 'premium_free_limit'})
        return int(doc.get('limit', 3)) if doc else 3

    async def set_premium_mode_free_limit(self, limit: int):
        """Set the free file access limit per user in Premium Mode."""
        await self.bot_mode_settings.update_one(
            {'_id': 'premium_free_limit'},
            {'$set': {'limit': int(limit)}},
            upsert=True
        )

    async def get_user_free_access_count(self, user_id: int) -> int:
        """Get how many free files a user has accessed in Premium Mode."""
        doc = await self.user_free_access.find_one({'_id': int(user_id)})
        return int(doc.get('count', 0)) if doc else 0

    async def increment_user_free_access(self, user_id: int):
        """Increment the free access counter for a user in Premium Mode."""
        await self.user_free_access.update_one(
            {'_id': int(user_id)},
            {'$inc': {'count': 1}},
            upsert=True
        )


db = Rohit(DB_URI, DB_NAME)
