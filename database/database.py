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
    """Return today's date string in IST (matches the bot's daily reset cron)."""
    return datetime.now(_tz("Asia/Kolkata")).strftime("%Y-%m-%d")


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
        # Per-user sequential shortener progress (sticks to 1 slot until success).
        self.shortener_progress = self.database['shortener_progress']
        # Daily counters for /count (per-shortener success, premium accesses, etc.)
        self.daily_stats = self.database['daily_stats']
        # Per-premium-user unique link access record (one doc per user+link+date).
        self.premium_access = self.database['premium_access']
        # Bypass protection: pending short-link records + escalating ban store.
        self.pending_shortener = self.database['pending_shortener']
        # Per-user, per-shortener 24h usage cooldowns. Persists across the
        # daily 00:00 IST reset (only the daily counters reset, NOT cooldowns).
        # Doc shape:
        #   { _id: user_id,
        #     cooldowns: { "<slot_idx>": unix_ts_until, ... } }
        self.shortener_cooldowns = self.database['shortener_cooldowns']
        self.bypass_bans = self.database['bypass_bans']

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
    # PER-USER SEQUENTIAL SHORTENER PROGRESS
    #
    # The bot serves one shortener at a time and STICKS to it until the
    # user successfully completes it (returns via the yu3elk callback).
    # Only then does it advance to the next slot, in strict order:
    #     Shortener 1 → Shortener 2 → ... → Shortener N
    # When all N are completed, the user is rate-limited until the
    # daily reset (00:00 IST), at which point the progress wipes and
    # they start over from Shortener 1.
    #
    # DB document shape (one per user):
    # {
    #   _id: user_id,
    #   current_idx: 0,          # next slot to serve (0..N)
    #   pending_idx: -1,         # slot user is mid-completion on (-1 if none)
    #   date: 'YYYY-MM-DD'       # IST date — auto-resets when this changes
    # }
    # ================================================================

    async def _get_progress_doc(self, user_id: int) -> dict:
        doc = await self.shortener_progress.find_one({'_id': user_id})
        return doc or {}

    async def _ensure_today(self, user_id: int) -> dict:
        """Return the user's progress doc, resetting it if the date rolled over."""
        today = _today_ist()
        doc = await self._get_progress_doc(user_id)
        if not doc or doc.get('date') != today:
            doc = {
                '_id': user_id,
                'current_idx': 0,
                'pending_idx': -1,
                'date': today,
            }
            await self.shortener_progress.update_one(
                {'_id': user_id},
                {'$set': {
                    'current_idx': 0,
                    'pending_idx': -1,
                    'date': today,
                }},
                upsert=True
            )
        return doc

    async def pick_sequential_shortener(self, user_id: int, total_providers: int) -> tuple:
        """
        Pick the shortener slot to serve next for this user.

        Sequential rotation (Shortener 1 → 2 → ... → N) is preserved, but
        any slot the user has used in the last 24 hours is SKIPPED — even
        across the daily reset. The 24h per-slot cooldown is applied at the
        moment of a successful completion (see `mark_shortener_used`).

        Returns (idx, is_available):
            (idx, True)  → serve providers[idx]; the user must complete it
                            before being moved off this slot.
            (-1, False)  → every still-rotatable slot is on cooldown for
                            this user; caller should look up the wait time
                            via `next_shortener_unlock_seconds`.

        Stickiness rule:
            If a `pending_idx` is already set (user was sent a link earlier
            and hasn't completed it yet), the SAME slot is returned every
            time so the user keeps seeing the same shortener until it
            works — unless that slot has somehow entered cooldown (defensive
            edge case), in which case the sticky lock is cleared.
        """
        doc = await self._ensure_today(user_id)
        cooldowns = await self.get_shortener_cooldowns(user_id)  # {int: until_ts}

        # Sticky: user is mid-flow on a slot — keep handing them the same one.
        pending = doc.get('pending_idx', -1)
        if pending is not None and pending >= 0 and pending < total_providers:
            if pending not in cooldowns:
                return (pending, True)
            # Defensive: pending slot is now on cooldown — clear and re-pick.
            await self.shortener_progress.update_one(
                {'_id': user_id},
                {'$set': {'pending_idx': -1}},
                upsert=True
            )

        # Walk forward from current_idx, skipping any slot still on cooldown.
        current = doc.get('current_idx', 0)
        i = current
        while i < total_providers and i in cooldowns:
            i += 1

        if i >= total_providers:
            # No rotatable slot available right now — caller will show the
            # cooldown / "buy premium" message with a wait time.
            return (-1, False)

        # Persist the advanced pointer + lock the user onto this slot.
        await self.shortener_progress.update_one(
            {'_id': user_id},
            {'$set': {'current_idx': i, 'pending_idx': i}},
            upsert=True
        )
        return (i, True)

    async def consume_shortener_success(self, user_id: int) -> int:
        """
        Mark the user's CURRENT pending shortener as completed and advance
        them to the next one. Returns the slot index that was completed,
        or -1 if there was nothing pending (e.g. repeat click on a link
        the user has already redeemed today — must NOT be double-counted).
        """
        doc = await self._ensure_today(user_id)
        pending = doc.get('pending_idx', -1)
        if pending is None or pending < 0:
            return -1

        new_current = max(doc.get('current_idx', 0), pending + 1)
        await self.shortener_progress.update_one(
            {'_id': user_id},
            {'$set': {
                'current_idx': new_current,
                'pending_idx': -1,
            }},
            upsert=True
        )
        return pending

    async def seconds_until_daily_reset(self) -> int:
        """Seconds remaining until the next 00:00 IST daily reset."""
        now = datetime.now(_tz("Asia/Kolkata"))
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return max(0, int((tomorrow - now).total_seconds()))

    # ================================================================
    # PER-USER 24-HOUR PER-SHORTENER COOLDOWN
    #
    # When a user successfully completes shortener slot `i`, that slot
    # becomes locked for that user for the next 24 hours. The lock is
    # NOT cleared by the daily 00:00 IST reset — only the daily counters
    # reset. The picker (`pick_sequential_shortener`) skips any slot
    # whose cooldown has not yet expired.
    # ================================================================

    async def mark_shortener_used(self, user_id: int, slot_idx: int,
                                  hours: int = 24):
        """Lock `slot_idx` for `user_id` for the next `hours` hours."""
        if slot_idx is None or slot_idx < 0:
            return
        until = time.time() + (int(hours) * 3600)
        await self.shortener_cooldowns.update_one(
            {'_id': int(user_id)},
            {'$set': {f'cooldowns.{int(slot_idx)}': float(until)}},
            upsert=True
        )

    async def get_shortener_cooldowns(self, user_id: int) -> dict:
        """
        Return {slot_idx_int: until_ts} for slots whose cooldown is still
        in the future. Expired entries are filtered out (and lazily
        cleaned up so the doc doesn't grow forever).
        """
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
                    {'_id': int(user_id)},
                    {'$unset': unset}
                )
            except Exception:
                pass
        return active

    async def next_shortener_unlock_seconds(self, user_id: int,
                                            total_providers: int) -> int:
        """
        Compute how many seconds until this user's next shortener slot
        becomes usable. Considers BOTH per-slot 24h cooldowns AND the
        00:00 IST daily reset (which wipes `current_idx`, allowing slots
        that are no longer on cooldown to be served again).

        Always returns at least 1.
        """
        cooldowns = await self.get_shortener_cooldowns(user_id)
        if total_providers <= 0:
            return await self.seconds_until_daily_reset() or 1

        now = time.time()
        # Earliest moment some slot in 0..N-1 leaves cooldown.
        slot_unlocks = [
            cooldowns[i] for i in range(total_providers) if i in cooldowns
        ]
        if not slot_unlocks:
            # No active cooldowns at all — exhaustion must be due to
            # current_idx already past N. Daily reset is what unblocks.
            return max(1, await self.seconds_until_daily_reset())

        earliest_slot_unlock = min(slot_unlocks) - now
        # The user also needs `current_idx` reset (which only happens at
        # the daily IST midnight) before a freshly-uncooled slot can be
        # served, so the true wait is the LATER of the two.
        daily_reset = await self.seconds_until_daily_reset()
        return max(1, int(max(earliest_slot_unlock, daily_reset)))

    # ================================================================
    # DAILY COUNTERS for /count  (auto-reset at 00:00 IST)
    # ================================================================

    async def _today_stats_doc(self):
        today = _today_ist()
        doc = await self.daily_stats.find_one({'_id': today})
        return doc or {'_id': today}

    async def increment_shortener_success(self, slot_idx: int):
        """Increment the per-slot success counter for today."""
        today = _today_ist()
        await self.daily_stats.update_one(
            {'_id': today},
            {'$inc': {f'shortener_success.{slot_idx}': 1, 'total_success': 1}},
            upsert=True
        )

    async def record_premium_access(self, user_id: int, link_payload: str) -> bool:
        """
        Record that a premium user accessed a link today.
        Returns True if this is a NEW link for this user today (counted),
        False if they've already accessed this exact link today (not counted).
        """
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
        """Return the raw daily stats doc for today (zero-filled if missing)."""
        today = _today_ist()
        doc = await self.daily_stats.find_one({'_id': today})
        if not doc:
            return {
                '_id': today,
                'total_success': 0,
                'shortener_success': {},
                'premium_users': [],
                'premium_unique_link_count': 0,
            }
        doc.setdefault('total_success', 0)
        doc.setdefault('shortener_success', {})
        doc.setdefault('premium_users', [])
        doc.setdefault('premium_unique_link_count', 0)
        return doc

    async def reset_all_daily_stats(self):
        """Wipe every daily counter and per-user progress so the day starts fresh."""
        await self.sex_data.update_many({}, {'$set': {'verify_count': 0}})
        await self.daily_stats.delete_many({})
        await self.premium_access.delete_many({})
        await self.shortener_progress.delete_many({})
        # Pending short-link records also reset — yesterday's unfinished links
        # don't carry over since the user starts at slot #1 again today.
        # NOTE: bypass_bans and shortener_cooldowns are deliberately NOT
        # wiped: bans must persist across days, and the per-user 24h
        # per-shortener cooldowns are also explicitly long-lived (only
        # the /count daily counters reset at 00:00 IST).
        await self.pending_shortener.delete_many({})

    # ================================================================
    # BYPASS PROTECTION
    #
    # When a short link is sent we record:
    #   {_id: "{user_id}:{base64}",
    #    user_id, base64, chat_id, message_id,
    #    sent_at: unix_ts,           # when the link was sent
    #    expired: bool,              # true after a bypass detection
    #   }
    # The yu3elk callback then either:
    #   - completes legitimately (delta >= BYPASS_PROTECTION_SECONDS) → delete
    #   - is too fast → mark expired, register a strike, escalate the ban
    #
    # Escalation table (per user, cumulative across days):
    #   strike 1 → warn only
    #   strike 2 → ban 12 hours
    #   strike 3 → ban 24 hours
    #   strike 4 → permanent ban
    # ================================================================

    @staticmethod
    def _pending_id(user_id: int, base64: str) -> str:
        return f"{int(user_id)}:{str(base64)}"

    async def create_pending_shortener(self, user_id: int, base64: str,
                                       chat_id: int, message_id: int) -> float:
        """Record that a short link was just served. Returns the sent_at ts."""
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
        """All non-expired pending short-link records for a user (for cleanup)."""
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
        """
        Record a bypass attempt and apply the next escalation step.
        Returns a dict:
            {
              'strikes': int,
              'action': 'warn'|'ban_12h'|'ban_24h'|'permanent',
              'banned_until': float|None,
              'permanent': bool,
            }
        """
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

        # Track today's bypass-attempt counter for /count
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
        """
        Return ban info dict if the user is currently banned via bypass
        protection (timed or permanent), else None.
        """
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
        """Counts of currently-active bypass bans (timed + permanent)."""
        now = time.time()
        timed = await self.bypass_bans.count_documents({
            'permanent': {'$ne': True},
            'banned_until': {'$gt': now},
        })
        permanent = await self.bypass_bans.count_documents({'permanent': True})
        return {'timed': int(timed), 'permanent': int(permanent),
                'total': int(timed) + int(permanent)}


db = Rohit(DB_URI, DB_NAME)
