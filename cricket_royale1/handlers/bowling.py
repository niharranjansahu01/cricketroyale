"""
/bowling - the bowling captain picks the bowler for the next over using
inline buttons. The bowler who just finished an over cannot be reselected
for the following over (standard cricket rule).
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from handlers.start import get_store
from utils.keyboards import bowling_select_keyboard
from utils.models import MatchMode, MatchStatus


async def bowling_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.status not in (MatchStatus.AWAITING_LINEUP, MatchStatus.IN_PROGRESS):
        await update.message.reply_text("There's no match awaiting a bowler right now.")
        return

    if match.mode is MatchMode.SOLO:
        await update.message.reply_text("Solo Match (Royale mode) rotates the bowler automatically -- /bowling isn't needed.")
        return

    bowling_team = match.bowling_team
    if user.id != bowling_team.captain_id:
        await update.message.reply_text(f"Only the {bowling_team.name} captain can pick the bowler.")
        return

    if match.bowler_id is not None:
        await update.message.reply_text("A bowler is already set for this over.")
        return

    await update.message.reply_text(
        "🎯 Pick your bowler:",
        reply_markup=bowling_select_keyboard(match),
    )


async def bowling_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.status not in (MatchStatus.AWAITING_LINEUP, MatchStatus.IN_PROGRESS):
        await query.answer("No bowler selection active.", show_alert=True)
        return

    bowling_team = match.bowling_team
    if user.id != bowling_team.captain_id:
        await query.answer("Only the bowling captain can do this.", show_alert=True)
        return

    picked_id = int(query.data.split(":")[1])
    if picked_id == match.last_bowler_id:
        await query.answer("This bowler just bowled the previous over.", show_alert=True)
        return

    player = bowling_team.players.get(picked_id)
    if player is None:
        await query.answer("That player isn't available.", show_alert=True)
        return

    match.bowler_id = picked_id
    await query.answer(f"{player.display_name} will bowl this over!")
    await query.edit_message_text(f"🎯 Bowler: {player.display_name}")

    from handlers.gameplay import maybe_ready_to_bowl
    await maybe_ready_to_bowl(match, context)
