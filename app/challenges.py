"""The challenge ladder.

You start at 30 days. Finish it and the next tier unlocks. Nothing unlocks
early — the point is that the ladder is earned, not chosen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Tier:
    key: str
    name: str
    days: int
    tagline: str
    rules: List[str]
    grace_days: int  # missed days you can absorb before the streak resets


LADDER: List[Tier] = [
    Tier(
        key="start30",
        name="Start Small — 30",
        days=30,
        tagline="Thirty days of showing up. That's the whole ask.",
        rules=[
            "Train on every day your plan says to train",
            "Move for at least 20 minutes on rest days — a walk counts",
            "Log the day here before you sleep",
        ],
        grace_days=3,
    ),
    Tier(
        key="build60",
        name="Build — 60",
        days=60,
        tagline="The habit exists. Now it gets weight behind it.",
        rules=[
            "Every training session completed, no skipped lifts",
            "Hit your protein target 6 days out of 7",
            "Sleep 7+ hours at least 5 nights a week",
            "Log the day here before you sleep",
        ],
        grace_days=3,
    ),
    Tier(
        key="forge90",
        name="Forge — 90",
        days=90,
        tagline="Ninety days is where other people start noticing.",
        rules=[
            "Every session completed and progressively overloaded",
            "Stick to your eating window every day",
            "One mobility session a week, minimum",
            "Weekly progress photo and one benchmark lift recorded",
        ],
        grace_days=2,
    ),
    Tier(
        key="temper120",
        name="Temper — 120",
        days=120,
        tagline="Four months. This is no longer a challenge, it's your default.",
        rules=[
            "All of the 90 rules",
            "Two conditioning sessions a week alongside lifting",
            "Deload week scheduled and actually taken",
            "No more than one unplanned rest day per month",
        ],
        grace_days=1,
    ),
    Tier(
        key="year365",
        name="Standard — 365",
        days=365,
        tagline="A year. Not a challenge any more — a standard.",
        rules=[
            "All of the 120 rules, held for a year",
            "Re-test your benchmark lifts every 12 weeks",
            "Plan rewritten every 8–12 weeks so it keeps fitting you",
        ],
        grace_days=0,
    ),
]

HARD75 = Tier(
    key="hard75",
    name="75 Hard",
    days=75,
    tagline="The well-known one. Demanding by design, and no grace days.",
    rules=[
        "Two 45-minute workouts a day, one of them outdoors",
        "Follow your chosen eating plan — no drinking",
        "Drink around 4 litres of water",
        "Read 10 pages of non-fiction",
        "Take a progress photo",
        "Miss anything and day one starts again",
    ],
    grace_days=0,
)

ALL_TIERS: Dict[str, Tier] = {t.key: t for t in LADDER + [HARD75]}


@dataclass
class Progress:
    """Check-in state for one challenge attempt."""

    tier_key: str = "start30"
    started: str = field(default_factory=lambda: date.today().isoformat())
    checked_days: List[str] = field(default_factory=list)  # ISO dates
    completed_tiers: List[str] = field(default_factory=list)

    # --- derived ------------------------------------------------------- #
    @property
    def tier(self) -> Tier:
        return ALL_TIERS.get(self.tier_key, LADDER[0])

    @property
    def days_done(self) -> int:
        return len(set(self.checked_days))

    @property
    def percent(self) -> float:
        return min(1.0, self.days_done / self.tier.days)

    @property
    def is_complete(self) -> bool:
        return self.days_done >= self.tier.days

    def checked_today(self, today: Optional[date] = None) -> bool:
        return (today or date.today()).isoformat() in self.checked_days

    def current_streak(self, today: Optional[date] = None) -> int:
        """Consecutive logged days ending today or yesterday."""
        today = today or date.today()
        done = set(self.checked_days)
        cursor = today if today.isoformat() in done else today - timedelta(days=1)
        streak = 0
        while cursor.isoformat() in done:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    def missed_days(self, today: Optional[date] = None) -> int:
        """Elapsed calendar days since start that were never logged."""
        today = today or date.today()
        start = date.fromisoformat(self.started)
        elapsed = (today - start).days + 1
        return max(0, elapsed - self.days_done)

    def at_risk(self, today: Optional[date] = None) -> bool:
        return self.missed_days(today) > self.tier.grace_days

    # --- mutations ------------------------------------------------------ #
    def check_in(self, today: Optional[date] = None) -> None:
        stamp = (today or date.today()).isoformat()
        if stamp not in self.checked_days:
            self.checked_days.append(stamp)

    def undo_today(self, today: Optional[date] = None) -> None:
        stamp = (today or date.today()).isoformat()
        self.checked_days = [d for d in self.checked_days if d != stamp]

    def promote(self) -> Optional[Tier]:
        """Move to the next rung. Returns the new tier, or None at the top."""
        if self.tier_key not in self.completed_tiers:
            self.completed_tiers.append(self.tier_key)
        keys = [t.key for t in LADDER]
        if self.tier_key not in keys:  # 75 Hard sits outside the ladder
            return None
        idx = keys.index(self.tier_key)
        if idx + 1 >= len(keys):
            return None
        self.tier_key = keys[idx + 1]
        self.started = date.today().isoformat()
        self.checked_days = []
        return self.tier

    def restart(self, tier_key: Optional[str] = None) -> None:
        self.tier_key = tier_key or self.tier_key
        self.started = date.today().isoformat()
        self.checked_days = []

    # --- serialisation --------------------------------------------------- #
    def to_dict(self) -> Dict:
        return {
            "tier_key": self.tier_key,
            "started": self.started,
            "checked_days": self.checked_days,
            "completed_tiers": self.completed_tiers,
        }

    @classmethod
    def from_dict(cls, raw: Dict) -> "Progress":
        try:
            return cls(
                tier_key=raw.get("tier_key", "start30"),
                started=raw.get("started", date.today().isoformat()),
                checked_days=list(raw.get("checked_days", [])),
                completed_tiers=list(raw.get("completed_tiers", [])),
            )
        except (TypeError, ValueError):
            return cls()


def unlocked_tiers(progress: Progress) -> List[Tier]:
    """Tiers the user is allowed to select: everything completed, plus current, plus 75 Hard."""
    keys = [t.key for t in LADDER]
    highest = 0
    for key in progress.completed_tiers:
        if key in keys:
            highest = max(highest, keys.index(key) + 1)
    if progress.tier_key in keys:
        highest = max(highest, keys.index(progress.tier_key))
    return LADDER[: highest + 1] + [HARD75]


def calendar_grid(progress: Progress, today: Optional[date] = None) -> List[Dict]:
    """One entry per day of the challenge for rendering the grid."""
    today = today or date.today()
    start = date.fromisoformat(progress.started)
    done = set(progress.checked_days)
    grid = []
    for i in range(progress.tier.days):
        day = start + timedelta(days=i)
        if day.isoformat() in done:
            state = "done"
        elif day > today:
            state = "future"
        elif day == today:
            state = "today"
        else:
            state = "missed"
        grid.append({"n": i + 1, "date": day, "state": state})
    return grid


MOTIVATION: List[str] = [
    "The plan you follow beats the plan you optimise.",
    "Nobody has ever regretted the session they showed up for tired.",
    "Consistency isn't intensity. It's just Tuesday, again.",
    "You're not behind. You're on day {day}.",
    "The hardest rep is the one that gets you out the door.",
    "Small, boring, repeated. That's the whole secret.",
    "Progress is quiet until suddenly it isn't.",
    "Two months from now you'll wish you'd started two months ago. So: today.",
]


def line_for_today(progress: Progress) -> str:
    idx = (date.today().toordinal() + progress.days_done) % len(MOTIVATION)
    return MOTIVATION[idx].format(day=progress.days_done + 1)


def days_remaining(progress: Progress) -> int:
    return max(0, progress.tier.days - progress.days_done)


def next_tier_name(progress: Progress) -> Optional[str]:
    keys = [t.key for t in LADDER]
    if progress.tier_key not in keys:
        return None
    idx = keys.index(progress.tier_key)
    return LADDER[idx + 1].name if idx + 1 < len(LADDER) else None


def parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()
