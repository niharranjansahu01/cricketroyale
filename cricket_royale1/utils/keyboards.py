"""
Inline keyboard builders for Cricket Royale.

Keeping all keyboard construction in one place makes callback_data
conventions easy to audit. Convention: "namespace:action:arg1:arg2".
"""

from __future__ import annotations

from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import MAX_OVERS, MIN_OVERS
from utils.models import MatchState, TeamKey


def start_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🏏 Solo Match", callback_data="start:solo")],
        [InlineKeyboardButton("👥 Team Match", callback_data="start:team")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="start:leaderboard")],
        [InlineKeyboardButton("❌ Cancel", callback_data="start:cancel")],
    ]
    return InlineKeyboardMarkup(rows)


def host_select_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🎪 Main Host Banunga", callback_data="host:claim")],
        [InlineKeyboardButton("❌ Cancel", callback_data="host:cancel")],
    ]
    return InlineKeyboardMarkup(rows)


def lobby_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🅰️ Join Team A", callback_data="lobby:join:A"),
            InlineKeyboardButton("🅱️ Join Team B", callback_data="lobby:join:B"),
        ],
        [InlineKeyboardButton("🚪 Leave", callback_data="lobby:leave")],
        [InlineKeyboardButton("🛑 Cancel Lobby", callback_data="lobby:cancel")],
    ]
    return InlineKeyboardMarkup(rows)


def captain_select_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🅰️ Become Team A Captain", callback_data="captain:A")],
        [InlineKeyboardButton("🅱️ Become Team B Captain", callback_data="captain:B")],
    ]
    return InlineKeyboardMarkup(rows)


def toss_call_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("HEADS", callback_data="toss:call:heads"),
            InlineKeyboardButton("TAILS", callback_data="toss:call:tails"),
        ]
    ]
    return InlineKeyboardMarkup(rows)


def toss_decision_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🏏 Bat First", callback_data="toss:decide:bat"),
            InlineKeyboardButton("🎯 Bowl First", callback_data="toss:decide:bowl"),
        ]
    ]
    return InlineKeyboardMarkup(rows)


def overs_keyboard() -> InlineKeyboardMarkup:
    """A grid of buttons for every legal overs value (1-20)."""
    numbers = list(range(MIN_OVERS, MAX_OVERS + 1))
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for n in numbers:
        row.append(InlineKeyboardButton(str(n), callback_data=f"overs:{n}"))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def batting_select_keyboard(match: MatchState, picking_non_striker: bool) -> InlineKeyboardMarkup:
    team = match.batting_team
    rows: List[List[InlineKeyboardButton]] = []
    exclude = {uid for uid in (match.striker_id, match.non_striker_id) if uid is not None}
    for p in team.players.values():
        if p.is_out or p.user_id in exclude:
            continue
        label = p.display_name
        stage = "nonstriker" if picking_non_striker else "striker"
        rows.append([InlineKeyboardButton(label, callback_data=f"batting:{stage}:{p.user_id}")])
    if not rows:
        rows.append([InlineKeyboardButton("(no eligible players)", callback_data="noop")])
    return InlineKeyboardMarkup(rows)


def bowling_select_keyboard(match: MatchState) -> InlineKeyboardMarkup:
    team = match.bowling_team
    rows: List[List[InlineKeyboardButton]] = []
    for p in team.players.values():
        if p.user_id == match.last_bowler_id:
            continue  # can't bowl consecutive overs
        rows.append([InlineKeyboardButton(p.display_name, callback_data=f"bowling:{p.user_id}")])
    if not rows:
        rows.append([InlineKeyboardButton("(no eligible bowlers)", callback_data="noop")])
    return InlineKeyboardMarkup(rows)


def bowl_now_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    url = f"https://t.me/{bot_username}?start=bowl"
    rows = [[InlineKeyboardButton("🎯 Bowl Now (Opens DM)", url=url)]]
    return InlineKeyboardMarkup(rows)


def back_to_game_keyboard(chat_username: str) -> InlineKeyboardMarkup:
    url = f"https://t.me/{chat_username}"
    rows = [[InlineKeyboardButton("⬅ Back to Game", url=url)]]
    return InlineKeyboardMarkup(rows)
