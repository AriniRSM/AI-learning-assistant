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
    logger.info(f"Generating plan for goals: {goals}")

    prompt = build_planner_prompt(goals, learning_hours, working_hours, preferred_time)
    plan = call_llm(prompt)

    data = load_data()
    data["plan"] = plan
    data["goals"] = goals
    data["history"] = {}
    data["completed_topics"] = []
    save_data(data)

    logger.info("Plan generated and saved.")
    return plan


def adapt_plan() -> str:
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

    data["plan"] = adapted_plan
    data["history"] = {}
    save_data(data)

    logger.info("Adapted plan saved.")
    return adapted_plan
