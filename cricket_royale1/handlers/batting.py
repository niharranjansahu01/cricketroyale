"""
/batting - the batting captain picks the striker and non-striker (or a new
batter after a wicket) using inline buttons. No manual number entry here.
"""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from handlers.start import get_store
from utils.keyboards import batting_select_keyboard
from utils.models import MatchMode, MatchStatus


async def batting_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.status not in (MatchStatus.AWAITING_LINEUP, MatchStatus.IN_PROGRESS):
        await update.message.reply_text("There's no match awaiting a batting lineup right now.")
        return

    if match.mode is MatchMode.SOLO:
        await update.message.reply_text("Solo Match (Royale mode) sets the batting order automatically by join order -- /batting isn't needed.")
        return

    batting_team = match.batting_team
    if user.id != batting_team.captain_id:
        await update.message.reply_text(
            f"Only the {batting_team.name} captain can select batters."
        )
        return

    if match.striker_id and match.non_striker_id:
        await update.message.reply_text("Both batters are already at the crease.")
        return

    picking_non_striker = match.striker_id is not None
    label = "non-striker" if picking_non_striker else "striker"
    await update.message.reply_text(
        f"🏏 Pick your {label}:",
        reply_markup=batting_select_keyboard(match, picking_non_striker),
    )


async def batting_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.status not in (MatchStatus.AWAITING_LINEUP, MatchStatus.IN_PROGRESS):
        await query.answer("No lineup selection active.", show_alert=True)
        return

    batting_team = match.batting_team
    if user.id != batting_team.captain_id:
        await query.answer("Only the batting captain can do this.", show_alert=True)
        return

    _, stage, user_id_str = query.data.split(":")
    picked_id = int(user_id_str)
    player = batting_team.players.get(picked_id)
    if player is None or player.is_out:
        await query.answer("That player isn't available.", show_alert=True)
        return

    if stage == "striker":
        if match.striker_id is not None:
            await query.answer("Striker already chosen.", show_alert=True)
            return
        if picked_id == match.non_striker_id:
            await query.answer("That player is already the non-striker.", show_alert=True)
            return
        match.striker_id = picked_id
        await query.answer(f"{player.display_name} is on strike!")
        await query.edit_message_text(f"🔸 Striker: {player.display_name}")
        if match.non_striker_id is None and batting_team.size > 1:
            await context.bot.send_message(
                chat_id=match.chat_id,
                text="Now pick your non-striker:",
                reply_markup=batting_select_keyboard(match, True),
            )
    else:  # non-striker
        if picked_id == match.striker_id:
            await query.answer("That player is already the striker.", show_alert=True)
            return
        match.non_striker_id = picked_id
        await query.answer(f"{player.display_name} is the non-striker!")
        await query.edit_message_text(f"◾ Non-striker: {player.display_name}")

    from handlers.gameplay import maybe_ready_to_bowl
    await maybe_ready_to_bowl(match, context)
