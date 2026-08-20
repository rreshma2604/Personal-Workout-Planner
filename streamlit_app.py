"""Workout Forge — a personal training and nutrition companion.

Run with:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List

import streamlit as st
from dotenv import load_dotenv

import pandas as pd

from app import challenges, generate, llm, muscles, prompts, storage, ui
from app.challenges import HARD75, LADDER, Progress, unlocked_tiers

load_dotenv()

st.set_page_config(
    page_title="Workout Forge",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.inject()


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #

def boot() -> None:
    if "loaded" in st.session_state:
        return
    data = storage.load()
    st.session_state.profile = data.get("profile", {})
    st.session_state.workout_plan = data.get("workout_plan", "")
    st.session_state.diet_plan = data.get("diet_plan", "")
    st.session_state.progress = Progress.from_dict(data.get("progress", {}))
    st.session_state.history = data.get("history", [])
    st.session_state.regen_count = 0
    st.session_state.swap_result = None
    st.session_state.explain_result = None
    st.session_state.loaded = True


def show_error(message: str) -> None:
    """Friendly message up front, raw exception behind a disclosure."""
    st.error(message)
    detail = llm.LAST_ERROR.get("detail")
    if detail:
        with st.expander("Technical detail"):
            st.code(detail)


def persist() -> None:
    storage.save(
        {
            "profile": st.session_state.profile,
            "workout_plan": st.session_state.workout_plan,
            "diet_plan": st.session_state.diet_plan,
            "progress": st.session_state.progress.to_dict(),
            "history": st.session_state.history,
        }
    )


boot()
profile: Dict[str, Any] = st.session_state.profile
progress: Progress = st.session_state.progress


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.markdown('<div class="wf-eyebrow">Workout Forge</div>', unsafe_allow_html=True)
    st.markdown("### 🔥")

    env_key = os.getenv("GROQ_API_KEY", "")
    api_key = st.text_input(
        "Groq API key",
        value=env_key,
        type="password",
        help="Free at console.groq.com. Or put GROQ_API_KEY in a .env file and it loads itself.",
    )
    if not api_key:
        st.warning("Add a key to generate plans. Everything else still works.")

    model_label = st.selectbox("Model", list(llm.MODEL_CHOICES.keys()))
    model_id = llm.MODEL_CHOICES[model_label]

    if st.button("Test connection", use_container_width=True):
        ok, msg = llm.probe(api_key, model_id)
        (st.success if ok else st.error)(msg)

    st.divider()
    st.markdown('<div class="wf-eyebrow">Where you are</div>', unsafe_allow_html=True)
    st.markdown(f"**{progress.tier.name}**")
    st.progress(progress.percent)
    st.caption(f"Day {progress.days_done} of {progress.tier.days} · streak {progress.current_streak()}")

    st.divider()
    if st.button("Clear saved data", use_container_width=True):
        for key in ("profile", "workout_plan", "diet_plan", "history"):
            st.session_state[key] = {} if key == "profile" else ("" if "plan" in key else [])
        st.session_state.progress = Progress()
        persist()
        st.rerun()

    ui.note(
        "Coaching guidance, not medical advice. Talk to a doctor, physio or "
        "registered dietitian before starting something new — especially with "
        "an injury, a health condition, or if you're pregnant."
    )


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #

tab_today, tab_build, tab_plan, tab_food, tab_body, tab_challenge = st.tabs(
    ["Today", "Build a plan", "Your plan", "Nutrition", "Muscle map", "Challenge"]
)


# ---------------------------------- TODAY ---------------------------------- #
with tab_today:
    left, right = st.columns([3, 2], gap="large")

    with left:
        name = profile.get("name", "").strip()
        ui.header("Day " + str(progress.days_done + 1), f"Good to see you{', ' + name if name else ''}")
        ui.quote(challenges.line_for_today(progress))

        ui.stats(
            [
                ("days logged", progress.days_done),
                ("streak", progress.current_streak()),
                ("to go", challenges.days_remaining(progress)),
                ("tier", progress.tier.days),
            ]
        )
        ui.streak_grid(progress)

        done_today = progress.checked_today()
        c1, c2 = st.columns([1, 1])
        with c1:
            if not done_today:
                if st.button("✓ Log today", type="primary", use_container_width=True):
                    progress.check_in()
                    persist()
                    st.rerun()
            else:
                st.success("Logged. That's today handled.")
        with c2:
            if done_today and st.button("Undo today", use_container_width=True):
                progress.undo_today()
                persist()
                st.rerun()

        if progress.is_complete:
            st.balloons()
            nxt = challenges.next_tier_name(progress)
            st.success(f"**{progress.tier.name} complete.** {progress.tier.days} days, done.")
            if nxt and st.button(f"Unlock {nxt} →", type="primary"):
                progress.promote()
                persist()
                st.rerun()
        elif progress.at_risk():
            st.warning(
                f"{progress.missed_days()} days unlogged — past the "
                f"{progress.tier.grace_days} this tier allows. Log today and keep going; "
                "the ladder cares about the next day, not the last one."
            )

    with right:
        st.markdown('<div class="wf-eyebrow">Today\'s rules</div>', unsafe_allow_html=True)
        for rule in progress.tier.rules:
            st.checkbox(rule, key=f"rule_{progress.tier_key}_{rule[:18]}")

        if st.session_state.workout_plan:
            worked = muscles.muscles_in_plan(st.session_state.workout_plan)
            if worked:
                st.markdown('<div class="wf-eyebrow">This week hits</div>', unsafe_allow_html=True)
                top = list(worked)[:6]
                st.markdown(
                    muscles.body_svg(list(worked), primary=top, height=260),
                    unsafe_allow_html=True,
                )
        else:
            ui.panel("No plan yet", "Head to <b>Build a plan</b> and answer eight questions. Takes a minute.")


# ------------------------------- BUILD A PLAN ------------------------------ #
with tab_build:
    ui.header("Intake", "Tell me what I'd need to know")
    st.caption("Same questions a coach asks before writing anything down.")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        p_name = st.text_input("First name (optional)", value=profile.get("name", ""))
        goal = st.selectbox(
            "Primary goal",
            list(prompts.GOALS.keys()),
            index=0,
        )
        experience = st.selectbox(
            "Experience", ["Beginner", "Intermediate", "Advanced"],
            index=["Beginner", "Intermediate", "Advanced"].index(profile.get("experience", "Beginner")),
        )
        age_band = st.selectbox(
            "Age band", ["Under 25", "25–34", "35–44", "45–54", "55+", "Prefer not to say"],
            index=5,
        )

    with col_b:
        setting = st.radio(
            "Where will you train?",
            ["Home", "Gym", "Both"],
            horizontal=True,
            help="Both gives you a gym day template and a home day template you can swap between.",
        )
        days_per_week = st.slider("Training days per week", 1, 7, profile.get("days", 4))
        session_minutes = st.select_slider(
            "Minutes per session", [20, 30, 45, 60, 75, 90], value=profile.get("minutes", 45)
        )

    with col_c:
        home_kit = ["Nothing — bodyweight", "Resistance bands", "Adjustable dumbbells",
                    "Kettlebell", "Pull-up bar", "Bench", "Yoga mat"]
        gym_kit = ["Full gym", "Barbell + rack", "Dumbbell rack", "Cable machine",
                   "Machines", "Cardio machines"]
        options = home_kit if setting == "Home" else gym_kit if setting == "Gym" else home_kit + gym_kit
        equipment = st.multiselect(
            "What you actually have access to", options,
            default=[o for o in profile.get("equipment", []) if o in options],
        )
        focus_areas = st.multiselect(
            "Anything you want prioritised",
            ["Glutes", "Legs", "Back", "Chest", "Shoulders", "Arms", "Core", "Conditioning"],
            default=profile.get("focus", []),
        )

    limitations = st.text_area(
        "Injuries, pain, or movements to avoid",
        value=profile.get("limitations", ""),
        placeholder="e.g. bad knees — no deep squats · no overhead pressing · sore lower back",
        help="Anything you write here removes that movement pattern from the plan and swaps in an alternative.",
    )

    st.markdown("")
    gen_col, opt_col = st.columns([1, 2])
    with gen_col:
        go = st.button("Generate my plan", type="primary", use_container_width=True)
    with opt_col:
        also_diet = st.checkbox("Also generate a matching eating plan", value=True)

    if go:
        profile.update(
            {
                "name": p_name, "goal": goal, "experience": experience, "age_band": age_band,
                "setting": setting, "days": days_per_week, "minutes": session_minutes,
                "equipment": equipment, "focus": focus_areas, "limitations": limitations,
            }
        )
        with st.spinner("Writing your week…"):
            ok, result = generate.generate_workout_plan(
                goal=goal, experience=experience, days_per_week=days_per_week,
                session_minutes=session_minutes, setting=setting, equipment=equipment,
                limitations=limitations, age_band=age_band, focus_areas=focus_areas,
                api_key=api_key, model=model_id,
            )
        if ok:
            storage.archive_plan(
                {"history": st.session_state.history}, st.session_state.workout_plan, "previous"
            )
            st.session_state.workout_plan = result
            st.session_state.regen_count = 0
            persist()
            st.success("Plan ready — open the **Your plan** tab.")
        else:
            show_error(result)

        if ok and also_diet:
            with st.spinner("And the food…"):
                d_ok, d_res = generate.generate_diet_plan(
                    goal=goal, days_per_week=days_per_week,
                    diet_pattern=profile.get("diet_pattern", "No restrictions"),
                    cuisines=profile.get("cuisines", []),
                    allergies=profile.get("allergies", ""),
                    dislikes=profile.get("dislikes", ""),
                    fasting_protocol=profile.get("fasting", "None"),
                    eating_window=profile.get("window", "12:00 – 20:00"),
                    cooking_effort=profile.get("effort", "Medium — 30 minutes"),
                    meals_per_day=profile.get("meals", 3),
                    api_key=api_key, model=model_id,
                )
            if d_ok:
                st.session_state.diet_plan = d_res
                persist()
            else:
                st.warning(f"Training plan saved. Nutrition didn't come through: {d_res}")


# -------------------------------- YOUR PLAN -------------------------------- #
with tab_plan:
    plan = st.session_state.workout_plan
    if not plan:
        ui.header("Empty", "Nothing forged yet")
        ui.panel("Start here", "Fill in the intake on the <b>Build a plan</b> tab.")
    else:
        ui.header(profile.get("goal", "Training"), "Your week")

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("↻ Regenerate a different version", use_container_width=True):
                st.session_state.regen_count += 1
                with st.spinner("Writing a different take…"):
                    ok, result = generate.generate_workout_plan(
                        goal=profile.get("goal", "General fitness"),
                        experience=profile.get("experience", "Beginner"),
                        days_per_week=profile.get("days", 3),
                        session_minutes=profile.get("minutes", 45),
                        setting=profile.get("setting", "Home"),
                        equipment=profile.get("equipment", []),
                        limitations=profile.get("limitations", ""),
                        age_band=profile.get("age_band", "Prefer not to say"),
                        focus_areas=profile.get("focus", []),
                        api_key=api_key, model=model_id,
                        variation_seed=st.session_state.regen_count,
                    )
                if ok:
                    storage.archive_plan({"history": st.session_state.history}, plan, "regenerated")
                    st.session_state.workout_plan = result
                    persist()
                    st.rerun()
                else:
                    show_error(result)
        with b2:
            st.download_button(
                "⬇ Download as .md",
                data=generate.as_markdown_file(plan, profile, "Workout"),
                file_name=generate.plan_filename(profile.get("goal", "plan"), profile.get("days", 3)),
                mime="text/markdown",
                use_container_width=True,
            )
        with b3:
            st.download_button(
                "⬇ Download as .txt",
                data=generate.as_markdown_file(plan, profile, "Workout"),
                file_name=generate.plan_filename(profile.get("goal", "plan"), profile.get("days", 3)).replace(".md", ".txt"),
                mime="text/plain",
                use_container_width=True,
            )

        st.markdown(plan)

        st.divider()
        st.markdown('<div class="wf-eyebrow">Swap an exercise</div>', unsafe_allow_html=True)
        names: List[str] = muscles.exercise_names(plan)
        if names:
            s1, s2, s3 = st.columns([2, 2, 1])
            with s1:
                target = st.selectbox("Which one isn't working?", names)
            with s2:
                reason = st.text_input("Why?", placeholder="hurts my shoulder / gym's too busy / bored of it")
            with s3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Swap it", use_container_width=True):
                    with st.spinner("Finding a fair replacement…"):
                        ok, res = generate.swap_exercise(
                            target, profile.get("equipment", []),
                            profile.get("limitations", ""), reason,
                            api_key=api_key, model=model_id,
                        )
                    st.session_state.swap_result = res if ok else None
                    if not ok:
                        show_error(res)

            swap = st.session_state.swap_result
            if swap:
                sc1, sc2 = st.columns([2, 1])
                with sc1:
                    st.markdown(f"### {swap['name']}")
                    st.markdown(
                        f"**{swap.get('sets_reps','')}** · rest {swap.get('rest','')}  \n"
                        f"{swap.get('cue','')}  \n\n_{swap.get('why','')}_"
                    )
                    ui.chips(swap.get("muscles", []), primary=swap.get("muscles", [])[:2])
                with sc2:
                    st.markdown(
                        muscles.body_svg(swap.get("muscles", []),
                                         primary=swap.get("muscles", [])[:2], height=220),
                        unsafe_allow_html=True,
                    )

        if st.session_state.history:
            with st.expander("Previous plans"):
                for i, item in enumerate(st.session_state.history):
                    st.markdown(f"**{i+1}. {item['label']}**")
                    st.markdown(item["plan"][:1200] + "…")
                    st.divider()


# -------------------------------- NUTRITION -------------------------------- #
with tab_food:
    ui.header("Fuel", "Eating that fits the training")

    f1, f2, f3 = st.columns(3)
    with f1:
        diet_pattern = st.selectbox(
            "Eating pattern",
            ["No restrictions", "Vegetarian", "Vegan", "Pescatarian", "Halal", "Kosher",
             "Gluten-free", "Dairy-free", "Low carb", "High protein"],
        )
        meals = st.slider("Meals per day", 1, 6, 3)
    with f2:
        cuisines = st.multiselect(
            "Cuisines you actually enjoy",
            ["Indian", "British", "Mediterranean", "Italian", "Middle Eastern", "Chinese",
             "Japanese", "Thai", "Mexican", "West African", "Caribbean"],
            default=profile.get("cuisines", []),
        )
        effort = st.select_slider(
            "Cooking effort you'll sustain",
            ["Minimal — 10 minutes", "Medium — 30 minutes", "Happy to cook — 45+"],
            value="Medium — 30 minutes",
        )
    with f3:
        fasting = st.selectbox(
            "Intermittent fasting",
            ["None", "12:12", "14:10", "16:8", "18:6", "One meal a day (OMAD)"],
            help="Fasting is one option among many, not a requirement. Skip it if it doesn't suit you.",
        )
        windows = {
            "None": "no window — eat normally",
            "12:12": "08:00 – 20:00", "14:10": "10:00 – 20:00",
            "16:8": "12:00 – 20:00", "18:6": "13:00 – 19:00",
            "One meal a day (OMAD)": "18:00 – 19:00",
        }
        window = st.text_input("Eating window", value=windows[fasting])

    allergies = st.text_input("Allergies — these never appear in the plan",
                              value=profile.get("allergies", ""), placeholder="peanuts, shellfish")
    dislikes = st.text_input("Foods you won't eat", value=profile.get("dislikes", ""),
                             placeholder="mushrooms, olives")

    if fasting in ("18:6", "One meal a day (OMAD)"):
        st.info(
            "Longer fasts suit some people and not others. If you're training hard, "
            "under 18, pregnant, or managing any health condition, check with a GP or "
            "registered dietitian first — and if it leaves you dizzy or drained, widen the window."
        )

    if st.button("Generate eating plan", type="primary"):
        profile.update({"diet_pattern": diet_pattern, "cuisines": cuisines, "allergies": allergies,
                        "dislikes": dislikes, "fasting": fasting, "window": window,
                        "effort": effort, "meals": meals})
        with st.spinner("Building the week…"):
            ok, res = generate.generate_diet_plan(
                goal=profile.get("goal", "General fitness"),
                days_per_week=profile.get("days", 3),
                diet_pattern=diet_pattern, cuisines=cuisines, allergies=allergies,
                dislikes=dislikes, fasting_protocol=fasting, eating_window=window,
                cooking_effort=effort, meals_per_day=meals,
                api_key=api_key, model=model_id,
            )
        if ok:
            st.session_state.diet_plan = res
            persist()
        else:
            show_error(res)

    if st.session_state.diet_plan:
        st.download_button(
            "⬇ Download eating plan",
            data=generate.as_markdown_file(st.session_state.diet_plan, profile, "Eating"),
            file_name="eating-plan.md",
            mime="text/markdown",
        )
        st.markdown(st.session_state.diet_plan)
        ui.note(
            "General nutrition guidance only. It isn't tailored to any medical condition, "
            "medication or allergy testing — see a registered dietitian or your GP for that."
        )


# ------------------------------- MUSCLE MAP -------------------------------- #
with tab_body:
    ui.header("Anatomy", "What each movement actually trains")

    m1, m2 = st.columns([2, 3], gap="large")
    with m1:
        plan_names = muscles.exercise_names(st.session_state.workout_plan) if st.session_state.workout_plan else []
        source = st.radio("Look up", ["From my plan", "Any exercise"], horizontal=True)
        if source == "From my plan" and plan_names:
            chosen = st.selectbox("Exercise", plan_names)
        else:
            chosen = st.text_input("Exercise name", value="Romanian deadlift")

        local = muscles.muscles_for(chosen)
        if local:
            st.markdown("**Primary**")
            ui.chips(local[:2], primary=local[:2])
            if local[2:]:
                st.markdown("**Also working**")
                ui.chips(local[2:])
        else:
            st.caption("Not in the offline map — ask the model below.")

        if st.button("Explain this exercise"):
            with st.spinner("Looking it up…"):
                ok, res = generate.explain_exercise(chosen, api_key=api_key, model=model_id)
            st.session_state.explain_result = res if ok else None
            if not ok:
                show_error(res)

        detail = st.session_state.explain_result
        if detail:
            st.markdown(f"**Setup.** {detail.get('setup','')}")
            st.markdown(f"**Cue.** {detail.get('cue','')}")
            st.markdown(f"**Common mistake.** {detail.get('mistake','')}")

    with m2:
        detail = st.session_state.explain_result
        primary = (detail or {}).get("primary") if detail else local[:2]
        secondary = (detail or {}).get("secondary") if detail else local[2:]
        active = list(dict.fromkeys((primary or []) + (secondary or []))) or local
        st.markdown(
            muscles.body_svg(active, primary=primary or local[:2], height=380),
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<span class="wf-chip on">■ primary</span>'
            f'<span class="wf-chip sec">■ supporting</span>',
            unsafe_allow_html=True,
        )

    if st.session_state.workout_plan:
        st.divider()
        st.markdown('<div class="wf-eyebrow">Weekly coverage — where your volume goes</div>',
                    unsafe_allow_html=True)
        counts = muscles.muscles_in_plan(st.session_state.workout_plan)
        if counts:
            chart_df = pd.DataFrame(
                {"sets logged": list(counts.values())}, index=list(counts.keys())
            )
            st.bar_chart(chart_df, color=ui.EMBER, height=240)
            thin = [m for m in ["chest", "lats", "quads", "hamstrings", "glutes", "abs", "side delts"]
                    if counts.get(m, 0) == 0]
            if thin:
                st.caption("Getting little or nothing this week: " + ", ".join(thin))


# -------------------------------- CHALLENGE -------------------------------- #
with tab_challenge:
    ui.header("The ladder", "Earn the next rung")
    st.caption("Start at 30 days. Finish it and 60 unlocks. Nothing opens early.")

    unlocked = {t.key for t in unlocked_tiers(progress)}
    cols = st.columns(len(LADDER))
    for col, tier in zip(cols, LADDER):
        with col:
            state = ("✓ done" if tier.key in progress.completed_tiers
                     else "current" if tier.key == progress.tier_key
                     else "locked" if tier.key not in unlocked else "open")
            klass = "wf-panel" + (" wf-locked" if state == "locked" else "")
            st.markdown(
                f'<div class="{klass}"><h4>{tier.days}</h4>'
                f'<p><b>{tier.name.split("—")[0].strip()}</b><br>{state}</p></div>',
                unsafe_allow_html=True,
            )

    st.markdown("")
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown(f"### {progress.tier.name}")
        st.markdown(f"_{progress.tier.tagline}_")
        for rule in progress.tier.rules:
            st.markdown(f"- {rule}")
        st.caption(
            f"Grace days this tier: {progress.tier.grace_days}. "
            "Life happens — grace days exist so one bad week doesn't cost you the streak."
        )
        ui.streak_grid(progress)

    with right:
        st.markdown('<div class="wf-eyebrow">Switch challenge</div>', unsafe_allow_html=True)
        choices = [t.name for t in unlocked_tiers(progress)]
        pick = st.selectbox("Available to you", choices,
                            index=choices.index(progress.tier.name) if progress.tier.name in choices else 0)
        if pick != progress.tier.name:
            st.warning("Switching restarts the day count for that challenge.")
            if st.button("Switch and start at day 1", use_container_width=True):
                key = next(t.key for t in unlocked_tiers(progress) if t.name == pick)
                progress.restart(key)
                persist()
                st.rerun()

        st.markdown("")
        with st.expander("What's 75 Hard?"):
            st.markdown(f"_{HARD75.tagline}_")
            for rule in HARD75.rules:
                st.markdown(f"- {rule}")
            ui.note(
                "It's a mental-toughness programme, not a training programme, and it's "
                "intentionally unforgiving. It isn't right for everyone — the 30/60/90 "
                "ladder gets most people further, because it's built to be survivable."
            )

    st.divider()
    ui.note(
        "Workout Forge gives general fitness coaching, not medical advice. "
        "Stop if something hurts, and get an injury, health condition or medication "
        "checked by a qualified professional before training around it."
    )
