"""Match agent: rank seniors for a junior's need.

score = 0.45 * did this course
      + 0.25 * topic fit (text similarity to the senior's strengths)
      + 0.15 * rating (out of 5)
      + 0.15 * response rate (0 to 1)
  + 0.10 bonus if the question is urgent and the senior is free within 48 hours
Change WEIGHTS to tune it, and say why in the demo.
"""
from agents.coordination import IST, next_slots
from retrieval import Retriever
from datetime import datetime

WEIGHTS = {"course": 0.45, "topic": 0.25, "rating": 0.15, "response": 0.15, "soon": 0.10}


def _courses(senior):
    return [c.strip() for c in str(senior.get("courses_done", "")).split(";") if c.strip()]


def rank_seniors(question, intake_result, seniors, k=3, skip_ids=()):
    if seniors.empty:
        return []
    pool = seniors[~seniors["id"].astype(str).isin([str(s) for s in skip_ids])]
    if pool.empty:
        return []
    texts = [f"{r['strengths']} {r['courses_done']}" for _, r in pool.iterrows()]
    topic_scores = Retriever(texts).scores(question)
    course = intake_result.get("course")

    ranked = []
    for i, (_, s) in enumerate(pool.iterrows()):
        did_course = 1.0 if course and course in _courses(s) else 0.0
        topic = float(topic_scores[i]) if len(topic_scores) else 0.0
        rating = float(s["rating"]) / 5
        response = float(s["response_rate"])
        slots = next_slots(s.get("availability", ""), min_gap_hours=1)
        hours_away = (slots[0] - datetime.now(IST)).total_seconds() / 3600 if slots else 999
        soon = 1.0 if intake_result.get("urgency") == "high" and hours_away <= 48 else 0.0
        score = (WEIGHTS["course"] * did_course + WEIGHTS["topic"] * topic
                 + WEIGHTS["rating"] * rating + WEIGHTS["response"] * response + WEIGHTS["soon"] * soon)
        reasons = []
        if soon:
            reasons.append("free within 48 hours")
        if did_course:
            reasons.append(f"has done {course}")
        if topic > 0.15:
            reasons.append("strong on this topic")
        if s["rating"] >= 4.5:
            reasons.append(f"rated {s['rating']}/5")
        if response >= 0.8:
            reasons.append("replies fast")
        row = s.to_dict()
        row.update({"score": round(score, 3), "reasons": reasons or ["available senior"]})
        ranked.append(row)
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:k]
