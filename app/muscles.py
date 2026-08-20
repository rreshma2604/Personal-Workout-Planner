"""Muscle mapping and the SVG anatomy figure.

The figure is drawn inline rather than loaded as an image so it recolours
instantly and works offline with no asset licensing to worry about.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

MUSCLES: List[str] = [
    "chest", "front delts", "side delts", "rear delts", "biceps", "triceps",
    "forearms", "lats", "traps", "upper back", "lower back", "abs", "obliques",
    "glutes", "quads", "hamstrings", "calves", "hip flexors", "adductors",
]

# Keyword -> muscles. Checked longest-first so "romanian deadlift" beats "deadlift".
LOOKUP: Dict[str, List[str]] = {
    "romanian deadlift": ["hamstrings", "glutes", "lower back"],
    "stiff leg deadlift": ["hamstrings", "glutes", "lower back"],
    "sumo deadlift": ["glutes", "quads", "adductors", "lower back"],
    "deadlift": ["hamstrings", "glutes", "lower back", "traps", "forearms"],
    "back squat": ["quads", "glutes", "adductors", "lower back"],
    "front squat": ["quads", "glutes", "abs"],
    "goblet squat": ["quads", "glutes", "abs"],
    "split squat": ["quads", "glutes", "adductors"],
    "bulgarian": ["quads", "glutes", "adductors"],
    "squat": ["quads", "glutes", "adductors"],
    "lunge": ["quads", "glutes", "hamstrings"],
    "step up": ["quads", "glutes"],
    "leg press": ["quads", "glutes"],
    "leg extension": ["quads"],
    "leg curl": ["hamstrings"],
    "hip thrust": ["glutes", "hamstrings"],
    "glute bridge": ["glutes", "hamstrings"],
    "good morning": ["hamstrings", "lower back", "glutes"],
    "hyperextension": ["lower back", "glutes"],
    "calf raise": ["calves"],
    "incline press": ["chest", "front delts", "triceps"],
    "bench press": ["chest", "front delts", "triceps"],
    "chest press": ["chest", "front delts", "triceps"],
    "push up": ["chest", "front delts", "triceps", "abs"],
    "push-up": ["chest", "front delts", "triceps", "abs"],
    "pushup": ["chest", "front delts", "triceps", "abs"],
    "dip": ["chest", "triceps", "front delts"],
    "fly": ["chest"],
    "pec deck": ["chest"],
    "overhead press": ["front delts", "side delts", "triceps", "abs"],
    "shoulder press": ["front delts", "side delts", "triceps"],
    "arnold press": ["front delts", "side delts", "triceps"],
    "lateral raise": ["side delts"],
    "side raise": ["side delts"],
    "front raise": ["front delts"],
    "rear delt": ["rear delts", "upper back"],
    "reverse fly": ["rear delts", "upper back"],
    "face pull": ["rear delts", "upper back", "traps"],
    "upright row": ["side delts", "traps"],
    "shrug": ["traps"],
    "pull up": ["lats", "biceps", "upper back"],
    "pull-up": ["lats", "biceps", "upper back"],
    "chin up": ["lats", "biceps"],
    "lat pulldown": ["lats", "biceps", "upper back"],
    "pulldown": ["lats", "biceps"],
    "pullover": ["lats", "chest"],
    "bent over row": ["lats", "upper back", "biceps", "lower back"],
    "barbell row": ["lats", "upper back", "biceps"],
    "dumbbell row": ["lats", "upper back", "biceps"],
    "cable row": ["lats", "upper back", "biceps"],
    "seated row": ["lats", "upper back", "biceps"],
    "inverted row": ["upper back", "lats", "biceps"],
    "row": ["lats", "upper back", "biceps"],
    "curl": ["biceps", "forearms"],
    "hammer": ["biceps", "forearms"],
    "triceps": ["triceps"],
    "tricep": ["triceps"],
    "skull crusher": ["triceps"],
    "pushdown": ["triceps"],
    "kickback": ["triceps"],
    "close grip": ["triceps", "chest"],
    "farmer": ["forearms", "traps", "abs"],
    "plank": ["abs", "obliques"],
    "dead bug": ["abs"],
    "hollow": ["abs", "hip flexors"],
    "crunch": ["abs"],
    "sit up": ["abs", "hip flexors"],
    "leg raise": ["abs", "hip flexors"],
    "knee raise": ["abs", "hip flexors"],
    "russian twist": ["obliques", "abs"],
    "side plank": ["obliques"],
    "wood chop": ["obliques", "abs"],
    "pallof": ["abs", "obliques"],
    "mountain climber": ["abs", "hip flexors", "front delts"],
    "burpee": ["quads", "chest", "abs"],
    "kettlebell swing": ["glutes", "hamstrings", "lower back"],
    "thruster": ["quads", "front delts", "glutes"],
    "clean": ["glutes", "hamstrings", "traps", "quads"],
    "snatch": ["glutes", "traps", "side delts"],
    "carry": ["forearms", "abs", "traps"],
    "jump rope": ["calves", "quads"],
    "sprint": ["hamstrings", "glutes", "quads", "calves"],
    "run": ["quads", "hamstrings", "calves", "glutes"],
    "cycle": ["quads", "glutes", "calves"],
    "row machine": ["lats", "quads", "upper back"],
    "hip abduction": ["glutes"],
    "adduction": ["adductors"],
    "copenhagen": ["adductors", "obliques"],
    "nordic": ["hamstrings"],
}

_SORTED_KEYS = sorted(LOOKUP, key=len, reverse=True)


def muscles_for(exercise: str) -> List[str]:
    """Best-effort muscle list for a free-text exercise name."""
    name = exercise.lower()
    for key in _SORTED_KEYS:
        if key in name:
            return LOOKUP[key]
    return []


def parse_muscle_text(text: str) -> List[str]:
    """Pull known muscle names out of a table cell the model wrote."""
    low = text.lower()
    found = [m for m in MUSCLES if m in low]
    if "delt" in low and not any("delts" in f for f in found):
        found.append("front delts")
    if "quad" in low and "quads" not in found:
        found.append("quads")
    if "ham" in low and "hamstrings" not in found:
        found.append("hamstrings")
    if "glute" in low and "glutes" not in found:
        found.append("glutes")
    if "core" in low and "abs" not in found:
        found.append("abs")
    return found


def muscles_in_plan(markdown: str) -> Dict[str, int]:
    """Count how often each muscle appears across a generated plan."""
    counts: Dict[str, int] = {}
    for line in markdown.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        hits: Set[str] = set(parse_muscle_text(" ".join(cells[1:])))
        hits.update(muscles_for(cells[0]))
        for muscle in hits:
            counts[muscle] = counts.get(muscle, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


# --------------------------------------------------------------------------- #
# SVG figure
# --------------------------------------------------------------------------- #

# region id -> (view, svg shapes)
_REGIONS: Dict[str, str] = {
    # ---- FRONT (x offset 0) ----
    "chest": '<path d="M62 96 q18 -10 36 0 l-2 26 q-16 9 -32 0 z"/>',
    "front delts": '<ellipse cx="52" cy="96" rx="12" ry="13"/><ellipse cx="108" cy="96" rx="12" ry="13"/>',
    "side delts": '<ellipse cx="45" cy="100" rx="8" ry="12"/><ellipse cx="115" cy="100" rx="8" ry="12"/>',
    "biceps": '<ellipse cx="44" cy="126" rx="9" ry="18"/><ellipse cx="116" cy="126" rx="9" ry="18"/>',
    "forearms": '<ellipse cx="38" cy="164" rx="8" ry="20"/><ellipse cx="122" cy="164" rx="8" ry="20"/>',
    "abs": '<rect x="68" y="126" width="24" height="46" rx="7"/>',
    "obliques": '<path d="M62 128 l4 44 -10 -6 z"/><path d="M98 128 l-4 44 10 -6 z"/>',
    "hip flexors": '<ellipse cx="70" cy="186" rx="9" ry="10"/><ellipse cx="90" cy="186" rx="9" ry="10"/>',
    "quads": '<ellipse cx="68" cy="228" rx="15" ry="34"/><ellipse cx="92" cy="228" rx="15" ry="34"/>',
    "adductors": '<ellipse cx="76" cy="215" rx="6" ry="26"/><ellipse cx="84" cy="215" rx="6" ry="26"/>',
    # ---- BACK (x offset 170) ----
    "traps": '<path d="M226 74 l32 0 l14 26 -60 0 z"/>',
    "upper back": '<rect x="222" y="102" width="40" height="26" rx="6"/>',
    "rear delts": '<ellipse cx="215" cy="98" rx="11" ry="13"/><ellipse cx="269" cy="98" rx="11" ry="13"/>',
    "lats": '<path d="M220 106 l-12 46 16 10 8 -52 z"/><path d="M264 106 l12 46 -16 10 -8 -52 z"/>',
    "triceps": '<ellipse cx="206" cy="128" rx="9" ry="19"/><ellipse cx="278" cy="128" rx="9" ry="19"/>',
    "lower back": '<rect x="230" y="132" width="24" height="34" rx="7"/>',
    "glutes": '<ellipse cx="232" cy="186" rx="16" ry="15"/><ellipse cx="252" cy="186" rx="16" ry="15"/>',
    "hamstrings": '<ellipse cx="231" cy="232" rx="14" ry="32"/><ellipse cx="253" cy="232" rx="14" ry="32"/>',
    "calves": '<ellipse cx="231" cy="296" rx="11" ry="24"/><ellipse cx="253" cy="296" rx="11" ry="24"/>',
}

_SILHOUETTE = """
<g fill="none" stroke="{outline}" stroke-width="2" stroke-linejoin="round">
  <circle cx="80" cy="52" r="20"/>
  <path d="M80 72 q-32 6 -38 30 l-8 74 12 4 10 -46 -4 60 8 96 14 0 6 -76 6 76 14 0 8 -96 -4 -60 10 46 12 -4 -8 -74 q-6 -24 -38 -30z"/>
  <circle cx="250" cy="52" r="20"/>
  <path d="M250 72 q-32 6 -38 30 l-8 74 12 4 10 -46 -4 60 8 96 14 0 6 -76 6 76 14 0 8 -96 -4 -60 10 46 12 -4 -8 -74 q-6 -24 -38 -30z"/>
</g>
<text x="80" y="345" text-anchor="middle" fill="{label}" font-size="11" letter-spacing="2">FRONT</text>
<text x="250" y="345" text-anchor="middle" fill="{label}" font-size="11" letter-spacing="2">BACK</text>
"""


def body_svg(
    active: List[str],
    primary: List[str] | None = None,
    outline: str = "#4A5568",
    label: str = "#8C97A5",
    hot: str = "#F2A03D",
    warm: str = "#3FBFA8",
    height: int = 320,
) -> str:
    """Render the two-view anatomy figure with the given muscles highlighted.

    `primary` muscles glow in the accent colour, everything else in `active`
    gets the secondary colour.
    """
    primary_set = {m.lower() for m in (primary or active)}
    active_set = {m.lower() for m in active}

    shapes = []
    for muscle, path in _REGIONS.items():
        if muscle not in active_set:
            continue
        colour = hot if muscle in primary_set else warm
        opacity = 0.92 if muscle in primary_set else 0.55
        shapes.append(f'<g fill="{colour}" opacity="{opacity}">{path}</g>')

    return (
        f'<svg viewBox="0 0 330 360" height="{height}" width="100%" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Body diagram highlighting {", ".join(sorted(active_set)) or "no muscles"}">'
        + "".join(shapes)
        + _SILHOUETTE.format(outline=outline, label=label)
        + "</svg>"
    )


def exercise_names(markdown: str) -> List[str]:
    """Pull exercise names out of the markdown tables in a plan."""
    names: List[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        first = stripped.strip("|").split("|")[0].strip()
        first = re.sub(r"\*\*|\*", "", first).strip()
        if not first or set(first) <= set("-: ") or first.lower() in {"exercise", "meal"}:
            continue
        if first not in names:
            names.append(first)
    return names
