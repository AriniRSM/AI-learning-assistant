# AI Learning Assistant

An AI-powered learning companion for planning, tracking, and working with course material. It helps learners turn goals and source documents into a structured study workflow.

## What it does

- Creates personalised multi-day study plans from learning goals, availability, and preferred study windows.
- Tracks daily progress and mastered topics, then adapts subsequent plans to that progress.
- Indexes PDF, DOCX, and XLSX course material into a local vector store.
- Generates course summaries, notes, and flashcards through retrieval-augmented generation (RAG).

## Architecture

```text
Streamlit UI
├── Planner and progress tracker
├── Course tools
│   ├── document ingestion
│   ├── ChromaDB vector store
│   └── RAG-powered summaries and notes
└── Agent layer for planning and learning-content generation
```

## Stack

- Python
- Streamlit
- Google Gemini API
- LangChain
- ChromaDB
- FastAPI
- PyPDF, docx2txt, and openpyxl

## Run locally

1. Clone the repository and create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Add your Gemini API key to a `.env` file:

```env
GEMINI_API_KEY=your_key_here
```

4. Start the application:

```bash
streamlit run app.py
```

## Project structure

```text
agents/   # planning and content-generation agents
api/      # API layer
rag/      # ingestion and retrieval pipeline
tracker/  # progress persistence
utils/    # shared helpers
app.py    # Streamlit application
```

## Scope

This is a learning project exploring how LLM applications can combine planning, retrieval, and user progress into one practical workflow.
