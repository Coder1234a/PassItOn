
"""Orchestrator: decides which agents run, in what order, and records a trace
so we can show the jury exactly what happened ("Under the hood" tab)."""
import time
from pathlib import Path

import pandas as pd

from agents import ask, coordination, intake, listing, match
from llm import LLM

DATA = Path(__file__).resolve().parent.parent / "data"
MAX_STEPS = 6  # guardrail: an agent chain never runs longer than this
DEFAULT_THRESHOLD = 0.20  # below this retrieval score, the Ask agent hands off (tuned with eval.py on 45 test questions)


class Trace:
    def __init__(self):
        self.steps = []

    def add(self, agent, action, detail="", started=None):
        if len(self.steps) >= MAX_STEPS * 2:
            return
        ms = int((time.time() - started) * 1000) if started else 0
        self.steps.append({"agent": agent, "action": action, "detail": detail, "ms": ms})


def load_csv(name):
    path = DATA / name
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


class Orchestrator:
    def __init__(self):
        self.llm = LLM()
        self.kb = load_csv("knowledge.csv")
        self.seniors = load_csv("seniors.csv")
        self.wanted = load_csv("wanted.csv")
        places = load_csv("places.csv")
        self.places = places["place"].tolist() if not places.empty else ["Library"]
        self.pending = []  # handed-off questions waiting for a senior's answer (the flywheel)
        self.stats = {"questions": 0, "answered_by_ai": 0, "handed_off": 0, "blocked": 0, "kb_added": 0}

    @property
    def courses(self):
        names = set(self.kb["course"].dropna()) if not self.kb.empty else set()
        for c in self.seniors.get("courses_done", pd.Series(dtype=str)).dropna():
            names.update(x.strip() for x in str(c).split(";") if x.strip())
        return sorted(names)

    # ---------- Flow 1: a junior asks a question ----------
    def handle_question(self, question, threshold=DEFAULT_THRESHOLD):
        trace = Trace()
        self.stats["questions"] += 1

        # Safety + relevance filter runs before intake, retrieval, and matching.
        t = time.time()
        check = intake.classify_request(question)

        status = check["status"]
        reason = check["reason"]
        category = check["category"]

        trace.add(
            "Safety",
            status,
            f"Category: {category}. {reason}",
            t
        )

        if status != "allowed":
            self.stats["blocked"] += 1
            return {
                "status": status,
                "message": reason,
                "category": category,
                "trace": trace.steps
            }

        t = time.time()
        info = intake.intake(question, self.courses, self.llm)
        trace.add("Intake", f"course={info.get('course')}, type={info.get('type')}, urgency={info.get('urgency')}",
                  f"via {info.get('source')}", t)

        t = time.time()
        tips = ask.retrieve(question, self.kb, info)
        trace.add("Ask", f"retrieved {len(tips)} senior tips",
                  ", ".join(f"#{x['id']} ({x['score']})" for x in tips), t)

        t = time.time()
        result = ask.answer(question, tips, self.llm, threshold)
        trace.add("Ask", "confident answer" if result["confident"] else "not confident, handing off",
                  f"best match {result['best_score']} vs threshold {threshold}, via {result['source']}", t)

        seniors = []
        if result["confident"]:
            self.stats["answered_by_ai"] += 1
        else:
            self.stats["handed_off"] += 1
            t = time.time()
            seniors = match.rank_seniors(question, info, self.seniors)
            trace.add("Match", f"ranked {len(self.seniors)} seniors, showing top {len(seniors)}",
                      ", ".join(f"{s['name']} ({s['score']})" for s in seniors), t)
            if question not in [p["question"] for p in self.pending]:
                self.pending.append({"question": question, "course": info.get("course"), "topic": info.get("topic")})

        return {"status": "ok", "intake": info, "answer": result, "tips": tips,
                "seniors": seniors, "trace": trace.steps}

    def more_seniors(self, question, info, skip_ids):
        return match.rank_seniors(question, info, self.seniors, skip_ids=skip_ids)

    # ---------- Flow 2: junior picks a senior ----------
    def plan(self, junior_name, senior, info, question):
        t = time.time()
        plan = coordination.plan_meeting(junior_name, senior, info, question, self.places, self.llm)
        trace = Trace()
        trace.add("Coordination", f"slot {plan['when_text']} at {plan['spot']}", "message drafted", t)
        plan["trace"] = trace.steps
        return plan

    # ---------- Flow 3: the flywheel ----------
    def add_to_kb(self, question, advice, senior_name, senior_year, course, topic, save=True):
        tidy = None
        if self.llm.online:
            tidy = self.llm.text(
                "Rewrite this senior's advice as a clear, standalone tip for future juniors at VIT. "
                "Keep every fact, add nothing, max 5 sentences. Return only the tip.\n\n"
                f"Question: {question}\nAdvice: {advice}"
            )
        new_id = int(self.kb["id"].max()) + 1 if not self.kb.empty else 1
        row = {"id": new_id, "course": course or "General", "topic": topic or question[:40],
               "question": question, "answer": (tidy or advice).strip(),
               "senior_name": senior_name, "senior_year": senior_year, "approved": True, "sample": False}
        self.kb = pd.concat([self.kb, pd.DataFrame([row])], ignore_index=True)
        self.stats["kb_added"] += 1
        if save:
            try:
                self.kb.to_csv(DATA / "knowledge.csv", index=False)
            except Exception:
                pass  # read-only hosting: it still lives in memory for this session
        return row

    # ---------- Insights agent (Phase 2 preview) ----------
    def unmet_needs(self):
        """Questions the AI couldn't answer, grouped by course: what seniors should write tips about next."""
        if not self.pending:
            return pd.DataFrame(columns=["course", "waiting_questions", "examples"])
        df = pd.DataFrame(self.pending)
        df["course"] = df["course"].fillna("General")
        out = df.groupby("course")["question"].agg(["count", lambda q: " | ".join(list(q)[:3])]).reset_index()
        out.columns = ["course", "waiting_questions", "examples"]
        return out.sort_values("waiting_questions", ascending=False)

    # ---------- Flow 4: a senior passes on an item ----------
    def handle_listing(self, text="", image_bytes=None, mime_type="image/jpeg"):
        trace = Trace()
        t = time.time()
        item = listing.describe_item(text, image_bytes, mime_type, self.llm)
        trace.add("Listing", f"{item.get('category')}: {item.get('title')}", f"via {item.get('source')}", t)
        t = time.time()
        buyers = listing.match_wanted(item, self.wanted)
        trace.add("Listing", f"matched {len(buyers)} 'looking for' requests", "", t)
        return {"item": item, "buyers": buyers, "trace": trace.steps}
