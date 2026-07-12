"""
/leaderboard - top players ranked by matches won, then runs, then wickets.
"""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes


async def render_leaderboard_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    db = context.application.bot_data["db"]
    rows = await db.get_leaderboard(limit=10)

    if not rows:
        return "🏆 *Leaderboard*\n━━━━━━━━━━━━━━━━━━\n\nNo matches played yet. Be the first champion! ✨"

    lines = ["🏆✨ *CRICKET ROYALE LEADERBOARD* ✨🏆", "━━━━━━━━━━━━━━━━━━", ""]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        name = f"@{row['username']}" if row["username"] else row["first_name"]
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(
            f"{prefix} {name} — {row['matches_won']}W / {row['matches_played']}P  "
            f"| {row['runs_scored']} runs | {row['wickets_taken']} wkts"
        )
    return "\n".join(lines)


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = await render_leaderboard_text(context)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def userstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows a full career stats card. Reply to someone's message with
    /userstats to check their stats instead of your own."""
    target_user = update.effective_user
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_user = update.message.reply_to_message.from_user

    db = context.application.bot_data["db"]
    row = await db.get_user_stats(target_user.id)

    if row is None or row["matches_played"] == 0:
        who = "You haven't" if target_user.id == update.effective_user.id else f"{target_user.first_name} hasn't"
        await update.message.reply_text(f"{who} played any matches yet. Jump into a Solo or Team Match first!")
        return

    from utils.userstats import format_user_stats
    display_name = f"@{target_user.username}" if target_user.username else target_user.first_name
    text = format_user_stats(row, display_name)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
