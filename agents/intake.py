
"""Safety + Intake agent.

1. Safety: refuse cheating and abuse before anything else runs.
2. Intake: turn a messy question into structured fields the other agents use.
"""
import re

from agents import content_filter

# Quick rule-based check. Runs even without the AI, so it costs nothing.
# ("do my DA" on its own is no longer here: content_filter.py tells "can you do my DA" from "how do I do my DA".)
BLOCK_PATTERNS = [
    r"\b(assignment|da|record|homework)s?\b.{0,25}\bfor me\b",
    r"\b(answer key|leaked? (paper|question)|paper leak)\b",
    r"\bproxy\b.{0,15}\battendance\b",
    r"\b(buy|sell)\b.{0,15}\b(assignment|records?)\b",
]

# Requests unrelated to academic support or useful college resources.
# These are checked separately from academic integrity violations.
OUT_OF_SCOPE_PATTERNS = [
    r"\b(movie|movies|film|films)\b.{0,30}\b(recommend|suggest|watch)\b",
    r"\b(recommend|suggest)\w*\b.{0,30}\b(movies?|films?|web ?series)\b",
    r"\bmake[\s-]?out\s+(spots?|places?)\b",
    r"\b(date|dating)\s+(spots?|places?|ideas?)\b",
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


def _gemini_classifier(llm):
    """Gemini as the grey-zone judge; returns None when the AI is offline (the filter then uses rules)."""
    if llm is None or not llm.online:
        return None

    def classify(text):
        reply = llm.text(content_filter.CLASSIFIER_PROMPT.format(text=text)) or "ok"
        words = reply.strip().lower().split()
        return words[0].strip(".,") if words else "ok"
    return classify


def classify_request(question, retrieval_score=None, llm=None):
    """Sort a question into allowed / blocked / out_of_scope, with a category and a reason."""
    # 0. The content filter: vulgar, cheating, leisure and off-topic, cheapest check first.
    check = content_filter.check_content(question, kind="question", retrieval_score=retrieval_score,
                                         llm_classify=_gemini_classifier(llm))
    if not check["allowed"]:
        hard_no = check["category"] in ("vulgar", "cheating", "too_short")
        return {"status": "blocked" if hard_no else "out_of_scope",
                "category": check["category"], "reason": check["message"]}

    q = question.lower()

    # 1. Block academic dishonesty and other prohibited requests first.
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, q):
            return {"status": "blocked", "category": "academic_integrity", "reason": REFUSAL}

    # 2. Reject empty or extremely short questions.
    if len(q.strip()) < 4:
        return {"status": "blocked", "category": "too_short",
                "reason": "Please type a full question so we can help."}

    # 3. Flag requests unrelated to the app's purpose.
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, q):
            return {"status": "out_of_scope", "category": "off_topic", "reason": OUT_OF_SCOPE_REFUSAL}

    # 4. Allow requests that pass the checks above.
    return {"status": "allowed", "category": "campus_help", "reason": ""}


def safety_check(question, llm=None):
    """Older yes/no form of classify_request: returns (allowed, reason)."""
    check = classify_request(question)
    return check["status"] == "allowed", check["reason"]


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
