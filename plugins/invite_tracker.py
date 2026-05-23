# Invite Link Tracker — tracks who joined a channel via whose referral invite link
# Activated only when invite mode is set to "channel" via /hash panel

import asyncio
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
from bot import Bot
from database.database import db


@Bot.on_chat_member_updated()
async def track_channel_invite_join(client: Client, update: ChatMemberUpdated):
    """
    Fires on every chat member status change across all chats the bot is in.
    We filter down to only the configured invite channel and only actual new joins.
    """
    try:
        # Only process if invite mode is set to "channel"
        mode = await db.get_invite_link_mode()
        if mode != "channel":
            return

        invite_channel_id = await db.get_invite_channel()
        if not invite_channel_id:
            return

        # Only care about the configured invite channel
        if not update.chat or update.chat.id != int(invite_channel_id):
            return

        new_member = update.new_chat_member
        old_member = update.old_chat_member

        if not new_member:
            return

        # Only count actual joins (MEMBER status)
        if new_member.status != ChatMemberStatus.MEMBER:
            return

        # Only count users who weren't already members (joined fresh)
        old_status = old_member.status if old_member else None
        if old_status not in (
            ChatMemberStatus.LEFT,
            ChatMemberStatus.BANNED,
            ChatMemberStatus.RESTRICTED,
            None,
        ):
            return

        # Check if they joined via a tracked invite link
        invite_link_obj = getattr(update, 'invite_link', None)
        if not invite_link_obj:
            return

        link_str = getattr(invite_link_obj, 'invite_link', None)
        if not link_str:
            return

        invitee_id = new_member.user.id

        # Look up who owns this invite link
        referrer_id = await db.get_invite_link_owner(link_str)
        if not referrer_id:
            return

        # Don't let someone count as their own referral
        if invitee_id == referrer_id:
            return

        # Record the referral join (de-duped — returns False if already recorded)
        is_new = await db.record_referral_join(
            invitee_id=invitee_id,
            referrer_id=referrer_id,
        )

        # Mark this user joined in the invite link's record
        await db.user_channel_invites.update_one(
            {'_id': int(referrer_id)},
            {'$addToSet': {'joined_users': int(invitee_id)}}
        )

        if not is_new:
            return  # Already counted before, skip notifications

        # Notify the referrer
        try:
            await client.send_message(
                chat_id=referrer_id,
                text=(
                    f"<blockquote>🎉 <b>ɴᴇᴡ ᴄʜᴀɴɴᴇʟ ɪɴᴠɪᴛᴇ ᴊᴏɪɴ!</b></blockquote>\n\n"
                    f"<blockquote>sᴏᴍᴇᴏɴᴇ ᴊᴜsᴛ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴛʜʀᴏᴜɢʜ ʏᴏᴜʀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ! 👥</blockquote>\n\n"
                    f"<blockquote expandable>⚠️ ɪɴᴠɪᴛᴇ ᴡɪʟʟ ʙᴇ <b>ᴠᴀʟɪᴅᴀᴛᴇᴅ</b> ᴡʜᴇɴ ᴛʜᴇʏ ᴄᴏᴍᴘʟᴇᴛᴇ ᴀ sʜᴏʀᴛ-ʟɪɴᴋ ᴏʀ ʙᴜʏ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ᴛʜɪs ᴍᴏɴᴛʜ.</blockquote>"
                ),
            )
        except Exception:
            pass

    except Exception as e:
        print(f"[invite_tracker] error: {e}")
