
"""Safety + Intake agent.

1. Safety: refuse cheating and abuse before anything else runs.
2. Intake: turn a messy question into structured fields the other agents use.
"""
import re

# Quick rule-based check. Runs even without the AI, so it costs nothing.
BLOCK_PATTERNS = [
    r"\b(do|write|solve|complete|finish|make)\s+(my|our|this)\b.{0,25}\b(assignment|da|record|lab record|project|homework)s?\b",
    r"\b(assignment|da|record|homework)s?\b.{0,25}\bfor me\b",
    r"\b(answer key|leaked? (paper|question)|paper leak)\b",
    r"\bproxy\b.{0,15}\battendance\b",
    r"\b(buy|sell)\b.{0,15}\b(assignment|records?)\b",
]

# Requests unrelated to academic support or useful college resources.
# These are checked separately from academic integrity violations.
OUT_OF_SCOPE_PATTERNS = [
    r"\b(movie|movies|film|films)\b.{0,30}\b(recommend|suggest|watch)\b",
    r"\b(makeout|make-out)\s+spots?\b",
    r"\b(date|dating)\s+spots?\b",
    r"\b(weekend)\s+(fun|plans|activities)\b",
]

REFUSAL = (
    "PassItOn can't help with doing graded work, leaks or proxies. "
    "Ask how to approach it instead, and we'll find you tips or a senior who can explain it."
)

OUT_OF_SCOPE_REFUSAL = (
    "PassItOn focuses on academic support and useful college resources. "
    "Try asking about study tips, campus facilities, clubs, FFCS, "
    "student opportunities, or items you need for college instead."
)

# Shortcuts students actually type. Add more as you see them.
ALIASES = {
    "dsa": "Data Structures and Algorithms",
    "data structures": "Data Structures and Algorithms",
    "recursion": "Data Structures and Algorithms",
    "eg": "Engineering Graphics",
    "engineering graphics": "Engineering Graphics",
    "drafter": "Engineering Graphics",
    "ffcs": "FFCS",
    "slot": "FFCS",
    "timetable": "FFCS",
    "calc": "Calculus",
    "calculus": "Calculus",
    "physics": "Engineering Physics",
    "chemistry": "Engineering Chemistry",
    "python": "Problem Solving and Programming",
    "c programming": "Problem Solving and Programming",
    "programming": "Problem Solving and Programming",
    "internship": "Internships and Careers",
    "club": "Clubs and Campus Life",
    "hostel": "Clubs and Campus Life",
    "mess": "Clubs and Campus Life",
}

TYPES = ["concept", "exam", "ffcs", "lab", "project", "career", "campus", "item", "other"]


def safety_check(question, llm=None):
    """Returns (allowed, reason)."""
    q = question.lower()

    # 1. Block academic dishonesty and other prohibited requests first.
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, q):
            return False, REFUSAL

    # 2. Reject empty or extremely short questions.
    if len(q.strip()) < 4:
        return False, "Please type a full question so we can help."

    # 3. Flag requests unrelated to the app's purpose.
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, q):
            return False, OUT_OF_SCOPE_REFUSAL

    # 4. Allow requests that pass the checks above.
    return True, ""


def _rule_intake(question, courses):
    q = question.lower()
    course = None
    for c in courses:
        if c.lower() in q:
            course = c
            break
    if not course:
        for word, c in ALIASES.items():
            if re.search(rf"\b{re.escape(word)}\b", q):
                course = c
                break
    if any(w in q for w in ["cat", "fat", "exam", "test", "quiz", "pyq", "paper"]):
        qtype = "exam"
    elif any(w in q for w in ["ffcs", "slot", "timetable", "register"]):
        qtype = "ffcs"
    elif any(w in q for w in ["lab", "record", "viva"]):
        qtype = "lab"
    elif any(w in q for w in ["intern", "placement", "resume", "career"]):
        qtype = "career"
    elif any(w in q for w in ["buy", "sell", "book", "kit", "coat", "calculator", "cycle"]):
        qtype = "item"
    else:
        qtype = "concept"
    urgent_words = ["tomorrow", "today", "tonight", "urgent", "asap", "thursday", "monday",
                    "tuesday", "wednesday", "friday", "saturday", "sunday"]
    urgency = "high" if any(w in q for w in urgent_words) else "medium" if qtype == "exam" else "low"
    return {"course": course, "topic": question[:80], "type": qtype, "urgency": urgency, "source": "rules"}


def intake(question, courses, llm=None):
    """Structured fields: course, topic, type, urgency."""
    if llm is not None and llm.online:
        prompt = f"""You are the intake agent of PassItOn, a help app for students at VIT Vellore.
Read the student's question and return JSON with exactly these keys:
"course": one of {courses} or null if none fits,
"topic": the specific topic in at most 6 words,
"type": one of {TYPES},
"urgency": "high" if they mention an exam or deadline within about 3 days, "medium" if an exam is mentioned without a date, otherwise "low".

Question: {question}"""
        result = llm.json(prompt)
        if result and "type" in result:
            if result.get("course") not in courses:
                result["course"] = _rule_intake(question, courses)["course"]
            result["source"] = "ai"
            return result
    return _rule_intake(question, courses)
