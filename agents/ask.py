"""Ask agent: answer from seniors' knowledge, and admit when it can't.

Steps: retrieve the closest senior tips -> (AI) write an answer that only uses
those tips -> decide if we're confident enough, otherwise hand off to Match.
"""
from retrieval import Retriever

COURSE_BOOST = 0.10  # small bonus for tips from the same course as the question


QUESTION_WEIGHT = 0.6  # how much the tip's own question/topic counts vs. the full tip text


def kb_text(row):
    return f"{row['course']} {row['topic']} {row['question']} {row['answer']}"


def kb_question(row):
    return f"{row['topic']} {row['question']}"


def retrieve(question, kb, intake_result, k=3):
    """Top-k tips as a list of dicts with a 'score'.

    Short questions match the tip's own question better than its long answer,
    so we score both and blend them.
    """
    if kb.empty:
        return []
    full = Retriever([kb_text(r) for _, r in kb.iterrows()]).scores(question)
    short = Retriever([kb_question(r) for _, r in kb.iterrows()]).scores(question)
    raw = QUESTION_WEIGHT * short + (1 - QUESTION_WEIGHT) * full
    results = []
    for i, score in enumerate(raw):
        row = kb.iloc[i].to_dict()
        if intake_result.get("course") and row["course"] == intake_result["course"]:
            score += COURSE_BOOST
        row["score"] = round(float(min(score, 1.0)), 3)
        results.append(row)
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]


def answer(question, tips, llm=None, threshold=0.20):
    """Returns dict: text, confident, sources, best_score, source ('ai' or 'rules')."""
    best = tips[0]["score"] if tips else 0.0
    if not tips or best < threshold:
        return {"text": None, "confident": False, "sources": [], "best_score": best, "source": "rules"}

    if llm is not None and llm.online:
        notes = "\n".join(
            f"[{t['id']}] ({t['senior_name']}, {t['senior_year']}, {t['course']}): {t['answer']}" for t in tips
        )
        prompt = f"""You are the Ask agent of PassItOn, a help app for VIT Vellore students.
Answer the junior's question using ONLY the senior notes below. Do not add facts that are not in the notes.
Write 3 to 6 short sentences in a friendly senior-to-junior tone.
Return JSON: {{"answer": "...", "covered": true or false, "used_ids": ["id", ...]}}
Set "covered" to false if the notes do not really answer the question.

Senior notes:
{notes}

Junior's question: {question}"""
        result = llm.json(prompt)
        if result and result.get("answer"):
            used = [str(u) for u in result.get("used_ids", [])]
            sources = [t for t in tips if str(t["id"]) in used] or tips[:1]
            return {
                "text": result["answer"],
                "confident": bool(result.get("covered")),
                "sources": sources,
                "best_score": best,
                "source": "ai",
            }

    # Offline fallback: show the best senior tip as it is.
    top = tips[0]
    return {
        "text": f"{top['answer']}",
        "confident": True,
        "sources": [top],
        "best_score": best,
        "source": "rules",
    }
