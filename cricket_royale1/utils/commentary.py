"""
Hard-hitting, high-energy English commentary for every ball bowled in
Cricket Royale -- one line fires after every single delivery, for every
run value 0-6 and every wicket, in both Team Match and Solo Match/Royale
mode (they share the same ball-resolution engine).
"""

import random

DOT_BALL = [
    "DOT BALL! Absolutely nailed the yorker, batter has no answer!",
    "BEATEN ALL ENDS UP! Ferocious delivery, not a run in sight!",
    "Stonewalled! The bat comes down like a wall — no run!",
    "Unplayable stuff! The batter can only watch it fly through!",
    "Ice in the veins from the bowler — dot ball, pressure building!",
]

ONE_RUN = [
    "Sharp single! Smart cricket, they steal the strike!",
    "Nurdled away for a quick one — clinical running!",
    "Single taken under pressure — nerves of steel!",
    "Worked into the gap, one run banked ruthlessly!",
]

TWO_RUNS = [
    "TWO! Ripped into the gap, brutal running between the wickets!",
    "Two more! Relentless, they're carving this bowler apart!",
    "Smart placement, two runs muscled through the field!",
    "TWO! Full-blooded shot, the fielders had zero chance!",
]

THREE_RUNS = [
    "THREE! Blistering running, they're pushing this to the limit!",
    "Three big ones! Gap found, legs pumping like pistons!",
    "THREE! Ruthless placement, the fielder's chasing shadows!",
]

FOUR_RUNS = [
    "FOUR! ABSOLUTELY MURDERED! Cracked through the covers like a bullet!",
    "FOUR! That's raw brutality — smashed through point, no chance!",
    "FOUR! Pure carnage! The boundary rope is on fire!",
    "FOUR! Timed to perfection, ruthless and unstoppable!",
    "FOUR! The bowler is shell-shocked — that shot had NO mercy!",
]

FIVE_RUNS = [
    "FIVE! Chaos in the field, and they punish every inch of it!",
    "FIVE runs! Brutal running plus a fumble — no mercy shown!",
    "FIVE! The fielders are in meltdown, and the runs keep coming!",
]

SIX_RUNS = [
    "SIX!! OBLITERATED! That ball is never coming back!",
    "SIX!! MASSIVE! Launched into the next postcode — pure violence!",
    "SIX!! The bowler is DESTROYED — that was an absolute missile!",
    "SIX!! Sheer brutality — clean, ferocious, unanswerable!",
    "SIX!! GONE! That's as hard as cricket balls get hit!",
]

WICKET = [
    "WICKET!! GOT HIM! Same number — bowled all ends up, BRUTAL strike!",
    "WICKET!! GONE! The bowler DEMOLISHES the batter at the perfect time!",
    "WICKET!! Numbers matched — ICE COLD finish, no escape!",
    "WICKET!! DESTROYED! That's a hammer blow to the batting side!",
    "WICKET!! CLINICAL! The bowler reads it perfectly and STRIKES!",
]

_RUN_MAP = {
    0: DOT_BALL,
    1: ONE_RUN,
    2: TWO_RUNS,
    3: THREE_RUNS,
    4: FOUR_RUNS,
    5: FIVE_RUNS,
    6: SIX_RUNS,
}


def get_commentary(runs: int, is_wicket: bool) -> str:
    """Return a random hard-hitting commentary line for the outcome of a
    ball. Works identically for every run value (0-6) and for wickets, in
    both Team Match and Solo Match/Royale mode."""
    if is_wicket:
        return random.choice(WICKET)
    pool = _RUN_MAP.get(runs, DOT_BALL)
    return random.choice(pool)
