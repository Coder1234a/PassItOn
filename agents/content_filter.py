"""
content_filter.py  ->  put in agents/ next to intake.py

Blocks vulgar, abusive, sexual and clearly off-topic text BEFORE any AI runs.
Three layers, cheapest first:
  1. Profanity / sexual / abuse   (rules, works offline, Hinglish included)
  2. Off-topic check              (campus/academic keywords + retrieval score)
  3. Optional Gemini classifier   (only for the grey zone, falls back to allow)

Usage:
    from agents.content_filter import check_content
    r = check_content(text, kind="question", retrieval_score=None)
    if not r["allowed"]:
        return {"blocked": True, "message": r["message"], "category": r["category"]}
"""
import re

# ---------------------------------------------------------------- 1. vulgar
# Whole-word matches only (avoids the "Scunthorpe problem": class, assess, Essex).
# Extend these lists freely.
PROFANITY = {
    "fuck", "fucking", "fucker", "shit", "bitch", "bastard", "asshole", "dick",
    "pussy", "cock", "slut", "whore", "cunt", "motherfucker", "bullshit",
    "wtf", "stfu",
}
HINGLISH = {
    "chutiya", "chutiye", "madarchod", "behenchod", "bhenchod", "bhosdike",
    "bhosdi", "gandu", "randi", "harami", "lund", "gaand", "saala", "kutta",
    "kamina", "lavde", "mc", "bc", "bkl",
}
SEXUAL = {
    "sex", "sexy", "porn", "nude", "nudes", "naked", "boobs", "horny", "hookup",
    "onlyfans", "xxx", "erotic", "masturbate",
}
# Phrases, matched as whole words (so "grapes" is not "rape")
ABUSE_PHRASES = [
    "kill yourself", "go die", "i will kill", "i'll kill", "rape", "raped", "send nudes",
]
_ABUSE_RE = [re.compile(r"\b" + re.escape(p) + r"\b") for p in ABUSE_PHRASES]

LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
                      "7": "t", "@": "a", "$": "s", "!": "i"})


def _normalise(text: str) -> str:
    t = text.lower().translate(LEET)
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)          # fuuuuck -> fuuck
    return t


_SPACED = re.compile(r"\b(?:[a-z][\s.\-_*]){2,}[a-z]\b")


def _spaced_variants(t: str):
    """'f u c k' / 'f.u.c.k' -> 'fuck'. Also tries without the first letter,
    so 'a f u c k i n g' (leading word 'a') still yields 'fucking'."""
    out = set()
    for m in _SPACED.finditer(t):
        joined = re.sub(r"[\s.\-_*]", "", m.group())
        out.add(joined)
        out.add(joined[1:])
    return out


def _tokens(t: str):
    return re.findall(r"[a-z']+", t)


BAD_WORDS = PROFANITY | HINGLISH | SEXUAL
_COLLAPSE = lambda w: re.sub(r"(.)\1+", r"\1", w)  # noqa: E731  "fuuck" -> "fuck"
# Collapsed forms shorter than 3 letters are dropped, or "xxx" -> "x" would block every "x".
_BAD_COLLAPSED = {c for c in (_COLLAPSE(w) for w in BAD_WORDS) if len(c) >= 3}
# Spelled-out letters only count for words of 4+ letters, so "slot a b c" is not "bc".
_LONG_BAD = {w for w in BAD_WORDS if len(w) >= 4}


def _is_vulgar(text: str, min_len=1):
    """True if the text has a blocked word (incl. stretched or spelled-out) or an abuse phrase.
    min_len skips short slang (mc, bc) where it would hit real names like "Mc Donald"."""
    t = _normalise(text)
    raw_tokens = set(_tokens(text.lower()))           # before leetspeak, so "1st" stays "1st"
    toks = set(_tokens(t)) | raw_tokens
    toks |= {_COLLAPSE(w) for w in toks}
    bad = {w for w in BAD_WORDS if len(w) >= min_len} | _BAD_COLLAPSED
    if toks & bad:
        return True
    if _spaced_variants(t) & (_LONG_BAD | {_COLLAPSE(w) for w in _LONG_BAD}):
        return True
    return any(r.search(t) for r in _ABUSE_RE)


# ------------------------------------------- 1b. cheating / paid work / misuse
# Always blocked, for every kind (question, answer, listing, name).
# Regex, matched on the normalised text. "proxy server" etc. are allowed.
CHEATING_PATTERNS = [
    # proxy attendance & bunking
    r"\bproxy\s+(attendance|attendence|for me|marking|in class|lagwa|laga)",
    r"\b(give|get|mark|need|want|arrange|take)\s+(me\s+|my\s+)?(a\s+)?proxy\b",
    r"\battend(a|e)nce\s+proxy\b",
    r"\b(fake|false|bogus)\s+attend(a|e)nce\b",
    r"\bbunk(ing)?\s+(class|classes|lecture|lectures)\b",
    r"\bbypass\s+(biometric|attendance|face)",
    # paying someone to do academic work / selling such services
    # asking SOMEONE ELSE to do your work ("how do I do my DA" stays allowed)
    # (the look-behinds keep "can you tell me how to do my project" and "how do I do my DA" allowed)
    r"\b(who|anyone|anybody|someone|somebody|can you|could you|will you|any senior|please|pls|need someone to|looking for someone to)\b.{0,25}(?<!how to )(?<!how )(?<!\bi )(?<!\bwe )\b(do|write|complete|finish|make|solve|submit)\s+(my|our)\s+(da|fat|cat|assignment|assignments|homework|project|record|lab\s*record|report|thesis|seminar|ppt|work|exam)\b",
    r"\b(do|write|complete|finish|make|solve|submit)\s+(my|our)\s+(da|fat|cat|assignment|assignments|homework|project|record|lab\s*record|report|exam|work)\s+for\s+(me|us)\b",
    r"\b(pay|paid|paying|money|rupees|rs\.?|\u20b9|paisa|paise)\b.{0,40}\b(assignment|da|project|record|homework|exam|fat|cat|attendance|report)\b",
    r"\b(assignment|assignments|project|projects|da|record|records|homework|thesis)\b.{0,30}\b(for money|for cash|for pay|for rs|for rupees|paid service|service)\b",
    r"\b(i|we)('ll|\s+will|\s+can)\s+(do|write|complete|make)\s+(your|ur)\s+(assignment|da|project|record|homework|exam)",
    r"\bassignment\s+(help|service|writing)\s+(for|at)\s+(rs|price|money|cash)",
    r"\bwrite\s+(my|the)\s+exam\s+for\b",
    r"\b(impersonat|dummy\s+candidate|appear\s+(in|for)\s+(my\s+)?exam\s+for)",
    # exam malpractice
    r"\b(question\s*paper|qp|paper)\s+(leak|leaked|leaks|before\s+exam)",
    r"\bleak(ed)?\s+(paper|papers|question|questions|answers|key)\b",
    r"\b(cheat|cheating|copy)\s+(in|during|at)\s+(the\s+)?(exam|cat|fat|test)",
    r"\bchit(s)?\s+(in|for)\s+(exam|cat|fat)",
    r"\b(buy|sell|selling|purchase)\s+(exam\s+)?(answers|answer\s*key|marks|grades|certificates?|fake\s+certificate)",
    r"\bchange\s+(my\s+)?(marks|grades|cgpa)\b",
    r"\bhack\s+(vtop|marks|grades|attendance|portal)",
    r"\b(malpractice|plagiari[sz]e|plagiarism\s+checker\s+bypass|bypass\s+turnitin)",
]
_CHEATING_RE = [re.compile(p) for p in CHEATING_PATTERNS]


_PAY_RE = _CHEATING_RE[CHEATING_PATTERNS.index(next(p for p in CHEATING_PATTERNS if p.startswith(r"\b(pay|paid")))]
_FEES_RE = re.compile(r"\b(fee|fees|fine|fines|deposit|registration)\b")


def _is_cheating(text: str) -> bool:
    """True for proxy attendance, paid/outsourced academic work, leaks and other malpractice."""
    t = _normalise(text)
    t_raw = text.lower()  # undo the leetspeak damage on "rs." and the rupee sign for money patterns
    paying_fees = bool(_FEES_RE.search(t_raw))  # "pay FAT exam fees" is not buying an exam
    for r in _CHEATING_RE:
        if r is _PAY_RE and paying_fees:
            continue
        if r.search(t) or r.search(t_raw):
            return True
    return False


# ------------------------------------------------ 1c. leisure / non-academic
# Off-topic fun/lifestyle requests. Blocked UNLESS the text is clearly about
# a VIT club, fest or event (so "film club", "Riviera movie night" still work).
LEISURE_PATTERNS = [
    r"\b(movie|movies|film|films|cinema|theatre|theater|pvr|inox|netflix|web\s*series|ott)\b",
    r"\b(go|going|plan|planning|let'?s\s+go|bunk\s+for)\s+(out\s+)?(for\s+|to\s+)?(a\s+)?(movie|film|party|pub|club\s*night|date|outing|picnic)\b",
    # "date" alone is a deadline ("last date for FFCS"), so only dating phrases count
    r"\b(pub|nightclub|clubbing|dating|girlfriend|boyfriend|crush|tinder)\b",
    r"\b(go|going|went)\s+(on\s+)?a\s+date\b|\bdate\s+(spots?|ideas?|places?|night)\b",
    r"\b(house|birthday|night|drinking|dj)\s+part(y|ies)\b|\bparty\s+(tonight|this\s+weekend|plans?|places?)\b",
    r"\b(gambling|betting|casino|poker|rummy|dream11|ipl\s+bet|satta)\b",
    # "alcohol" is also an organic chemistry topic, and "drug" a biotech one, so only use phrases count
    r"\b(weed|ganja|marijuana|cigarette|cigarettes|vape|vaping|beer|whisky|vodka|booze|liquor)\b",
    r"\b(drink|drinking|buy|get|smoke|smoking|take|taking)\s+(some\s+)?(alcohol|drugs)\b",
    r"\b(gossip|celebrity|celebrities|bollywood|kollywood|tollywood)\b",
    r"\b(ipl|cricket\s+score|match\s+score|who\s+will\s+win)\b",
    r"\b(horoscope|astrology|zodiac)\b",
    r"\b(tell\s+me\s+a\s+joke|meme|memes|roast\s+me)\b",
]
_LEISURE_RE = [re.compile(p) for p in LEISURE_PATTERNS]
# Words that rescue a leisure match because it is a legit campus activity
CAMPUS_EVENT_WORDS = {
    "club", "clubs", "fest", "riviera", "gravitas", "society", "chapter",
    "association", "committee", "orientation", "event", "events", "workshop",
}


def _is_leisure(text: str) -> bool:
    t = _normalise(text)
    raw = text.lower()
    if not any(r.search(t) or r.search(raw) for r in _LEISURE_RE):
        return False
    # "film club", "movie night at Riviera" -> allowed
    return not (set(_tokens(t)) & CAMPUS_EVENT_WORDS)


# ------------------------------------------------------------- 2. off-topic
# If the text contains none of these AND retrieval finds nothing close,
# it is treated as off-topic. Keep this broad: students phrase things loosely.
ON_TOPIC = {
    # academics
    "ffcs", "slot", "slots", "cat", "fat", "da", "exam", "exams", "paper",
    "papers", "syllabus", "course", "courses", "credit", "credits", "grade",
    "gpa", "cgpa", "faculty", "professor", "lab", "labs", "assignment",
    "project", "projects", "research", "dsa", "coding", "programming",
    "python", "java", "c++", "maths", "math", "physics", "chemistry",
    "electronics", "eg", "calculus", "recursion", "algorithm", "notes",
    "server", "network", "computer", "software", "hardware", "linux", "database",
    "sql", "web", "app", "ai", "ml", "data", "code", "plagiarism",
    "study", "revision", "backlog", "arrear", "semester", "exchange",
    "elective", "minor", "honors", "attendance", "timetable", "class",
    # career
    "internship", "internships", "placement", "placements", "resume", "cv",
    "interview", "job", "gsoc", "hackathon", "certification", "linkedin",
    # campus life
    "club", "clubs", "hostel", "mess", "warden", "room", "roommate", "campus",
    "library", "fest", "riviera", "gravitas", "event", "events", "chapter",
    "scholarship", "fees", "bus", "laundry", "wifi", "vtop", "vit", "senior",
    "seniors", "junior", "juniors", "fresher", "first", "year",
    # marketplace
    "coat", "calculator", "kit", "kits", "drafter", "cycle", "bicycle",
    "mattress", "lamp", "kettle", "books", "textbook", "sell", "buy", "free",
    "price", "item", "listing",
    # campus services and deadlines
    "gym", "sports", "ground", "canteen", "food", "printing", "print", "xerox",
    "shop", "stationery", "bank", "atm", "medical", "health", "doctor", "clinic",
    "timing", "timings", "open", "deadline", "date", "registration", "register",
    "fee", "fees", "form", "portal", "certificate", "transport", "auto", "cab",
    "morning", "evening", "faculty", "proctor", "mentor", "cgpa", "marks", "grades",
    # wellbeing (allowed; handled kindly elsewhere)
    "stress", "anxiety", "homesick", "lonely", "advice", "help", "how", "apply",
}

QUESTION_STARTERS = ("how", "what", "which", "when", "where", "can", "should",
                     "is", "do", "does", "any")


def _looks_on_topic(text: str) -> bool:
    """True if any word (or its singular: 'classes' -> 'class') is a campus/academic word."""
    toks = set(_tokens(text.lower()))
    singular = {re.sub(r"(es|s)$", "", w) for w in toks} | {w[:-1] for w in toks if w.endswith("s")}
    return bool((toks | singular) & ON_TOPIC)


# ---------------------------------------------------------------- messages
MESSAGES = {
    "vulgar": "Let's keep it respectful. PassItOn is for VIT study and campus help. "
              "Try rephrasing your question without those words.",
    "off_topic": "That doesn't look like a VIT academics or campus question, so I can't "
                 "help with it here. Try FFCS, exams, clubs, hostel, internships or "
                 "the market.",
    "cheating": "PassItOn can't help with proxy attendance, paid assignment or exam work, "
                "paper leaks or any other academic dishonesty. Ask a senior how to "
                "learn the topic or plan your time instead.",
    "leisure": "PassItOn is only for VIT academics and campus help, so movies, parties "
               "and other fun plans are outside what it can do. Ask about FFCS, exams, "
               "clubs, hostel, internships or the market.",
    "too_short": "Add a few more words so a senior can understand what you need.",
}


def _result(allowed, category=None, reason=None):
    return {
        "allowed": allowed,
        "category": category,
        "reason": reason,
        "message": MESSAGES.get(category, "") if not allowed else "",
    }


# ------------------------------------------------------------------- main
def check_content(text, kind="question", retrieval_score=None, llm_classify=None):
    """
    kind: "question" | "answer" | "listing" | "name"
    retrieval_score: best TF-IDF similarity from agents/ask.py if you already
        have it (0..1). Lets close matches skip the off-topic check.
    llm_classify: optional callable(text) -> "ok" | "vulgar" | "cheating" | "off_topic".
        Only called in the grey zone. Wrap it in try/except; failure = allow.
    """
    text = (text or "").strip()

    # Layer 1b: cheating, proxy attendance, paid academic work (every kind)
    if kind != "name" and _is_cheating(text):
        return _result(False, "cheating", "academic dishonesty / paid work")

    if kind == "name":
        # names: only the vulgar check (no topic rules)
        return _result(False, "vulgar", "profanity in name") if _is_vulgar(text, min_len=3) \
            else _result(True)

    if len(text) < 3:
        return _result(False, "too_short", "empty or tiny input")

    # Layer 1: vulgar / abusive / sexual (applies to every kind)
    if _is_vulgar(text):
        return _result(False, "vulgar", "blocked word or phrase")

    # Layer 1c: movies, parties, betting and other non-academic plans.
    # Not for answers: a senior saying "avoid parties before FAT" is good advice.
    if kind in ("question", "listing") and _is_leisure(text):
        return _result(False, "leisure", "non-academic leisure topic")

    # Layer 2: off-topic (questions only; a listing like "Casio fx-991ES" has no campus words)
    if kind == "question":
        if _looks_on_topic(text):
            return _result(True)
        # retrieval_score may be a number or a function, so the search only runs when needed
        score = retrieval_score() if callable(retrieval_score) else retrieval_score
        if score is not None and score >= 0.20:
            return _result(True)                 # a real senior tip matches

        # Grey zone: nothing recognised. Ask Gemini if available.
        if llm_classify is not None:
            try:
                verdict = llm_classify(text)
                if verdict in ("vulgar", "cheating", "off_topic"):
                    return _result(False, verdict, "llm classifier")
                return _result(True)
            except Exception:
                pass                              # fall through to rule below

        # Rule fallback (offline): very short, no campus words -> off-topic
        if len(_tokens(text)) <= 6 or not text.lower().startswith(QUESTION_STARTERS):
            return _result(False, "off_topic", "no campus/academic keyword")

    return _result(True)


# --------------------------------------------------- Gemini prompt (optional)
CLASSIFIER_PROMPT = """You moderate a college help app for VIT Vellore students.
Classify the text with ONE word:
ok        = academics, exams, courses, FFCS, clubs, hostel, internships, campus life,
            wellbeing, or buying/selling student items
vulgar    = profanity, sexual content, harassment or abuse
cheating  = proxy attendance, paying/being paid to do assignments or exams, paper
            leaks, copying, grade tampering, any academic dishonesty
off_topic = unrelated to student life (celebrity gossip, politics debate, jokes, etc.)
Text: {text}
Answer with only: ok, vulgar, cheating or off_topic"""