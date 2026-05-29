import logging
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import shutil
import os
import tempfile

from agents.planner import generate_plan, adapt_plan
from agents.notes_agent import generate_notes_flashcards, generate_notes_summary
from tracker.storage import load_data, log_progress, mark_topic_complete
from rag.pipeline import process_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Learning Assistant",
    description="Personalized learning plan generator with RAG-powered course intelligence.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



class PlanRequest(BaseModel):
    goals: list[str] = Field(..., example=["Learn Flutter in 12 weeks", "Learn AI for job switch in 3 months"])
    learning_hours: float = Field(..., gt=0, le=8, example=2.0)
    working_hours: float = Field(..., gt=0, le=16, example=9.0)
    preferred_time: str | None = Field(None, example="9pm - 11pm")


class ProgressRequest(BaseModel):
    day: str = Field(..., example="Monday")
    status: str = Field(..., example="Completed")


class TopicRequest(BaseModel):
    topic: str = Field(..., example="Flutter Widgets")


class NotesRequest(BaseModel):
    notes_name: str = Field(..., example="flutter-bootcamp")
    topic: str | None = Field(None, example="State Management")



@app.get("/")
def root():
    return {"message": "AI Learning Assistant is running.", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/plan/generate")
def create_plan(req: PlanRequest):
    try:
        plan = generate_plan(
            goals=req.goals,
            learning_hours=req.learning_hours,
            working_hours=req.working_hours,
            preferred_time=req.preferred_time,
        )
        return {"plan": plan}
    except Exception as e:
        logger.error(f"Plan generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plan/adapt")
def adapt_current_plan():
    try:
        adapted = adapt_plan()
        return {"adapted_plan": adapted}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Plan adaptation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plan/current")
def get_current_plan():
    data = load_data()
    return {
        "plan": data.get("plan", ""),
        "goals": data.get("goals", []),
        "history": data.get("history", {}),
        "completed_topics": data.get("completed_topics", []),
    }


@app.post("/progress/log")
def log_daily_progress(req: ProgressRequest):
    valid_statuses = {"Completed", "Missed", "Partial"}
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{req.status}'. Must be one of: {valid_statuses}"
        )
    updated = log_progress(req.day, req.status)
    return {"message": f"{req.day} marked as {req.status}.", "history": updated["history"]}


@app.post("/progress/topic-complete")
def complete_topic(req: TopicRequest):
    mark_topic_complete(req.topic)
    return {"message": f"'{req.topic}' marked as mastered."}


@app.post("/notes/upload")
async def upload_notes(
    notes_name: str,
    file: UploadFile = File(...),
):
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Upload PDF, DOCX, or XLSX."
        )

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = process_file(tmp_path, notes_name)
        return {"message": result, "notes_name": notes_name}
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


@app.get("/notes/{notes_name}/summary")
def get_notes_summary(notes_name: str):
    data = load_data()
    if notes_name in data.get("notes", {}):
        return {"summary": data["notes"][notes_name], "cached": True}

    try:
        summary = generate_notes_summary(notes_name)
        return {"summary": summary, "cached": False}
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notes/flashcards")
def get_notes_flashcards(req: NotesRequest):
    try:
        notes = generate_notes_flashcards(req.notes_name, req.topic)
        return {"notes": notes, "notes_name": req.notes_name, "topic": req.topic}
    except Exception as e:
        logger.error(f"Notes generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
