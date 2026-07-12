"""
Solo Match ("Royale" mode): a join-order based, multiplayer, no-toss format.

Whoever joins first bats first. Everyone else who has already joined bowls
for that innings, rotating one full over at a time in join order (starting
right after the current batter, wrapping around). When the batter is
dismissed, the next player in join order comes in to bat, and the bowling
rotation is recomputed from everyone else (including players who have
already had their turn -- being out just means you can no longer bat, you
keep bowling for the rest of the match). Once every joined player has had
a turn to bat, the match ends and whoever scored the most runs wins.

Reuses the same ball-resolution engine as Team Match (handlers/gameplay.py):
team_a is repurposed each mini-innings to hold just the current batter,
and team_b holds the current bowling pool.
"""

from __future__ import annotations

import logging
import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

import config
from handlers.start import get_store
from utils.media import send_photo_or_text
from utils.models import MatchMode, MatchState, MatchStatus, Player, TeamKey

logger = logging.getLogger(__name__)


async def soloscore_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Anyone in the chat can run this any time to see a live, tree-style
    scorecard for the current Solo Match (Royale mode) -- batting figures,
    bowling figures, and a per-over 'spell' breakdown for each player."""
    chat = update.effective_chat
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.mode is not MatchMode.SOLO:
        await update.message.reply_text("There's no active Solo Match in this chat.")
        return

    if not match.royale_order:
        await update.message.reply_text("No one has joined this Solo Match yet.")
        return

    lines = [
        "🌀 ──────────",
        "⚡ *SOLO SCORECARD*",
        "────────── 🌀",
        "",
    ]

    for uid in match.royale_order:
        p = match.royale_players[uid]

        if p.is_out:
            status = "❌"
        elif match.status == MatchStatus.IN_PROGRESS and uid == match.striker_id:
            status = "🏏"
        elif match.status == MatchStatus.IN_PROGRESS and uid == match.bowler_id:
            status = "🥎"
        else:
            status = "⏳"

        sr = round((p.runs / p.balls_faced) * 100, 1) if p.balls_faced else 0.0
        bowl_overs = p.balls_bowled // 6
        bowl_balls = p.balls_bowled % 6
        eco = round(p.runs_conceded / (p.balls_bowled / 6), 1) if p.balls_bowled else 0.0

        lines.append(f"👤 *{p.display_name}* {status}")
        lines.append(f"├ 🏏 {p.runs}({p.balls_faced}) | SR {sr}")
        lines.append(f"├ 🥎 {p.wickets_taken}W | {p.runs_conceded}R | {bowl_overs}.{bowl_balls}ov | Eco {eco}")

        if p.spells:
            for i, spell in enumerate(p.spells, start=1):
                sp_overs = spell["balls"] // 6
                sp_balls = spell["balls"] % 6
                prefix = "└" if i == len(p.spells) else "├"
                lines.append(
                    f"{prefix} 📋 Spell{i} | {sp_overs}.{sp_balls}ov | {spell['runs']}R | {spell['wickets']}W"
                )
        else:
            lines.append("└ 📋 No spells")

        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


def _join_text(match: MatchState, seconds_left: int) -> str:
    lines = [
        "🏏 *Solo Match (Royale)!*",
        "",
        "❓ *Queue Open!* (1 over = 6 balls, rotates automatically)",
        "⚖️",
        "👉 Type /join",
        "👉 Type /leavesolo to exit the queue",
        "👉 The Admin (whoever started the match) can type /startsolo",
        "",
        f"👥 *Joined ({len(match.royale_order)}):*",
    ]
    if match.royale_order:
        for i, uid in enumerate(match.royale_order, start=1):
            p = match.royale_players[uid]
            lines.append(f"{i}. {p.display_name}")
    else:
        lines.append("  _(no one yet)_")
    lines.append("")
    lines.append(f"⏱ Auto-starts in {seconds_left}s (needs at least 2 players).")
    return "\n".join(lines)


async def start_solo_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        await context.bot.send_message(
            chat_id=chat.id,
            text="🏏 Solo Match is now multiplayer -- it needs a group chat. "
                 "Add me to a group and try again from there!",
        )
        return

    db = context.application.bot_data.get("db")
    if db is not None:
        await db.upsert_chat(chat.id, chat.type, chat.title)

    match = MatchState(chat_id=chat.id, mode=MatchMode.SOLO, initiator_id=user.id, creator_id=user.id)
    match.chat_username = chat.username
    match.status = MatchStatus.LOBBY
    store = get_store(context)
    store.set(match)

    msg = await send_photo_or_text(
        context=context,
        chat_id=chat.id,
        photo_path=config.solo_match_banner(),
        caption=_join_text(match, config.LOBBY_TIMEOUT_SECONDS),
    )
    match.lobby_message_id = msg.message_id
    match.banner_message_id = msg.message_id

    job_name = f"royale_timeout_{chat.id}_{match.match_id}"
    match.lobby_job_name = job_name
    context.job_queue.run_once(
        royale_timeout_callback,
        when=config.LOBBY_TIMEOUT_SECONDS,
        chat_id=chat.id,
        name=job_name,
        data={"chat_id": chat.id, "match_id": match.match_id},
    )


async def _refresh_join_message(match: MatchState, context: ContextTypes.DEFAULT_TYPE, seconds_left: int) -> None:
    if match.lobby_message_id is None:
        return
    text = _join_text(match, seconds_left)
    try:
        if match.banner_message_id == match.lobby_message_id:
            # It's the original banner message -- may be a photo.
            await context.bot.edit_message_caption(
                chat_id=match.chat_id, message_id=match.lobby_message_id,
                caption=text, parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await context.bot.edit_message_text(
                chat_id=match.chat_id, message_id=match.lobby_message_id,
                text=text, parse_mode=ParseMode.MARKDOWN,
            )
    except TelegramError:
        # Fall back: try the other edit method (covers text-fallback case
        # where the banner image was missing and the message is plain text).
        try:
            await context.bot.edit_message_text(
                chat_id=match.chat_id, message_id=match.lobby_message_id,
                text=text, parse_mode=ParseMode.MARKDOWN,
            )
        except TelegramError as exc:
            logger.debug("Could not refresh Royale join message: %s", exc)


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.mode is not MatchMode.SOLO or match.status != MatchStatus.LOBBY:
        await update.message.reply_text("There's no open Solo Match queue right now. Use /start and choose Solo Match.")
        return

    if user.id in match.royale_players:
        await update.message.reply_text("You're already in the queue!")
        return

    if len(match.royale_order) >= config.MAX_PLAYERS_PER_TEAM * 2:
        await update.message.reply_text("The queue is full.")
        return

    match.royale_players[user.id] = Player(user_id=user.id, username=user.username, first_name=user.first_name)
    match.royale_order.append(user.id)
    await update.message.reply_text(f"✅ Joined! Your position: {len(match.royale_order)}")

    seconds_left = max(0, int(config.LOBBY_TIMEOUT_SECONDS - (time.time() - match.created_at)))
    await _refresh_join_message(match, context, seconds_left)


async def leavesolo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.mode is not MatchMode.SOLO or match.status != MatchStatus.LOBBY:
        await update.message.reply_text("There's no open Solo Match queue right now.")
        return

    if user.id not in match.royale_players:
        await update.message.reply_text("You're not in the queue.")
        return

    del match.royale_players[user.id]
    match.royale_order.remove(user.id)
    await update.message.reply_text("👋 You've left the queue.")

    seconds_left = max(0, int(config.LOBBY_TIMEOUT_SECONDS - (time.time() - match.created_at)))
    await _refresh_join_message(match, context, seconds_left)


async def startsolo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    store = get_store(context)
    match = store.get(chat.id)

    if match is None or match.mode is not MatchMode.SOLO or match.status != MatchStatus.LOBBY:
        await update.message.reply_text("There's no open Solo Match queue right now.")
        return

    if user.id != match.initiator_id:
        await update.message.reply_text("Only whoever started this Solo Match can force it to start early.")
        return

    if len(match.royale_order) < 2:
        await update.message.reply_text("At least 2 players are needed to start.")
        return

    if match.lobby_job_name:
        for job in context.application.job_queue.get_jobs_by_name(match.lobby_job_name):
            job.schedule_removal()

    await update.message.reply_text("▶️ Match is starting!")
    await _start_royale_match(match, context)


async def _cancel_royale(match: MatchState, context: ContextTypes.DEFAULT_TYPE, reason: str) -> None:
    match.status = MatchStatus.CANCELLED
    store = get_store(context)
    if match.lobby_job_name:
        for job in context.application.job_queue.get_jobs_by_name(match.lobby_job_name):
            job.schedule_removal()
    text = f"🛑 *Solo Match Cancelled*\n\n{reason}"
    try:
        if match.banner_message_id == match.lobby_message_id:
            await context.bot.edit_message_caption(
                chat_id=match.chat_id, message_id=match.lobby_message_id,
                caption=text, parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await context.bot.edit_message_text(
                chat_id=match.chat_id, message_id=match.lobby_message_id,
                text=text, parse_mode=ParseMode.MARKDOWN,
            )
    except TelegramError as exc:
        logger.debug("Could not edit cancelled Royale message: %s", exc)
    store.remove(match.chat_id)


async def royale_timeout_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    store = get_store(context)
    match = store.get(chat_id)

    if match is None or match.status != MatchStatus.LOBBY or match.mode is not MatchMode.SOLO:
        return

    if len(match.royale_order) < 2:
        await _cancel_royale(
            match, context,
            reason="Not enough players joined (need at least 2). Use /start to try again.",
        )
    else:
        await _start_royale_match(match, context)


async def _start_royale_match(match: MatchState, context: ContextTypes.DEFAULT_TYPE) -> None:
    if match.status != MatchStatus.LOBBY:
        return
    match.status = MatchStatus.IN_PROGRESS
    match.royale_batter_index = 0

    names = ", ".join(match.royale_players[uid].display_name for uid in match.royale_order)
    await context.bot.send_message(
        chat_id=match.chat_id,
        text=f"✅ *Match starting!* Batting order: {names}",
        parse_mode=ParseMode.MARKDOWN,
    )
    await _setup_next_batter(match, context)


async def _setup_next_batter(match: MatchState, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Configure the pseudo team_a (batter) / team_b (bowling pool) for
    whoever's turn it is to bat next, and kick off the first delivery."""
    n = len(match.royale_order)
    idx = match.royale_batter_index
    batter_id = match.royale_order[idx]

    bowling_pool = [match.royale_order[(idx + 1 + i) % n] for i in range(n - 1)]
    match.royale_bowling_pool = bowling_pool
    match.royale_bowl_pointer = 0

    match.team_a.players = {batter_id: match.royale_players[batter_id]}
    match.team_a.captain_id = batter_id
    match.team_b.players = {pid: match.royale_players[pid] for pid in bowling_pool}
    match.team_b.captain_id = bowling_pool[0] if bowling_pool else None
    match.batting_team_key = TeamKey.A

    match.score = 0
    match.wickets = 0
    match.current_over = 0
    match.current_ball = 0
    match.this_over_balls = []
    match.striker_id = batter_id
    match.non_striker_id = None
    match.bowler_id = bowling_pool[0] if bowling_pool else None
    match.last_bowler_id = None

    batter = match.royale_players[batter_id]
    await context.bot.send_message(
        chat_id=match.chat_id,
        text=f"🏏 *Now batting:* {batter.display_name} (#{idx + 1} of {n})",
        parse_mode=ParseMode.MARKDOWN,
    )

    from handlers.gameplay import maybe_ready_to_bowl
    await maybe_ready_to_bowl(match, context)


async def advance_royale_bowler(match: MatchState, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called by gameplay.py after an over completes -- automatically
    rotates to the next bowler in the pool (no captain selection needed)."""
    if not match.royale_bowling_pool:
        return
    match.royale_bowl_pointer = (match.royale_bowl_pointer + 1) % len(match.royale_bowling_pool)
    match.bowler_id = match.royale_bowling_pool[match.royale_bowl_pointer]


async def advance_royale_batter(match: MatchState, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called by gameplay.py when the current batter is out -- moves on to
    the next player in join order, or finishes the match if everyone has
    already batted."""
    batter_id = match.royale_order[match.royale_batter_index]
    batter = match.royale_players[batter_id]
    await context.bot.send_message(
        chat_id=match.chat_id,
        text=f"🏏 {batter.display_name} out! Final score: {batter.runs} ({batter.balls_faced} balls)",
        parse_mode=ParseMode.MARKDOWN,
    )

    match.royale_batter_index += 1
    if match.royale_batter_index >= len(match.royale_order):
        await _finish_royale(match, context)
    else:
        await _setup_next_batter(match, context)


async def _finish_royale(match: MatchState, context: ContextTypes.DEFAULT_TYPE) -> None:
    store = get_store(context)
    db = context.application.bot_data["db"]

    ranked = sorted(
        match.royale_players.values(),
        key=lambda p: (-p.runs, p.balls_faced),
    )

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆✨ *SOLO MATCH COMPLETE!* ✨🏆", "━━━━━━━━━━━━━━━━━━", "", "📋 *Final Standings:*"]
    for i, p in enumerate(ranked):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} *{p.display_name}* — {p.runs} runs ({p.balls_faced}b), {p.wickets_taken} wkts")

    winner = ranked[0]
    lines.append("")
    lines.append(f"🎉 *{winner.display_name} wins with {winner.runs} runs!* 🎉")

    await context.bot.send_message(
        chat_id=match.chat_id, text="\n".join(lines), parse_mode=ParseMode.MARKDOWN,
    )

    from utils.player_of_match import send_player_of_the_match
    await send_player_of_the_match(context, match.chat_id, winner)

    for p in match.royale_players.values():
        is_fifty = 50 <= p.runs < 100
        is_century = p.runs >= 100
        is_duck = p.is_out and p.runs == 0
        await db.record_player_result(
            user_id=p.user_id,
            username=p.username,
            first_name=p.first_name,
            runs=p.runs,
            balls_faced=p.balls_faced,
            wickets=p.wickets_taken,
            balls_bowled=p.balls_bowled,
            runs_conceded=p.runs_conceded,
            won=(p.user_id == winner.user_id),
            fours=p.fours,
            sixes=p.sixes,
            is_fifty=is_fifty,
            is_century=is_century,
            is_duck=is_duck,
            was_out=p.is_out,
            is_solo=True,
            is_motm=(p.user_id == winner.user_id),
        )

    await db.log_match(
        match_id=match.match_id,
        chat_id=match.chat_id,
        mode=match.mode.value,
        overs=None,
        winner=winner.display_name,
        team_a_score=winner.runs,
        team_b_score=None,
    )

    match.status = MatchStatus.COMPLETED
    store.remove(match.chat_id)
