"""The generator functions: structured inputs in, plan text out, nothing raised."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from . import llm, prompts


def generate_workout_plan(
    goal: str,
    experience: str,
    days_per_week: int,
    session_minutes: int,
    setting: str,
    equipment: List[str],
    limitations: str = "",
    age_band: str = "Prefer not to say",
    focus_areas: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    variation_seed: int = 0,
    model: Optional[str] = None,
) -> Tuple[bool, str]:
    """Build a weekly training plan.

    Returns (True, markdown_plan) or (False, friendly_message). Never raises.
    """
    problem = prompts.validate_inputs(days_per_week, session_minutes, equipment, setting)
    if problem:
        return False, problem

    try:
        user_prompt = prompts.build_workout_prompt(
            goal=goal,
            experience=experience,
            days_per_week=days_per_week,
            session_minutes=session_minutes,
            setting=setting,
            equipment=equipment,
            limitations=limitations,
            age_band=age_band,
            focus_areas=focus_areas or [],
            variation_seed=variation_seed,
        )
    except (TypeError, ValueError):
        return False, "Something was off in the inputs. Reset the form and try again."

    ok, text = llm.ask(
        prompts.WORKOUT_SYSTEM,
        user_prompt,
        api_key=api_key,
        temperature=0.75 if variation_seed else 0.6,
        model=model,
    )
    if not ok:
        return False, text
    if "Day 1" not in text and "day 1" not in text.lower():
        return False, llm.FRIENDLY_ERRORS["parse"]
    return True, text


def generate_diet_plan(
    goal: str,
    days_per_week: int,
    diet_pattern: str,
    cuisines: List[str],
    allergies: str = "",
    dislikes: str = "",
    fasting_protocol: str = "None",
    eating_window: str = "12:00 – 20:00",
    cooking_effort: str = "Medium — 30 minutes",
    meals_per_day: int = 3,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[bool, str]:
    """Build a weekly eating guide that fits the training plan. Never raises."""
    if meals_per_day < 1:
        return False, "You need at least one meal a day for a plan to make sense."

    user_prompt = prompts.build_diet_prompt(
        goal=goal,
        days_per_week=days_per_week,
        diet_pattern=diet_pattern,
        cuisines=cuisines,
        allergies=allergies,
        dislikes=dislikes,
        fasting_protocol=fasting_protocol,
        eating_window=eating_window,
        cooking_effort=cooking_effort,
        meals_per_day=meals_per_day,
    )
    ok, text = llm.ask(
        prompts.DIET_SYSTEM, user_prompt, api_key=api_key, temperature=0.6, model=model
    )
    if not ok:
        return False, text
    return True, text


def swap_exercise(
    exercise: str,
    equipment: List[str],
    limitations: str = "",
    reason: str = "",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[bool, Any]:
    """Ask for a like-for-like replacement. Returns (True, dict) or (False, message)."""
    ok, payload = llm.ask_json(
        prompts.SWAP_SYSTEM,
        prompts.build_swap_prompt(exercise, equipment, limitations, reason),
        api_key=api_key,
        temperature=0.8,
        model=model,
    )
    if not ok:
        return False, payload
    if not isinstance(payload, dict) or "name" not in payload:
        return False, llm.FRIENDLY_ERRORS["parse"]
    return True, payload


def explain_exercise(
    exercise: str, api_key: Optional[str] = None, model: Optional[str] = None
) -> Tuple[bool, Any]:
    """Get muscles worked plus setup and cue for one exercise."""
    ok, payload = llm.ask_json(
        prompts.EXPLAIN_SYSTEM,
        f"Exercise: {exercise}",
        api_key=api_key,
        temperature=0.3,
        model=model,
    )
    if not ok:
        return False, payload
    if not isinstance(payload, dict) or "primary" not in payload:
        return False, llm.FRIENDLY_ERRORS["parse"]
    payload.setdefault("secondary", [])
    return True, payload


def plan_filename(goal: str, days: int, kind: str = "workout") -> str:
    slug = goal.lower().replace(" ", "-")
    return f"{kind}-{slug}-{days}day.md"


def as_markdown_file(plan: str, profile: Dict[str, Any], kind: str = "Workout") -> str:
    """Wrap a plan with its intake header so the download is self-explanatory."""
    lines = [f"# {kind} plan", ""]
    for key, value in profile.items():
        if value:
            pretty = key.replace("_", " ").capitalize()
            shown = ", ".join(value) if isinstance(value, list) else value
            lines.append(f"- **{pretty}:** {shown}")
    lines += ["", "---", "", plan]
    return "\n".join(lines)
