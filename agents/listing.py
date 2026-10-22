"""Listing agent: a photo or one line becomes a structured listing,
then gets matched to juniors who posted a 'looking for' request."""
from retrieval import Retriever

CATEGORIES = ["Textbook", "Drafting / EG kit", "Lab coat", "Calculator", "Cycle", "Hostel essentials", "Electronics", "Other"]
KEYWORDS = {
    "Textbook": ["book", "textbook", "edition", "guide"],
    "Drafting / EG kit": ["drafter", "drafting", "eg kit", "engineering graphics", "mini drafter", "set square"],
    "Lab coat": ["lab coat", "apron", "coat"],
    "Calculator": ["calculator", "casio", "fx-"],
    "Cycle": ["cycle", "bicycle", "bike"],
    "Hostel essentials": ["mattress", "bucket", "pillow", "cooler", "kettle", "extension", "lamp"],
    "Electronics": ["arduino", "laptop", "mouse", "keyboard", "headphone", "charger"],
}


def _rule_listing(text):
    t = (text or "").lower()
    category = "Other"
    for cat, words in KEYWORDS.items():
        if any(w in t for w in words):
            category = cat
            break
    condition = "Good"
    if any(w in t for w in ["new", "unused", "sealed"]):
        condition = "Like new"
    elif any(w in t for w in ["old", "used a lot", "torn", "worn"]):
        condition = "Fair"
    credits = {"Textbook": 20, "Drafting / EG kit": 30, "Lab coat": 15, "Calculator": 25,
               "Cycle": 80, "Hostel essentials": 15, "Electronics": 40}.get(category, 10)
    return {
        "title": (text or "Item").strip()[:60].capitalize(),
        "category": category,
        "course": None,
        "condition": condition,
        "suggested_credits": credits,
        "description": (text or "").strip(),
        "source": "rules",
    }


def describe_item(text="", image_bytes=None, mime_type="image/jpeg", llm=None):
    if llm is not None and llm.online and (image_bytes or text):
        prompt = f"""You are the Listing agent of PassItOn, where VIT seniors pass on items to juniors.
From the photo and/or the seller's note, return JSON with keys:
"title" (max 8 words), "category" (one of {CATEGORIES}), "course" (the course it is for, or null),
"condition" ("Like new", "Good" or "Fair"), "suggested_credits" (integer 5 to 100; textbook about 20, cycle about 80),
"description" (one sentence a junior would find useful).
Only describe what you can actually see or what the note says.
Seller's note: {text or '(none)'}"""
        result = llm.json(prompt, image_bytes=image_bytes, mime_type=mime_type)
        if result and result.get("title"):
            result["source"] = "ai"
            return result
    return _rule_listing(text)


def match_wanted(item, wanted, k=3, min_score=0.08):
    """Juniors whose 'looking for' request matches this item."""
    if wanted.empty:
        return []
    texts = [f"{r['item']} {r['course']}" for _, r in wanted.iterrows()]
    query = f"{item.get('title', '')} {item.get('category', '')} {item.get('course') or ''} {item.get('description', '')}"
    scores = Retriever(texts).scores(query)
    rows = []
    for i, (_, w) in enumerate(wanted.iterrows()):
        if scores[i] >= min_score:
            row = w.to_dict()
            row["score"] = round(float(scores[i]), 3)
            rows.append(row)
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:k]
