"""
Owner-only tools. Every command here checks config.OWNER_ID and silently
ignores anyone else -- these commands don't even show up as "denied" to
regular users, they just do nothing.
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

import config
from handlers.start import get_store

logger = logging.getLogger(__name__)


def is_owner(user_id: int) -> bool:
    return config.OWNER_ID != 0 and user_id == config.OWNER_ID


def _is_from_owner(update: Update) -> bool:
    user = update.effective_user
    return user is not None and is_owner(user.id)


async def ownerhelp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_from_owner(update):
        return
    text = (
        "👑 *Owner Commands*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🗣 /broadcast `<message>` — send an announcement to every chat "
        "the bot has ever seen\n\n"
        "📊 /botstats — global bot usage stats\n\n"
        "🔧 /maintenance `on|off` — block new matches for everyone but you\n\n"
        "🛑 /forceend `<chat_id>` — force-end the match/lobby in any chat\n\n"
        "👑 /ownerhelp — this menu"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_from_owner(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    db = context.application.bot_data["db"]
    chat_ids = await db.get_all_chat_ids()

    status = await update.message.reply_text(f"📡 Broadcasting to {len(chat_ids)} chats...")
    sent, failed = 0, 0
    for chat_id in chat_ids:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📢 *Announcement from Cricket Royale*\n━━━━━━━━━━━━━━━━━━\n\n{message}",
                parse_mode=ParseMode.MARKDOWN,
            )
            sent += 1
        except TelegramError as exc:
            logger.debug("Broadcast failed for chat %s: %s", chat_id, exc)
            failed += 1
        await asyncio.sleep(0.05)  # gentle rate limiting so Telegram doesn't throttle us

    await status.edit_text(f"✅ Broadcast complete: {sent} sent, {failed} failed.")


async def botstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_from_owner(update):
        return
    db = context.application.bot_data["db"]
    stats = await db.get_bot_stats()
    store = get_store(context)
    active = len(store.all())
    maintenance = context.application.bot_data.get("maintenance", False)

    text = (
        "👑 *Bot-wide Stats*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Registered users: *{stats['total_users']}*\n"
        f"💬 Known chats: *{stats['total_chats']}*\n"
        f"🏏 Matches logged: *{stats['total_matches']}*\n"
        f"🔴 Active matches right now: *{active}*\n"
        f"🏃 Total career runs scored: *{stats['total_runs']}*\n"
        f"🎯 Total career wickets taken: *{stats['total_wickets']}*\n"
        f"🔧 Maintenance mode: *{'ON' if maintenance else 'OFF'}*"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_from_owner(update):
        return
    if not context.args or context.args[0].lower() not in ("on", "off"):
        current = context.application.bot_data.get("maintenance", False)
        await update.message.reply_text(
            f"Maintenance mode is currently *{'ON' if current else 'OFF'}*.\nUsage: /maintenance on|off",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    on = context.args[0].lower() == "on"
    context.application.bot_data["maintenance"] = on
    await update.message.reply_text(
        f"🔧 Maintenance mode is now *{'ON' if on else 'OFF'}*.", parse_mode=ParseMode.MARKDOWN
    )


async def forceend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_from_owner(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /forceend <chat_id>")
        return
    try:
        target_chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("chat_id must be a number.")
        return

    store = get_store(context)
    match = store.get(target_chat_id)
    if match is None:
        await update.message.reply_text("No active match/lobby in that chat.")
        return

    if match.lobby_job_name:
        for job in context.application.job_queue.get_jobs_by_name(match.lobby_job_name):
            job.schedule_removal()

    store.remove(target_chat_id)
    try:
        await context.bot.send_message(chat_id=target_chat_id, text="🛑 This match was ended by the bot owner.")
    except TelegramError:
        pass
    await update.message.reply_text(f"✅ Force-ended the match in chat {target_chat_id}.")


def is_maintenance_mode(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.application.bot_data.get("maintenance", False))
