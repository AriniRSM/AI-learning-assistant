"""
Planner agent — generates and adapts the weekly learning plan.
"""

import logging
from utils.llm import call_llm
from agents.prompts import build_planner_prompt, build_adaptation_prompt
from tracker.storage import load_data, save_data

logger = logging.getLogger(__name__)


def generate_plan(
    goals: list[str],
    learning_hours: float,
    working_hours: float,
    preferred_time: str | None = None,
) -> str:
    """
    Generate a fresh 7-day learning plan and persist it.

    Args:
        goals:          List of learning goals.
        learning_hours: Daily hours available for learning.
        working_hours:  Daily hours spent on corporate work.
        preferred_time: Optional preferred learning time window (e.g. "9pm-11pm").

    Returns:
        The generated plan as a markdown string.
    """
    logger.info(f"Generating plan for goals: {goals}")

    prompt = build_planner_prompt(goals, learning_hours, working_hours, preferred_time)
    plan = call_llm(prompt)

    data = load_data()
    data["plan"] = plan
    data["goals"] = goals
    data["history"] = {}           # Reset history for new plan
    data["completed_topics"] = []  # Reset mastery for new plan
    save_data(data)

    logger.info("Plan generated and saved.")
    return plan


def adapt_plan() -> str:
    """
    Adapt the current plan based on tracked progress.
    Reads goals, history, and mastered topics from storage automatically.

    Returns:
        The adapted plan as a markdown string.
    """
    data = load_data()

    current_plan = data.get("plan", "")
    goals = data.get("goals", [])
    progress_logs = data.get("history", {})
    mastered = data.get("completed_topics", [])

    if not current_plan:
        raise ValueError("No existing plan found. Generate a plan first.")

    if not goals:
        raise ValueError("No goals found in storage. Generate a plan first.")

    logger.info(f"Adapting plan. Consistency: {sum(1 for s in progress_logs.values() if s == 'Completed')}/7 days.")

    prompt = build_adaptation_prompt(current_plan, progress_logs, goals, mastered)
    adapted_plan = call_llm(prompt)

    # Save adapted plan as the new current plan
    data["plan"] = adapted_plan
    data["history"] = {}  # Reset history for the new week
    save_data(data)

    logger.info("Adapted plan saved.")
    return adapted_plan
