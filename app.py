
import streamlit as st
import datetime
import re
import os
import tempfile

from agents.planner import generate_plan, adapt_plan
from agents.notes_agent import generate_notes_flashcards, generate_notes_summary
from tracker.storage import load_data, log_progress, mark_topic_complete
from rag.pipeline import process_file, list_collections

st.set_page_config(
    page_title="AI Learning Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 { font-family: 'DM Serif Display', serif; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f1117;
    border-right: 1px solid #1e2130;
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px;
    border-radius: 8px;
    display: block;
    margin: 2px 0;
    transition: background .15s;
}
section[data-testid="stSidebar"] .stRadio label:hover { background: #1e2130; }

/* Main background */
.main { 
background: #f8f9fc !important;
    color: #1a1f36 !important;
     }

/* Metric cards */
.metric-card {
    background: white;
    border: 1px solid #e8ecf2;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    text-align: center;
}
.metric-card .value {
    font-size: 2rem;
    font-weight: 600;
    color: #1a1f36;
    font-family: 'DM Serif Display', serif;
    color: #1a1f36 !important;
}
.metric-card .label {
    font-size: 0.78rem;
    color: #6b7280 !important;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-top: 4px;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 500;
}
.badge-completed { background: #dcfce7; color: #166534; }
.badge-missed    { background: #fee2e2; color: #991b1b; }
.badge-partial   { background: #fef3c7; color: #92400e; }
.badge-pending   { background: #f1f5f9; color: #64748b; }

/* Section headers */
.section-header {
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: #ffffff !important;
    margin: 0 0 1rem;
    padding-bottom: 8px;
    border-bottom: 2px solid #e8ecf2;
}

/* Info box */
.info-box {
    background: #eff6ff !important;
    border: 1px solid #bfdbfe !important;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-size: 0.875rem;
    color: #1e40af !important;
}

/* Plan display */
.plan-box {
    background: white;
    border: 1px solid #e8ecf2;
    border-radius: 12px;
    padding: 1.5rem;
    max-height: 480px;
    overflow-y: auto;
    font-size: 0.9rem;
    line-height: 1.7;
    color: #1a1f36 !important;
}

/* Buttons */
.stButton > button {
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    transition: all .15s !important;
}

.stMarkdown div[style] span {
    color: #374151 !important;
}

.stTabs [data-baseweb="tab"] {
    color: #ffffff !important;
}

/* Divider */
hr { border-color: #e8ecf2 !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize_collection_name(name: str) -> str:
    """
    ChromaDB collection name rules:
    - 3-512 chars, alphanumeric + underscores/hyphens/dots, no spaces.
    """
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", name.strip())
    return f"course_{clean}" if len(clean) < 3 else clean


def status_badge(status: str) -> str:
    cls = {
        "Completed": "badge-completed",
        "Missed":    "badge-missed",
        "Partial":   "badge-partial",
    }.get(status, "badge-pending")
    return f'<span class="badge {cls}">{status}</span>'


def consistency_stats(history: dict) -> tuple[int, int, int]:
    """Returns (completed, missed, partial) counts."""
    completed = sum(1 for s in history.values() if s == "Completed")
    missed    = sum(1 for s in history.values() if s == "Missed")
    partial   = sum(1 for s in history.values() if s == "Partial")
    return completed, missed, partial


# ── Session state init ────────────────────────────────────────────────────────

def init_session():
    data = load_data()
    if "plan" not in st.session_state:
        st.session_state.plan = data.get("plan", "")
    if "goals" not in st.session_state:
        st.session_state.goals = data.get("goals", [])
    if "history" not in st.session_state:
        st.session_state.history = data.get("history", {})
    if "completed_topics" not in st.session_state:
        st.session_state.completed_topics = data.get("completed_topics", [])
    if "notes_output" not in st.session_state:
        st.session_state.notes_output = ""
    if "summary_output" not in st.session_state:
        st.session_state.summary_output = ""

init_session()


# ── Sidebar navigation ────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📚 AI Learning\nAssistant")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["🏠 Dashboard", "📅 Planner", "📈 Tracker", "📖 Course Tools"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Quick stats in sidebar
    completed, missed, partial = consistency_stats(st.session_state.history)
    total = len(st.session_state.history)
    pct = round(completed / total * 100) if total else 0

    st.markdown(f"**This week**")
    st.progress(pct / 100)
    st.caption(f"{pct}% consistency · {completed}/{total} days completed")

    if st.session_state.goals:
        st.markdown("**Active goals**")
        for g in st.session_state.goals:
            st.caption(f"• {g}")


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

if page == "🏠 Dashboard":
    st.markdown('<div class="section-header">Dashboard</div>', unsafe_allow_html=True)

    completed, missed, partial = consistency_stats(st.session_state.history)
    total = len(st.session_state.history)
    pct = round(completed / total * 100) if total else 0

    # Metric row
    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl in [
        (c1, f"{pct}%",     "Consistency"),
        (c2, completed,     "Days completed"),
        (c3, missed,        "Days missed"),
        (c4, len(st.session_state.completed_topics), "Topics mastered"),
    ]:
        col.markdown(
            f'<div class="metric-card"><div class="value">{val}</div>'
            f'<div class="label">{lbl}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("**Weekly progress**")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        rows = ""
        for day in days:
            status = st.session_state.history.get(day, "Pending")
            rows += f"<div style='display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #f1f5f9;font-size:13px'><span style='color:#374151'>{day}</span>{status_badge(status)}</div>"
        st.markdown(
            f'<div style="background:white;border:1px solid #e8ecf2;border-radius:12px;padding:1rem 1.25rem">{rows}</div>',
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown("**Mastered topics**")
        if st.session_state.completed_topics:
            for t in st.session_state.completed_topics:
                st.markdown(f"✓ {t}")
        else:
            st.markdown(
                '<div class="info-box">No topics mastered yet. Mark topics complete in the Tracker.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Current goals**")
        if st.session_state.goals:
            for g in st.session_state.goals:
                st.markdown(f"→ {g}")
        else:
            st.markdown(
                '<div class="info-box">No plan generated yet. Go to Planner to get started.</div>',
                unsafe_allow_html=True,
            )


# ── PLANNER ───────────────────────────────────────────────────────────────────

elif page == "📅 Planner":
    st.markdown('<div class="section-header">Study Planner</div>', unsafe_allow_html=True)

    tab_gen, tab_view, tab_adapt = st.tabs(["Generate plan", "View current plan", "Adapt plan"])

    with tab_gen:
        st.markdown("**Your learning goals**")
        goals_input = st.text_area(
            "One goal per line",
            placeholder="Learn Flutter in 12 weeks\nLearn AI/ML for job switch in 3 months",
            height=100,
            label_visibility="collapsed",
        )

        col1, col2 = st.columns(2)
        with col1:
            learning_hours = st.number_input("Daily learning hours", min_value=0.5, max_value=8.0, value=2.0, step=0.5)
        with col2:
            working_hours = st.number_input("Daily working hours", min_value=0, max_value=16, value=9)

        st.markdown("**Preferred learning window**")
        t1, t2 = st.columns(2)
        with t1:
            start_time = st.time_input("Start", value=datetime.time(21, 0))
        with t2:
            end_time = st.time_input("End", value=datetime.time(23, 0))

        preferred_time = f"{start_time.strftime('%I:%M %p')} – {end_time.strftime('%I:%M %p')}"

        if st.button("Generate my plan", type="primary", use_container_width=True):
            if not goals_input.strip():
                st.warning("Please enter at least one goal.")
            else:
                goals = [g.strip() for g in goals_input.strip().splitlines() if g.strip()]
                with st.spinner("Building your personalised 7-day plan..."):
                    try:
                        plan = generate_plan(goals, learning_hours, working_hours, preferred_time)
                        st.session_state.plan  = plan
                        st.session_state.goals = goals
                        # Reload history and topics from freshly reset storage
                        data = load_data()
                        st.session_state.history = data.get("history", {})
                        st.session_state.completed_topics = data.get("completed_topics", [])
                        st.success("Plan generated! View it in the 'View current plan' tab.")
                    except Exception as e:
                        st.error(f"Failed to generate plan: {e}")

    with tab_view:
        if st.session_state.plan:
            st.markdown(
                f'<div class="plan-box">{st.session_state.plan}</div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                "Download plan as text",
                data=st.session_state.plan,
                file_name="my_learning_plan.txt",
                mime="text/plain",
            )
        else:
            st.markdown(
                '<div class="info-box">No plan yet. Go to the Generate tab to create one.</div>',
                unsafe_allow_html=True,
            )

    with tab_adapt:
        st.markdown("Adaptation reads your current progress and generates a new week that builds on what you've mastered and adjusts difficulty based on your consistency.")

        completed, missed, _ = consistency_stats(st.session_state.history)
        total = len(st.session_state.history)
        pct = round(completed / total * 100) if total else 0

        st.info(f"Current consistency: **{pct}%** ({completed}/{total} days logged)")

        if st.button("Adapt my plan", type="primary", use_container_width=True):
            if not st.session_state.plan:
                st.warning("Generate a plan first before adapting.")
            else:
                with st.spinner("Analysing your progress and adapting..."):
                    try:
                        adapted = adapt_plan()   # reads everything from storage automatically
                        st.session_state.plan = adapted
                        data = load_data()
                        st.session_state.history = data.get("history", {})
                        st.success("Plan adapted for your next week!")
                        st.markdown(
                            f'<div class="plan-box">{adapted}</div>',
                            unsafe_allow_html=True,
                        )
                    except ValueError as e:
                        st.warning(str(e))
                    except Exception as e:
                        st.error(f"Adaptation failed: {e}")


# ── TRACKER ───────────────────────────────────────────────────────────────────

elif page == "📈 Tracker":
    st.markdown('<div class="section-header">Daily Tracker</div>', unsafe_allow_html=True)

    tab_log, tab_topics = st.tabs(["Log progress", "Mark topics"])

    with tab_log:
        col_day, col_status = st.columns(2)
        with col_day:
            day = st.selectbox(
                "Day",
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            )
        with col_status:
            status = st.selectbox("Status", ["Completed", "Partial", "Missed"])

        if st.button("Save progress", type="primary", use_container_width=True):
            updated = log_progress(day, status)
            st.session_state.history = updated["history"]
            st.success(f"{day} marked as **{status}**")
            st.rerun()

        st.markdown("<br>**This week at a glance**", unsafe_allow_html=True)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        rows = ""
        for d in days:
            s = st.session_state.history.get(d, "Pending")
            rows += (
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:9px 0;border-bottom:1px solid #f1f5f9;font-size:13px'>"
                f"<span style='color:#374151;font-weight:500'>{d}</span>"
                f"{status_badge(s)}</div>"
            )
        st.markdown(
            f'<div style="background:white;border:1px solid #e8ecf2;border-radius:12px;padding:1rem 1.25rem">{rows}</div>',
            unsafe_allow_html=True,
        )

    with tab_topics:
        st.markdown("Mark a topic as mastered — the adaptation engine will never repeat it in future plans.")
        topic = st.text_input("Topic name", placeholder="e.g. Flutter Widgets, NumPy arrays")

        if st.button("Mark as mastered", use_container_width=True):
            if topic.strip():
                mark_topic_complete(topic.strip())
                st.session_state.completed_topics = load_data().get("completed_topics", [])
                st.success(f"'{topic}' marked as mastered.")
            else:
                st.warning("Enter a topic name.")

        if st.session_state.completed_topics:
            st.markdown("<br>**Mastered so far**", unsafe_allow_html=True)
            for t in st.session_state.completed_topics:
                st.markdown(f"✓ {t}")


# ── COURSE TOOLS ──────────────────────────────────────────────────────────────

elif page == "📖 Course Tools":
    st.markdown('<div class="section-header">Course Tools</div>', unsafe_allow_html=True)

    tab_upload, tab_summary, tab_notes = st.tabs(["Upload course", "Summary", "Notes"])

    with tab_upload:
        st.markdown("Upload a course file. It will be chunked and stored in the vector database.")

        course_name_raw = st.text_input("Course name", placeholder="e.g. Andrew Ng ML Course")
        uploaded_file = st.file_uploader(
            "Upload file", type=["pdf", "docx", "xlsx"],
            label_visibility="collapsed",
        )

        if uploaded_file and course_name_raw.strip():
            if st.button("Index this course", type="primary", use_container_width=True):
                suffix = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    tmp_path = tmp.name

                with st.spinner(f"Reading and indexing '{course_name_raw}'..."):
                    try:
                        result = process_file(tmp_path, course_name_raw.strip())
                        st.success(result)
                        st.session_state["last_course_display"] = course_name_raw.strip()
                    except ValueError as e:
                        # Covers both "already exists" and "no text found"
                        st.warning(str(e))
                    except Exception as e:
                        st.error(f"Indexing failed: {e}")
                    finally:
                        os.unlink(tmp_path)

        elif uploaded_file and not course_name_raw.strip():
            st.warning("Enter a course name before indexing.")

        # Show all indexed courses
        st.markdown("---")
        st.markdown("**Indexed courses**")
        collections = list_collections()
        if not collections:
            st.caption("No courses indexed yet.")
        else:
            for c in collections:
                st.markdown(
                    f"<div style='padding:6px 0;border-bottom:1px solid #f1f5f9;"
                    f"font-size:13px;color:#374151'>📄 {c['display_name']}"
                    f"<span style='color:#9ca3af;font-size:11px;margin-left:8px'>"
                    f"`{c['collection_name']}`</span></div>",
                    unsafe_allow_html=True,
                )

    with tab_summary:
        collections = list_collections()
        if not collections:
            st.info("No courses indexed yet. Upload a course first.")
        else:
            # Show display names in dropdown
            display_names = [c["display_name"] for c in collections]
            selected_display = st.selectbox("Select course", options=display_names)

            # Get the collection_name for the selected display_name
            selected_col = next(
                c["collection_name"] for c in collections
                if c["display_name"] == selected_display
            )

            if st.button("Generate summary", type="primary", use_container_width=True):
                with st.spinner(f"Summarising '{selected_display}'..."):
                    try:
                        summary = generate_notes_summary(selected_col)
                        st.session_state.summary_output = summary
                    except Exception as e:
                        st.error(f"Summary failed: {e}")

            if st.session_state.summary_output:
                st.markdown("---")
                st.markdown(st.session_state.summary_output)
                st.download_button(
                    "Download summary",
                    data=st.session_state.summary_output,
                    file_name=f"{selected_display}_summary.txt",
                    mime="text/plain",
                )

    with tab_notes:
        collections = list_collections()
        if not collections:
            st.info("No courses indexed yet. Upload a course first.")
        else:
            display_names = [c["display_name"] for c in collections]
            selected_display_n = st.selectbox(
                "Select course", options=display_names, key="notes_select"
            )
            selected_col_n = next(
                c["collection_name"] for c in collections
                if c["display_name"] == selected_display_n
            )

            topic_filter = st.text_input(
                "Topic (optional)",
                placeholder="e.g. Gradient Descent — leave empty for full course notes",
            )

            if st.button("Generate notes", type="primary", use_container_width=True):
                topic = topic_filter.strip() if topic_filter.strip() else None
                with st.spinner(f"Generating notes for '{selected_display_n}'..."):
                    try:
                        notes = generate_notes_flashcards(selected_col_n, topic)
                        st.session_state.notes_output = notes
                    except Exception as e:
                        st.error(f"Notes generation failed: {e}")

            if st.session_state.notes_output:
                st.markdown("---")
                st.markdown(st.session_state.notes_output)
                st.download_button(
                    "Download notes",
                    data=st.session_state.notes_output,
                    file_name=f"{selected_display_n}_notes.txt",
                    mime="text/plain",
                )