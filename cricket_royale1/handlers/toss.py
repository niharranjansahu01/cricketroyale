"""
Toss: send the toss GIF, randomly pick a winning captain, let them choose
to Bat or Bowl first.
"""

from __future__ import annotations

import logging
import random

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
from handlers.start import get_store
from utils.keyboards import toss_decision_keyboard
from utils.media import send_gif_or_text
from utils.models import MatchStatus, TeamKey

logger = logging.getLogger(__name__)


async def start_toss(match, context: ContextTypes.DEFAULT_TYPE) -> None:
    match.status = MatchStatus.TOSS
    winner_key = random.choice([TeamKey.A, TeamKey.B])
    match.toss_winner = winner_key
    winner_team = match.team(winner_key)
    winner_captain = winner_team.players[winner_team.captain_id]

    caption = (
        f"🪙✨ *TOSS TIME!* ✨🪙\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🎉 *{winner_team.name}* (captain {winner_captain.display_name}) has won the toss!\n\n"
        f"👉 {winner_captain.display_name}, will you Bat or Bowl first?"
    )
    await send_gif_or_text(
        context=context,
        chat_id=match.chat_id,
        gif_path=config.toss_gif(),
        caption=caption,
        reply_markup=toss_decision_keyboard(),
    )


async def toss_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.status != MatchStatus.TOSS:
        await query.answer("There's no toss happening right now.", show_alert=True)
        return

    winner_team = match.team(match.toss_winner)
    if user.id != winner_team.captain_id:
        await query.answer("Only the toss-winning captain can make this call.", show_alert=True)
        return

    decision = query.data.split(":")[2]  # "bat" or "bowl"
    match.toss_decision = decision
    match.batting_team_key = match.toss_winner if decision == "bat" else match.toss_winner.other
    match.status = MatchStatus.OVERS_SELECT

    await query.answer(f"{winner_team.name} will {decision} first!")

    from utils.keyboards import overs_keyboard

    text = (
        f"✅ *{winner_team.name}* chose to *{decision.upper()} first*.\n\n"
        f"🏏 Batting first: *{match.batting_team.name}*\n"
        f"🎯 Bowling first: *{match.bowling_team.name}*\n\n"
        "How many overs should this match be? (1-20)"
    )
    await context.bot.send_message(
        chat_id=match.chat_id, text=text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=overs_keyboard(),
    )
