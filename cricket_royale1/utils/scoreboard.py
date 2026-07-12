"""
Formats the live scoreboard message shown in the group chat.
"""

from utils.models import MatchMode, MatchState

DIVIDER = "━━━━━━━━━━━━━━━━━━"


def _overs_display(match: MatchState) -> str:
    if match.mode is MatchMode.SOLO:
        return f"{match.current_over}.{match.current_ball}"
    return f"{match.current_over}.{match.current_ball}/{match.overs}"


def format_scoreboard(match: MatchState) -> str:
    batting = match.batting_team
    bowling = match.bowling_team

    striker = batting.players.get(match.striker_id) if match.striker_id else None
    non_striker = batting.players.get(match.non_striker_id) if match.non_striker_id else None
    bowler = bowling.players.get(match.bowler_id) if match.bowler_id else None

    if match.mode is MatchMode.SOLO:
        name = striker.display_name if striker else "Batter"
        header = f"🏏 *{name}* batting — *{match.score}/{match.wickets}*  ({_overs_display(match)} ov)"
    else:
        header = f"🏏 *{batting.name}* *{match.score}/{match.wickets}*  ({_overs_display(match)} ov)"

    lines = [
        "⚡ *LIVE SCOREBOARD* ⚡",
        DIVIDER,
        header,
        f"📈 Run rate: {match.run_rate()}",
    ]

    if match.target is not None:
        req_rr = match.required_run_rate()
        remaining = max(match.target - match.score, 0)
        lines.append(f"🎯 Target: {match.target}  |  Need {remaining} runs")
        if req_rr is not None:
            lines.append(f"📊 Required run rate: {req_rr}")

    lines.append("")

    if striker and match.mode is not MatchMode.SOLO:
        lines.append(f"🔸 *{striker.display_name}*  {striker.runs} ({striker.balls_faced}b) *")
    if non_striker:
        lines.append(f"◾ {non_striker.display_name}  {non_striker.runs} ({non_striker.balls_faced}b)")
    if bowler:
        overs_bowled = bowler.balls_bowled // 6
        balls_part = bowler.balls_bowled % 6
        lines.append(
            f"🎯 Bowler: *{bowler.display_name}*  "
            f"{overs_bowled}.{balls_part}-{bowler.runs_conceded}-{bowler.wickets_taken}"
        )

    if match.this_over_balls:
        lines.append("")
        lines.append("🔴 This over: " + " ".join(match.this_over_balls))

    return "\n".join(lines)


def format_dm_bowl_prompt(match: MatchState) -> str:
    """The message shown inside the bowler's private chat with the bot,
    right after they deep-link in to bowl -- mirrors the 'Match in
    Progress! / Batter: X / Over Status: A.B / Your Turn to Bowl!' style."""
    batting = match.batting_team
    striker = batting.players.get(match.striker_id) if match.striker_id else None

    over_display = f"{match.current_over}.{match.current_ball}"
    if match.mode is not MatchMode.SOLO and match.overs:
        over_display += f" / {match.overs}"

    lines = ["🏏✨ *Match in Progress!* ✨🏏", DIVIDER, ""]
    if striker:
        lines.append(f"🏏 Batter: *{striker.display_name}*! ({striker.runs} off {striker.balls_faced})")
    lines.append(f"🥎 Over Status: {over_display}.")
    lines.append("")
    lines.append("👉 *Your Turn to Bowl!* Type a number from 1 to 6.")
    return "\n".join(lines)


def format_bowl_prompt(match: MatchState) -> str:
    """Compact status shown alongside the bowling GIF, right before the
    current bowler is prompted to bowl -- mirrors the 'Batter / Bowler /
    check your DM' style status card."""
    batting = match.batting_team
    bowling = match.bowling_team
    striker = batting.players.get(match.striker_id) if match.striker_id else None
    bowler = bowling.players.get(match.bowler_id) if match.bowler_id else None

    over_display = f"{match.current_over}.{match.current_ball}"
    if match.mode is not MatchMode.SOLO and match.overs:
        over_display += f" / {match.overs}"

    lines = ["📊 *Status* 📊", DIVIDER]
    if striker:
        lines.append(f"🏏 Batter: *{striker.display_name}* ({striker.runs} off {striker.balls_faced})")
    if bowler:
        lines.append(f"🥎 Bowler: *{bowler.display_name}* (Over: {over_display})")
    lines.append("")
    if bowler:
        lines.append(f"👉 {bowler.display_name}, check your DM to bowl! 🤫🥎")
    return "\n".join(lines)


def format_ball_delivered(striker_name: str) -> str:
    """Shown in the group right after the bowler has locked in their
    delivery via DM, prompting the striker to type their shot."""
    return f"🚨 *Ball delivered* 🌀\n👉 {striker_name}, type 0-6 to hit! 🏏🔴"


def format_innings_summary(match: MatchState, team: "TeamState") -> str:  # type: ignore[name-defined]
    lines = [f"📋 *{team.name} Innings Summary* 📋", DIVIDER]
    for p in team.players.values():
        if p.balls_faced > 0 or p.is_out:
            status = "out" if p.is_out else "not out"
            lines.append(f"🏏 {p.display_name}: {p.runs} ({p.balls_faced}b) — {status}")
    for p in team.players.values():
        if p.balls_bowled > 0:
            overs_bowled = p.balls_bowled // 6
            balls_part = p.balls_bowled % 6
            lines.append(
                f"🥎 {p.display_name} (bowling): {overs_bowled}.{balls_part}-"
                f"{p.runs_conceded}-{p.wickets_taken}"
            )
    return "\n".join(lines)
