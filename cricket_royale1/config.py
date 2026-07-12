"""
Cricket Royale - Configuration
All tunables, file paths and constants live here so the rest of the
codebase never hard-codes a magic number or path.
"""

import os
import logging
from pathlib import Path

# --------------------------------------------------------------------------
# Core bot settings
# --------------------------------------------------------------------------
BOT_TOKEN: str = os.environ.get("CRICKET_ROYALE_BOT_TOKEN", "8720156552:AAFHa5clWiP21GpN3Bk1J_UfjYCQ_u-pLWg")

# Your personal Telegram numeric user ID. Owner-only commands (/broadcast,
# /botstats, /maintenance, /forceend, /ownerhelp) only work for this ID.
# Find your ID by messaging @userinfobot on Telegram, then either set it
# here directly or via the CRICKET_ROYALE_OWNER_ID environment variable.
OWNER_ID: int = int(os.environ.get("CRICKET_ROYALE_OWNER_ID", "8845203704"))

BASE_DIR: Path = Path(__file__).resolve().parent
ASSETS_DIR: Path = BASE_DIR / "assets"
GIFS_DIR: Path = ASSETS_DIR / "gifs"
DB_PATH: Path = BASE_DIR / "cricket_royale.db"

# --------------------------------------------------------------------------
# Gameplay tunables
# --------------------------------------------------------------------------
MIN_OVERS: int = 1
MAX_OVERS: int = 20

MIN_PLAYERS_PER_TEAM: int = 2
MAX_PLAYERS_PER_TEAM: int = 11

LOBBY_TIMEOUT_SECONDS: int = 120  # 2 minutes

# Balls that rotate the strike when a batter scores them
STRIKE_ROTATING_RUNS = (1, 3, 5)

BALLS_PER_OVER: int = 6

# --------------------------------------------------------------------------
# Asset file paths
# --------------------------------------------------------------------------
# Drop your actual media files into assets/ using these exact base names and
# the bot will pick them up automatically -- .gif, .mp4, or .mov all work,
# since Telegram "GIFs" are sent via send_animation which accepts any of
# them (Telegram itself stores GIFs as soundless MP4s internally).
GIF_SEARCH_EXTENSIONS = (".mp4", ".gif", ".mov")


def _resolve_asset(base_name: str) -> Path:
    """Return the first existing file matching base_name.<ext>, trying
    .mp4 first (most common for cricket-style GIFs), falling back to
    .gif / .mov. If none exist yet, returns the .mp4 path as a
    placeholder -- utils/media.py falls back to text if it's missing.

    This is called fresh every time a GIF is about to be sent (not cached
    at import time), so dropping in or renaming a file takes effect
    immediately -- no bot restart required."""
    for ext in GIF_SEARCH_EXTENSIONS:
        candidate = GIFS_DIR / f"{base_name}{ext}"
        if candidate.exists():
            return candidate
    return GIFS_DIR / f"{base_name}.mp4"


def _resolve_image(base_name: str) -> Path:
    """Same idea as _resolve_asset but for static images (banner). Also
    re-checked live on every call -- see _resolve_asset's note above."""
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = ASSETS_DIR / f"{base_name}{ext}"
        if candidate.exists():
            return candidate
    return ASSETS_DIR / f"{base_name}.jpg"


# NOTE: these are functions, not fixed Path values -- call them (e.g.
# banner_image()) right before sending so a file dropped in after the bot
# started is picked up immediately.
def banner_image() -> Path:
    return _resolve_image("banner")


def team_match_banner() -> Path:
    return _resolve_image("team_match_banner")


def solo_match_banner() -> Path:
    return _resolve_image("solo_match_banner")


def player_of_match_banner() -> Path:
    return _resolve_image("player_of_match_banner")


def welcome_gif() -> Path:
    return _resolve_asset("welcome")


def toss_gif() -> Path:
    return _resolve_asset("toss")


def wicket_gif() -> Path:
    return _resolve_asset("wicket")


def bowling_gif() -> Path:
    return _resolve_asset("bowling")


def ball_delivered_gif() -> Path:
    return _resolve_asset("ball_delivered")


def fifty_gif() -> Path:
    return _resolve_asset("fifty")


def century_gif() -> Path:
    return _resolve_asset("century")


def run_gif(runs: int) -> Path:
    return _resolve_asset(str(runs))


# Pixel position/size of the circular photo frame on the Player of the
# Match banner, measured against the original 1264x842 template. If you
# swap in a differently-sized template, re-measure and update these.
POM_CIRCLE_CENTER = (910, 413)
POM_CIRCLE_RADIUS = 210

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure root logging once at process start."""
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
    # Silence the very chatty httpx/telegram internals a bit.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.Application").setLevel(logging.INFO)
