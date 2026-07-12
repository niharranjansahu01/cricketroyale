"""
Overs selection (1-20), Team Match only. Solo Match/Royale mode has no
overs cap -- each player's turn simply continues until they're out.
"""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from handlers.start import get_store
from utils.models import MatchStatus


async def overs_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.status != MatchStatus.OVERS_SELECT:
        await query.answer("Overs selection isn't active right now.", show_alert=True)
        return

    winner_team = match.team(match.toss_winner)
    if user.id != winner_team.captain_id:
        await query.answer("Only the toss-winning captain can set the overs.", show_alert=True)
        return

    overs = int(query.data.split(":")[1])
    match.overs = overs
    match.status = MatchStatus.AWAITING_LINEUP
    await query.answer(f"{overs} over match!")

    batting_captain = match.batting_team.players[match.batting_team.captain_id]
    bowling_captain = match.bowling_team.players[match.bowling_team.captain_id]

    text = (
        f"🏏 *Match set: {overs} overs!*\n\n"
        f"{batting_captain.display_name} ({match.batting_team.name}), use /batting to pick "
        f"your striker and non-striker.\n"
        f"{bowling_captain.display_name} ({match.bowling_team.name}), use /bowling to pick "
        f"your first bowler."
    )
    await context.bot.send_message(chat_id=match.chat_id, text=text, parse_mode=ParseMode.MARKDOWN)
