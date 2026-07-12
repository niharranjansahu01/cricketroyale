"""
/teams  - show the current lobby/match rosters and captains.
/add a  - join Team A during the lobby phase (command alternative to the button).
/add b  - join Team B during the lobby phase.
/remove - leave your team during the lobby phase.
"""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import config
from handlers.start import get_store
from utils.models import MatchMode, MatchStatus, Player, TeamKey


async def teams_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    store = get_store(context)
    match = store.get(chat.id)

    if match is None:
        await update.message.reply_text("There's no active match or lobby in this chat.")
        return

    if match.mode is MatchMode.SOLO:
        lines = [f"🏏 *Solo Match Status:* {match.status.name}", ""]
        if match.royale_order:
            lines.append(f"👥 *Joined ({len(match.royale_order)}):*")
            for i, uid in enumerate(match.royale_order, start=1):
                p = match.royale_players[uid]
                tag = ""
                if match.status.name == "IN_PROGRESS" and uid == match.striker_id:
                    tag = " 🏏 (batting now)"
                lines.append(f"{i}. {p.display_name}{tag}")
        else:
            lines.append("No one has joined yet.")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
        return

    lines = [
        f"👥 *Match Status:* {match.status.name}",
        "",
        f"🅰️ *{match.team_a.name}* ({match.team_a.size})",
        *match.team_a.roster_lines(),
        "",
        f"🅱️ *{match.team_b.name}* ({match.team_b.size})",
        *match.team_b.roster_lines(),
    ]
    if match.overs:
        lines.append("")
        lines.append(f"Overs: {match.overs}")
    if match.status.name == "IN_PROGRESS":
        lines.append(f"Score: {match.score}/{match.wickets} ({match.current_over}.{match.current_ball} ov)")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.status != MatchStatus.LOBBY:
        await update.message.reply_text("There's no open lobby to join right now.")
        return

    if match.mode is MatchMode.SOLO:
        await update.message.reply_text("Use /join for Solo Match, not /add.")
        return

    if not context.args or context.args[0].lower() not in ("a", "b"):
        await update.message.reply_text("Usage: /add a  or  /add b")
        return

    team_key = TeamKey.A if context.args[0].lower() == "a" else TeamKey.B
    target_team = match.team(team_key)
    other_team = match.team(team_key.other)

    if user.id in other_team.players:
        await update.message.reply_text("You're already in the other team!")
        return
    if user.id in target_team.players:
        await update.message.reply_text(f"You're already in {target_team.name}!")
        return
    if target_team.size >= config.MAX_PLAYERS_PER_TEAM:
        await update.message.reply_text(f"{target_team.name} is full.")
        return

    target_team.add_player(Player(user_id=user.id, username=user.username, first_name=user.first_name))
    await update.message.reply_text(f"✅ Added to {target_team.name}!")

    from handlers.lobby import _refresh_lobby_message, _auto_start_match
    import time
    seconds_left = max(0, int(config.LOBBY_TIMEOUT_SECONDS - (time.time() - match.created_at)))
    await _refresh_lobby_message(match, context, seconds_left)

    if match.team_a.size >= config.MIN_PLAYERS_PER_TEAM and match.team_b.size >= config.MIN_PLAYERS_PER_TEAM:
        await _auto_start_match(match, context)


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.status != MatchStatus.LOBBY:
        await update.message.reply_text("There's no open lobby to leave right now.")
        return

    if match.mode is MatchMode.SOLO:
        await update.message.reply_text("Use /leavesolo for Solo Match, not /remove.")
        return

    team = match.find_team_of(user.id)
    if team is None:
        await update.message.reply_text("You're not in a team yet.")
        return

    team.remove_player(user.id)
    await update.message.reply_text("👋 You've been removed from your team.")

    from handlers.lobby import _refresh_lobby_message
    import time
    seconds_left = max(0, int(config.LOBBY_TIMEOUT_SECONDS - (time.time() - match.created_at)))
    await _refresh_lobby_message(match, context, seconds_left)
