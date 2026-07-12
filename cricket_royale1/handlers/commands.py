"""
/endmatch - force-end the active match/lobby early.
/checkassets - debug command to see which media files are found vs missing.
Also holds the global error handler.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from handlers.start import get_store
from utils.models import MatchMode, MatchStatus

logger = logging.getLogger(__name__)


async def checkassets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists every media asset the bot looks for and whether it currently
    finds a matching file on disk -- handy for tracking down a GIF that
    isn't showing up."""
    assets = [
        ("banner", config.banner_image()),
        ("team_match_banner", config.team_match_banner()),
        ("solo_match_banner", config.solo_match_banner()),
        ("player_of_match_banner", config.player_of_match_banner()),
        ("welcome", config.welcome_gif()),
        ("toss", config.toss_gif()),
        ("wicket", config.wicket_gif()),
        ("bowling", config.bowling_gif()),
        ("ball_delivered", config.ball_delivered_gif()),
        ("fifty", config.fifty_gif()),
        ("century", config.century_gif()),
    ]
    for n in range(7):
        assets.append((str(n), config.run_gif(n)))

    lines = ["🔍 *Asset Check*", ""]
    for name, path in assets:
        mark = "✅" if path.exists() else "❌"
        lines.append(f"{mark} `{name}` → `{path.name}`")

    missing = [name for name, path in assets if not path.exists()]
    lines.append("")
    if missing:
        lines.append(f"⚠️ Missing: {', '.join(missing)}")
        lines.append(f"Expected folder: `{config.GIFS_DIR}` (banners go in `{config.ASSETS_DIR}` directly).")
    else:
        lines.append("🎉 All assets found!")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def _can_end_match(match, user_id: int) -> bool:
    if user_id == match.creator_id:
        return True
    if user_id == match.initiator_id:
        return True
    if match.mode is MatchMode.SOLO:
        return user_id in match.royale_players
    captains = {match.team_a.captain_id, match.team_b.captain_id}
    return user_id in captains


async def endmatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None:
        await update.message.reply_text("There's no active match or lobby in this chat.")
        return

    if not _can_end_match(match, user.id):
        await update.message.reply_text(
            "Only the match creator, a captain, or the solo player can end this match."
        )
        return

    if match.lobby_job_name:
        for job in context.application.job_queue.get_jobs_by_name(match.lobby_job_name):
            job.schedule_removal()

    was_in_progress = match.status == MatchStatus.IN_PROGRESS
    match.status = MatchStatus.CANCELLED
    store.remove(chat.id)

    if was_in_progress:
        if match.mode is MatchMode.SOLO and match.striker_id:
            batter = match.royale_players.get(match.striker_id)
            batter_line = f"{batter.display_name}: {batter.runs} ({batter.balls_faced}b)" if batter else ""
            await update.message.reply_text(
                f"🛑 Match ended early by {user.first_name}.\n\n"
                f"Current batter: {batter_line}"
            )
        else:
            await update.message.reply_text(
                f"🛑 Match ended early by {user.first_name}.\n\n"
                f"Final score: {match.batting_team.name} {match.score}/{match.wickets} "
                f"({match.current_over}.{match.current_ball}/{match.overs} ov)"
            )
    else:
        await update.message.reply_text(f"🛑 Match/lobby ended by {user.first_name}.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
