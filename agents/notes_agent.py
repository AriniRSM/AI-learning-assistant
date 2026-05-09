"""
Course intelligence agents — summary and notes generation from RAG content.
"""

import logging
from utils.llm import call_llm
from rag.pipeline import retrieve_notes_content
from agents.prompts import build_notes_summary_prompt, build_notes_flashcards_prompt
from tracker.storage import save_course_summary

logger = logging.getLogger(__name__)


def generate_notes_summary(notes_name: str) -> str:
    """
    Generate a structured summary of a notes from its ingested content.

    Args:
        notes_name: Must match the collection name used during process_file().

    Returns:
        Formatted notes summary as markdown.
    """
    logger.info(f"Generating summary for course: {notes_name}")

    context = retrieve_notes_content(
        query="Explain the full notes content with all important topics and concepts",
        collection_name=notes_name
    )

    if context.startswith("No content found"):
        return context  # Return the helpful error message directly

    prompt = build_notes_summary_prompt(context)
    summary = call_llm(prompt)

    # Persist summary so it doesn't need to be regenerated
    save_course_summary(notes_name, summary)
    logger.info(f"Summary saved for course: {notes_name}")

    return summary


def generate_notes_flashcards(course_name: str, topic: str | None = None) -> str:
    """
    Generate structured revision notes from a course.

    Args:
        course_name: Must match the collection name used during process_file().
        topic:       Optional specific topic to focus on. If None, covers the whole course.

    Returns:
        Structured notes as markdown.
    """
    query = (
        f"Extract all important concepts, definitions, and explanations about {topic}"
        if topic
        else "Extract all important concepts, definitions, and explanations"
    )

    logger.info(f"Generating notes for course: {course_name}, topic: {topic or 'all'}")

    context = retrieve_notes_content(query=query,collection_name=course_name)

    if context.startswith("No content found"):
        return context

    prompt = build_notes_flashcards_prompt(context)
    return call_llm(prompt)
