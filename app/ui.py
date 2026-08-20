"""Visual identity.

Palette:  ink #0F1216 · panel #171C23 · chalk #ECEFEA
          ember #F2A03D (the one accent — earned progress, active muscle)
          jade #3FBFA8 (secondary — supporting muscle, rest, nutrition)
          slate #7C8899 (labels, structure)

Type: Bricolage Grotesque for display, Inter for body, JetBrains Mono for
anything countable — days, sets, streaks. Numbers are the emotional content
of a training log, so they get their own face.
"""

from __future__ import annotations

from typing import Dict, List

import streamlit as st

from .challenges import Progress, calendar_grid

INK = "#0F1216"
PANEL = "#171C23"
CHALK = "#ECEFEA"
EMBER = "#F2A03D"
JADE = "#3FBFA8"
SLATE = "#7C8899"
LINE = "#252C36"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;700&display=swap');

.stApp {{ background: {INK}; }}
html, body, [class*="css"], .stMarkdown {{
    font-family: 'Inter', system-ui, sans-serif;
    color: {CHALK};
}}
h1, h2, h3 {{
    font-family: 'Bricolage Grotesque', 'Inter', sans-serif !important;
    letter-spacing: -0.02em;
    color: {CHALK} !important;
}}
h1 {{ font-size: 2.7rem !important; line-height: 1.02; }}

.wf-eyebrow {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase;
    color: {SLATE}; margin-bottom: 0.4rem;
}}
.wf-rule {{ height: 2px; background: {EMBER}; width: 56px; margin: 0.6rem 0 1.4rem; }}

.wf-panel {{
    background: {PANEL}; border: 1px solid {LINE}; border-radius: 14px;
    padding: 1.1rem 1.25rem; margin-bottom: 0.9rem;
}}
.wf-panel h4 {{ margin: 0 0 0.35rem; font-family:'Bricolage Grotesque',sans-serif; font-size:1.05rem; }}
.wf-panel p {{ margin: 0; color: {SLATE}; font-size: 0.9rem; line-height: 1.5; }}

.wf-stat {{ display:flex; gap: 1.6rem; flex-wrap: wrap; margin: 0.4rem 0 1rem; }}
.wf-stat div span.n {{
    font-family:'JetBrains Mono', monospace; font-size: 2rem; font-weight: 700;
    color: {EMBER}; display:block; line-height: 1;
}}
.wf-stat div span.l {{
    font-family:'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 0.16em;
    text-transform: uppercase; color: {SLATE};
}}

.wf-grid {{ display:flex; flex-wrap: wrap; gap: 4px; margin: 0.8rem 0 0.4rem; }}
.wf-cell {{
    width: 15px; height: 15px; border-radius: 3px; border: 1px solid {LINE};
    background: {INK};
}}
.wf-cell.done {{ background: {EMBER}; border-color: {EMBER}; }}
.wf-cell.today {{ border: 2px solid {JADE}; background: {INK}; }}
.wf-cell.missed {{ background: #2A1B1B; border-color: #4A2A2A; }}

.wf-quote {{
    font-family:'Bricolage Grotesque', sans-serif; font-size: 1.35rem; line-height: 1.3;
    border-left: 3px solid {EMBER}; padding-left: 1rem; margin: 0.5rem 0 1.2rem;
}}
.wf-chip {{
    display:inline-block; font-family:'JetBrains Mono',monospace; font-size:0.7rem;
    letter-spacing:0.08em; padding: 3px 9px; border-radius: 999px;
    border:1px solid {LINE}; color:{SLATE}; margin: 0 5px 5px 0;
}}
.wf-chip.on {{ border-color:{EMBER}; color:{EMBER}; }}
.wf-chip.sec {{ border-color:{JADE}; color:{JADE}; }}

.wf-locked {{ opacity: 0.38; }}
.wf-note {{ font-size:0.8rem; color:{SLATE}; line-height:1.5; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{
    font-family:'JetBrains Mono',monospace; font-size:0.75rem; letter-spacing:0.1em;
    text-transform: uppercase; color:{SLATE}; padding: 10px 14px;
}}
.stTabs [aria-selected="true"] {{ color: {EMBER} !important; }}

.stButton button {{
    font-family:'JetBrains Mono',monospace; letter-spacing:0.08em; text-transform:uppercase;
    font-size:0.76rem; border-radius: 9px; border:1px solid {LINE};
}}
.stButton button[kind="primary"] {{
    background: {EMBER}; color: {INK}; border: none; font-weight:700;
}}
.stDataFrame, table {{ font-size: 0.9rem; }}
table th {{ background: {PANEL} !important; color: {SLATE} !important;
    font-family:'JetBrains Mono',monospace !important; font-size:0.7rem !important;
    letter-spacing:0.08em; text-transform:uppercase; }}
table td {{ border-color: {LINE} !important; }}

section[data-testid="stSidebar"] {{ background: {PANEL}; border-right:1px solid {LINE}; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header(eyebrow: str, title: str) -> None:
    st.markdown(
        f'<div class="wf-eyebrow">{eyebrow}</div>'
        f'<h1>{title}</h1><div class="wf-rule"></div>',
        unsafe_allow_html=True,
    )


def stats(pairs: List[tuple]) -> None:
    cells = "".join(
        f'<div><span class="n">{value}</span><span class="l">{label}</span></div>'
        for label, value in pairs
    )
    st.markdown(f'<div class="wf-stat">{cells}</div>', unsafe_allow_html=True)


def panel(title: str, body: str) -> None:
    st.markdown(
        f'<div class="wf-panel"><h4>{title}</h4><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def chips(items: List[str], primary: List[str] | None = None) -> None:
    primary = primary or []
    html = "".join(
        f'<span class="wf-chip {"on" if i in primary else "sec"}">{i}</span>' for i in items
    )
    st.markdown(html or '<span class="wf-chip">nothing tagged yet</span>', unsafe_allow_html=True)


def streak_grid(progress: Progress) -> None:
    cells = "".join(
        f'<div class="wf-cell {d["state"]}" title="Day {d["n"]} — {d["date"]}"></div>'
        for d in calendar_grid(progress)
    )
    st.markdown(f'<div class="wf-grid">{cells}</div>', unsafe_allow_html=True)


def quote(text: str) -> None:
    st.markdown(f'<div class="wf-quote">{text}</div>', unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="wf-note">{text}</div>', unsafe_allow_html=True)


MUSCLE_EMOJI: Dict[str, str] = {
    "chest": "🫁", "abs": "🎯", "quads": "🦵", "glutes": "🍑",
    "lats": "🪽", "biceps": "💪", "calves": "🦶",
}
