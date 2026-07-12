"""
Safe media helpers.

If the operator hasn't dropped the real banner/GIF files into assets/ yet,
these helpers degrade gracefully to a plain text message instead of
crashing the bot with a "file not found" error. They also retry once on
a network timeout (large GIF/MP4 uploads can occasionally time out) and
fall back to plain text rather than letting the whole update crash.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from telegram import Message
from telegram.constants import ParseMode
from telegram.error import TimedOut
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def send_photo_or_text(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    photo_path: Path,
    caption: str,
    reply_markup=None,
) -> Message:
    if photo_path.exists():
        for attempt in (1, 2):
            try:
                with open(photo_path, "rb") as f:
                    return await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=f,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup,
                    )
            except TimedOut:
                logger.warning("send_photo timed out (attempt %d) for %s", attempt, photo_path)
        logger.warning("send_photo kept timing out for %s - falling back to text.", photo_path)
    else:
        logger.warning("Missing asset %s - falling back to text.", photo_path)
    return await context.bot.send_message(
        chat_id=chat_id,
        text=caption,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
    )


async def send_gif_or_text(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    gif_path: Path,
    caption: Optional[str] = None,
    reply_markup=None,
) -> Optional[Message]:
    if gif_path.exists():
        for attempt in (1, 2):
            try:
                with open(gif_path, "rb") as f:
                    return await context.bot.send_animation(
                        chat_id=chat_id,
                        animation=f,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN if caption else None,
                        reply_markup=reply_markup,
                    )
            except TimedOut:
                logger.warning("send_animation timed out (attempt %d) for %s", attempt, gif_path)
        logger.warning("send_animation kept timing out for %s - falling back to text.", gif_path)
    else:
        logger.warning("Missing asset %s - skipping GIF.", gif_path)
    if caption:
        return await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )
    return None
