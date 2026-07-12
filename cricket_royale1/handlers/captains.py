"""
Captain selection: only members of Team A can become Team A captain, and
likewise for Team B. Once both captains are set, the match moves to toss.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from handlers.start import get_store
from utils.models import MatchStatus, TeamKey

logger = logging.getLogger(__name__)


async def captain_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.status != MatchStatus.CAPTAIN_SELECT:
        await query.answer("Captain selection isn't active right now.", show_alert=True)
        return

    team_letter = query.data.split(":")[1]
    team_key = TeamKey.A if team_letter == "A" else TeamKey.B
    team = match.team(team_key)

    if user.id not in team.players:
        await query.answer(f"You must be a member of {team.name} to captain it.", show_alert=True)
        return

    if team.captain_id is not None:
        await query.answer(f"{team.name} already has a captain.", show_alert=True)
        return

    team.captain_id = user.id
    await query.answer(f"You are now {team.name} captain! 🧢")

    await _refresh_captain_message(match, context)

    if match.team_a.captain_id and match.team_b.captain_id:
        from handlers.toss import start_toss
        await start_toss(match, context)


async def _refresh_captain_message(match, context: ContextTypes.DEFAULT_TYPE) -> None:
    from utils.keyboards import captain_select_keyboard

    a_cap = match.team_a.players.get(match.team_a.captain_id)
    b_cap = match.team_b.players.get(match.team_b.captain_id)
    text = (
        "🧢 *Captain Selection*\n\n"
        f"🅰️ Team A captain: {a_cap.display_name if a_cap else '_not chosen yet_'}\n"
        f"🅱️ Team B captain: {b_cap.display_name if b_cap else '_not chosen yet_'}\n\n"
        "Tap below if you're a member of that team."
    )
    try:
        if match.lobby_message_id:
            await context.bot.edit_message_text(
                chat_id=match.chat_id,
                message_id=match.lobby_message_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=captain_select_keyboard(),
            )
    except Exception as exc:  # noqa: BLE001 - best-effort UI refresh
        logger.debug("Could not refresh captain message: %s", exc)
