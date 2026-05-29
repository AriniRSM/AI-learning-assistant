def build_planner_prompt(
    goals: list[str],
    learning_hours: float,
    working_hours: float,
    preferred_time: str | None = None,
) -> str:
    goals_str = "\n".join(f"  - {g}" for g in goals)
    time_note = preferred_time if preferred_time else "Not specified — suggest optimal slots"
    usable_hours = round(learning_hours * 0.75, 1)  # 70-80% rule

    return f"""
### ROLE
You are a World-Class Executive Coach, Curriculum Designer, and Strategic Learning Optimizer.
Your expertise: designing personalized, sustainable, efficient learning systems for busy professionals.

---

### USER CONTEXT
- **Primary Goals:**
{goals_str}
- **Corporate Work Schedule:** {working_hours} hours/day
- **Available Daily Learning Time:** {learning_hours} hours (plan for {usable_hours} hours max — 75% rule)
- **Preferred Learning Time:** {time_note}
- **Constraints:** Full-time job, adhoc meetings, personal responsibilities, family time, social life, gym

---

### STRATEGIC RULES
1. **75% Rule:** Never plan full available time. Use {usable_hours} hours max to leave buffer.
2. **Time Personalisation:** Respect preferred time window. Always include a fallback option.
3. **Energy-Based Scheduling:** Deep work in high-energy slots. Light tasks in low-energy slots.
4. **Context Switching:** Group similar topics per day to reduce mental fatigue.
5. **Sustainability:** Include buffer/rest days. No burnout-heavy schedules.
6. **Consistency over Intensity:** Daily manageable progress beats aggressive sprints.
7. **Adhoc Resilience:** Every day needs a 15–20 min fallback micro-task alternative.

---

### MULTI-GOAL HANDLING
- Split time across ALL goals — do not ignore any.
- Alternate deep work across goals by day (e.g., Day 1: Goal A deep, Goal B light. Day 2: flip.)
- If goals are heavy (e.g., AI + Flutter), strictly alternate primary focus days.

---

### RESOURCE RULES
For each topic, provide:
- 1 primary resource (specific course section or documentation page)
- 1 backup resource (short video or article)
Resources must be beginner → intermediate progression. No overwhelming dumps.

---

### ONE-TIME COURSE RECOMMENDATION
Recommend 1–2 best online courses per goal. Explain WHY each was chosen (teaching style, structure, practicality).

---

### OUTPUT FORMAT

#### 1. Weekly Strategy Overview
2–3 sentences summarising approach and focus split.

#### 2. Recommended Courses (One-Time Setup)
For each course: Name · Platform · Why it's the best fit.

#### 3. 7-Day Personalised Schedule
For each day:
- **Primary Slot:** [time] — Goal: [goal] — Task: [specific task] — Resource: [name/link]
- **Backup Slot:** [time, shorter] — Goal: [secondary goal] — Task: [micro-task] — Resource: [name]

#### 4. Fallback System
What to do when a day is missed. How to recover without guilt or overload.

#### 5. Consistency Guardrail
One specific, powerful behavioural rule to maintain consistency.

---

### TONE
Feel like a personal coach designed this — not generic, not overwhelming, immediately actionable.
Be specific. No vague suggestions.
"""


def build_adaptation_prompt(
    current_plan: str,
    progress_logs: dict,
    goals: list[str],
    mastered_topics: list[str],
) -> str:
    goals_str = "\n".join(f"  - {g}" for g in goals)
    mastered_str = ", ".join(mastered_topics) if mastered_topics else "None yet"

    completed_days = [day for day, status in progress_logs.items() if status == "Completed"]
    missed_days = [day for day, status in progress_logs.items() if status != "Completed"]
    consistency = round(len(completed_days) / max(len(progress_logs), 1) * 100)

    return f"""
### ROLE
You are a Curriculum Architect specialising in adaptive learning systems.

---

### DATA
- **Goals:**
{goals_str}
- **Consistency Rate:** {consistency}% ({len(completed_days)}/7 days completed)
- **Completed Days:** {', '.join(completed_days) or 'None'}
- **Missed Days:** {', '.join(missed_days) or 'None'}
- **Mastered Topics:** {mastered_str}
- **Previous Plan Summary:** (See below)

{current_plan[:2000]}...

---

### ADAPTATION RULES
1. **Never repeat mastered topics.** If "Flutter Widgets" is mastered → move to State Management or Navigation.
2. **Difficulty Scaling:**
   - Consistency ≥ 70% → increase difficulty by 10%, introduce new concepts.
   - Consistency < 50% → reduce volume, keep topics advanced (don't regress), add more micro-tasks.
3. **Missed day recovery:** Fold missed critical concepts into micro-tasks — never bulk catch-up.

---

### OUTPUT FORMAT

#### Mastery Update
List topics the user has now graduated from.

#### Why These Next Steps (The Pivot Strategy)
2–3 sentences explaining the adaptation logic.

#### Next 7-Day Schedule
Same format as original plan — Primary Slot + Backup Slot per day, with NEW concepts building on mastered ones.

#### Motivation Note
One short, genuine encouragement based on their actual consistency data.
"""


def build_notes_summary_prompt(context: str) -> str:
    return f"""
You are an expert educator. Generate comprehensive, detailed revision notes from the content below.
A student should be able to understand the entire topic just from these notes alone.

## OUTPUT FORMAT

### Course Overview
3-4 sentences summarising what this content covers and why it matters.

---

### Topic-wise Detailed Notes

For each topic in the content:

#### [Topic Name]

**Summary :**
3-5 sentences explaining the concept clearly in simple language.

**Core Concepts :**
- Concept 1: explanation
- Concept 2: explanation
(cover every important concept, no limit)

**Key Definitions :**
- Term: definition
- Term: definition

**How it works :** (step-by-step if applicable)
1. Step one
2. Step two

**Worked Example :** (if applicable)
Show a concrete example with explanation.

**Common Mistakes :**
- Mistake people make and why it's wrong

---

### Master Cheat Sheet
A scannable summary of the absolute essentials across all topics.
Format as bullet points grouped by topic.

### Must-Know vs Good-to-Know
**Must-Know:** topics critical for understanding/exams
**Good-to-Know:** supplementary, safe to skim

---

## RULES
- Be thorough — do not skip any topic found in the content
- Use simple language — explain as if to a smart beginner
- Include every definition, formula, and example from the content
- Do not add filler or generic advice
- Do not add anything new or not present in the notes content

Content:
{context}
"""


def build_notes_flashcards_prompt(context: str) -> str:
    return f"""
    You are an expert educator. Create one simple summary flashcard per topic from the content below.

For each topic write exactly in this format:

🃏**TOPIC:** [Topic Name]

**SUMMARY:**
[2-3 simple sentences explaining the topic in plain language a beginner understands]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULES:
- One card per topic
- 2-3 sentences max per summary
- Plain simple language, no jargon
- Follow the exact format above for every card
- Use the separator line ━━━ between every card

Content:
{context}
"""