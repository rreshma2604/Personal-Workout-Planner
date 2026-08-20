# Workout Forge

A Streamlit app that writes you a training week, a matching eating plan, and holds you to a challenge ladder that starts at 30 days and only unlocks 60 when you finish it.

Built for the Codebasics AI Engineering Cohort assignment, then extended into something worth actually opening on a Monday morning.

---

## Run it

```bash
git clone https://github.com/rreshma2604/Personal-Workout-Planner.git
cd Personal-Workout-Planner
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then paste your Groq key in
streamlit run streamlit_app.py
```

A free Groq key takes about a minute: <https://console.groq.com/keys>. You can also paste it straight into the sidebar without a `.env` file.

---

## What's in it

**Today** — day counter, streak, check-in grid, and the muscles this week's plan is hitting.

**Build a plan** — the intake. Goal, experience, days, session length, home / gym / both, actual equipment, priority areas, and a limitations box. Anything you type into limitations removes that movement pattern and swaps in an alternative that trains the same muscle.

**Your plan** — the week, day by day, with sets, reps, rest, target muscles and a coaching cue per exercise. Regenerate for a different take, download as `.md` or `.txt`, or swap any single exercise for a like-for-like replacement.

**Nutrition** — eating pattern, cuisines, allergies (hard exclusions), cooking effort, and an optional intermittent fasting window from 12:12 through OMAD. Returns a training-day and rest-day template, swap list and shopping list.

**Muscle map** — pick any exercise and see the muscles light up on a front/back figure. Primary in amber, supporting in teal. Also charts where your weekly volume actually goes, and flags muscle groups getting nothing.

**Challenge** — the ladder: 30 → 60 → 90 → 120 → 365, each with its own rules and its own allowance of grace days. Tiers stay locked until the one below is finished. 75 Hard sits alongside as an optional track.

---

## How it's organised

```
streamlit_app.py     UI and page flow
app/prompts.py       system prompts + prompt builders   ← the interesting part
app/generate.py      typed generator functions
app/llm.py           Groq client, error classification
app/muscles.py       exercise→muscle map, SVG anatomy figure
app/challenges.py    ladder, streaks, promotion logic
app/storage.py       local JSON save file
app/ui.py            theme
```

Every function that touches the network returns `(ok, payload)` and never raises. The UI has no `except` blocks because it doesn't need any.

---

## On the prompt design

The first version concatenated inputs into a sentence and the model cheerfully prescribed cable flyes to someone with a pair of dumbbells and a floor. Four things fixed it:

1. **Constraints framed as failure conditions**, not preferences — "breaking any one of these makes the plan useless" outperformed "please respect".
2. **A `Constraints I built around` section in the required output.** Making the model restate the equipment and limitations before writing exercises is what stopped it drifting by Day 3. Cheap self-check, big effect.
3. **An escape hatch.** "If the goal cannot be fully served within these constraints, say so in one honest sentence." Without it, the model quietly invented equipment rather than admit a 20-minute bodyweight session won't do everything.
4. **A closed vocabulary for muscle names**, so the parser in `muscles.py` can reliably light up the diagram instead of guessing at whatever the model felt like calling the posterior chain.

Same pattern on the nutrition side: allergies are checked per meal, portions are described in hand sizes, calories are given as a starting band rather than a prescription, and the prompt bans detox and fat-burning-food language outright.

---

## Error handling

| Case | Behaviour |
|---|---|
| 0 days, 0 equipment, sub-15-minute sessions | Caught before the API call, with a specific message |
| Bad or missing API key | "Your Groq API key isn't working. Check GROQ_API_KEY in your .env file." |
| Rate limit | Named as a free-tier limit with a wait suggestion |
| Network failure | Named as a connection problem |
| Empty or truncated response | Detected by length and by absence of `Day 1`, offers a retry |
| Malformed JSON on swap/explain | Regex-extracted, then a friendly retry message |
| Corrupt save file | Falls back to defaults rather than crashing on boot |

---

## Not medical advice

This is general fitness and nutrition coaching. It doesn't know your medical history, and it isn't a substitute for a doctor, physiotherapist or registered dietitian — see one before training around an injury or making a significant dietary change, and stop if something hurts.
