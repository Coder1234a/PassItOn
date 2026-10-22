"""PassItOn web server: serves the phone app (static/) and a small JSON API
that calls the same Python agents as before (agents/).

Run locally:   python server.py        then open http://localhost:5000
On Render:     gunicorn server:app --workers 1 --threads 8
(one worker on purpose: juniors and seniors share live in-memory state)
"""
import base64
import math
import os
import socket
import threading
import time
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from agents import intake as intake_agent
from agents import match
from agents.coordination import next_slots
from agents.orchestrator import DEFAULT_THRESHOLD, Orchestrator

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # photos are shrunk in the browser first

# Questions already waiting for seniors when the demo starts, so their inbox isn't empty.
SEED_QUESTIONS = [
    ("Can first years get into the robotics team, or do they only take second years?", "Clubs and Campus Life", "Ananya"),
    ("Where can I print EG sheets late at night near the men's hostel?", "Engineering Graphics", "Kabir"),
    ("Is the gym open on Sundays?", "Clubs and Campus Life", "Zoya"),
]

# Home-screen rows, in the order first years asked for help in our survey.
ROWS = ["FFCS", "Exams & courses", "Clubs & projects", "Hostel & campus", "Internships & careers"]
CAMPUS_WORDS = ["hostel", "mess", "homesick", "cycle", "travel", "buy", "water", "room", "laundry", "food"]


def clean(value):
    """Make pandas/numpy values safe for JSON (NaN becomes None, numpy numbers become Python)."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def row_for_tip(tip):
    """Which home-screen row a tip belongs to."""
    course = str(tip.get("course", ""))
    text = f"{tip.get('topic', '')} {tip.get('question', '')}".lower()
    if course == "FFCS":
        return "FFCS"
    if course == "Internships and Careers":
        return "Internships & careers"
    if course in ("Clubs and Campus Life", "General"):
        return "Hostel & campus" if any(w in text for w in CAMPUS_WORDS) else "Clubs & projects"
    return "Exams & courses"


class Store:
    """All live demo state. One instance, guarded by a lock."""

    def __init__(self):
        self.lock = threading.Lock()
        self.orc = Orchestrator()
        self.items = [clean(r) for r in pd.read_csv(DATA / "items.csv").to_dict("records")]
        self.requests = []
        self.questions = []
        self.helpful = {}
        self.points = {}
        self.next_id = 1
        for text, course, who in SEED_QUESTIONS:
            self.add_question(text, course, who)

    def new_id(self):
        self.next_id += 1
        return self.next_id

    def add_question(self, text, course, asked_by):
        # Don't queue the same question twice.
        for q in self.questions:
            if q["question"].strip().lower() == text.strip().lower():
                return q
        q = {"id": self.new_id(), "question": text, "course": course or "General",
             "asked_by": asked_by, "created": time.time()}
        self.questions.append(q)
        return q

    def senior(self, senior_id):
        rows = self.orc.seniors[self.orc.seniors["id"].astype(str) == str(senior_id)]
        return None if rows.empty else clean(rows.iloc[0].to_dict())

    def public_senior(self, s, extra=None):
        """What the app shows about a senior (no phone number)."""
        slots = next_slots(s.get("availability", ""), min_gap_hours=1)
        tips = int((self.orc.kb["senior_name"] == s["name"]).sum()) if not self.orc.kb.empty else 0
        helped = sum(1 for r in self.requests if str(r["senior_id"]) == str(s["id"]) and r["status"] == "accepted")
        out = {
            "id": s["id"], "name": s["name"], "year": s["year"], "branch": s["branch"],
            "strengths": [x.strip() for x in str(s.get("strengths", "")).split(",") if x.strip()],
            "courses": [x.strip() for x in str(s.get("courses_done", "")).split(";") if x.strip()],
            "rating": s.get("rating"), "response_rate": s.get("response_rate"),
            "spot": s.get("preferred_spot"), "tips": tips, "helped": helped,
            "next_free": slots[0].strftime("%a %I:%M %p").replace(" 0", " ") if slots else None,
        }
        if extra:
            out.update({k: extra[k] for k in ("score", "reasons") if k in extra})
        return clean(out)

    def tip_view(self, t):
        return clean({"id": t["id"], "course": t["course"], "topic": t["topic"], "question": t["question"],
                      "answer": t["answer"], "senior_name": t["senior_name"], "senior_year": t["senior_year"],
                      "row": row_for_tip(t), "helpful": self.helpful.get(int(t["id"]), 0)})


store = Store()


def body():
    return request.get_json(silent=True) or {}


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/demo")
def demo():
    # Junior and senior phones side by side, for presenting on a laptop or projector.
    return send_from_directory(app.static_folder, "demo.html")


@app.get("/api/bootstrap")
def bootstrap():
    with store.lock:
        tips = [store.tip_view(t) for t in store.orc.kb.to_dict("records")]
        seniors = [store.public_senior(s) for s in store.orc.seniors.to_dict("records")]
        return jsonify({"rows": ROWS, "tips": tips, "seniors": seniors, "items": store.items,
                        "ai_online": store.orc.llm.online})


@app.post("/api/ask")
def ask():
    data = body()
    question = str(data.get("question", "")).strip()[:500]
    me = str(data.get("me", "A junior"))[:40]
    if len(question) < 4:
        return jsonify({"status": "blocked", "message": "Type a full question so seniors know what you need."})
    with store.lock:
        result = store.orc.handle_question(question, DEFAULT_THRESHOLD)
        if result["status"] == "blocked":
            return jsonify({"status": "blocked", "message": result["message"], "trace": result["trace"]})
        info = result["intake"]
        ranked = match.rank_seniors(question, info, store.orc.seniors, k=6)
        deck = [store.public_senior(store.senior(r["id"]), r) for r in ranked]
        ans = result["answer"]
        queued = None
        if not ans["confident"]:
            queued = store.add_question(question, info.get("course"), me)
        sources = [store.tip_view(t) for t in ans["sources"]]
        return jsonify(clean({"status": "ok", "question": question, "info": info, "deck": deck,
                              "answer": {"text": ans["text"], "confident": ans["confident"], "sources": sources,
                                         "via": ans["source"]},
                              "queued": bool(queued), "trace": result["trace"]}))


@app.get("/api/deck")
def deck():
    need = str(request.args.get("need", "")).strip()[:100]
    with store.lock:
        if need:
            info = intake_agent.intake(need, store.orc.courses)  # rules only: fast, no AI call
            ranked = match.rank_seniors(need, info, store.orc.seniors, k=10)
        else:
            ranked = [dict(s, score=None, reasons=[]) for s in store.orc.seniors.to_dict("records")]
            ranked.sort(key=lambda s: s["rating"] * s["response_rate"], reverse=True)
        return jsonify([store.public_senior(store.senior(r["id"]), r) for r in ranked])


@app.post("/api/request")
def request_senior():
    data = body()
    me = str(data.get("me", "A junior"))[:40]
    question = str(data.get("question") or "").strip()[:500]
    with store.lock:
        senior = store.senior(data.get("senior_id"))
        if not senior:
            return jsonify({"error": "That senior isn't on PassItOn any more."}), 404
        for r in store.requests:  # already asked this senior: reuse it
            if r["kind"] == "meet" and r["junior"] == me and str(r["senior_id"]) == str(senior["id"]) \
                    and r["status"] == "pending":
                return jsonify(r)
        topic = question or ", ".join(store.public_senior(senior)["strengths"][:1]) or "general advice"
        info = data.get("info") or intake_agent.intake(topic, store.orc.courses)
        plan = store.orc.plan(me, senior, info, topic)
        req = {"id": store.new_id(), "kind": "meet", "junior": me, "senior_id": senior["id"],
               "senior_name": senior["name"], "question": topic, "status": "pending", "created": time.time(),
               "when": plan["when_text"], "spot": plan["spot"], "message": plan["message"],
               "wa_link": plan["wa_link"], "warning": plan.get("warning"), "trace": plan["trace"]}
        store.requests.append(req)
        return jsonify(clean(req))


@app.post("/api/item_request")
def item_request():
    data = body()
    me = str(data.get("me", "A junior"))[:40]
    with store.lock:
        item = next((i for i in store.items if str(i["id"]) == str(data.get("item_id"))), None)
        if not item:
            return jsonify({"error": "This item was just taken off the market."}), 404
        for r in store.requests:
            if r["kind"] == "item" and r["junior"] == me and r.get("item_id") == item["id"] and r["status"] != "declined":
                return jsonify(r)
        seller = store.senior(item["seller_id"]) or {"name": "the senior", "id": item["seller_id"]}
        req = {"id": store.new_id(), "kind": "item", "junior": me, "senior_id": seller["id"],
               "senior_name": seller["name"], "item_id": item["id"], "question": item["title"],
               "status": "pending", "created": time.time(), "spot": seller.get("preferred_spot")}
        store.requests.append(req)
        return jsonify(clean(req))


@app.get("/api/state")
def state():
    role = request.args.get("role", "junior")
    me = str(request.args.get("me", ""))
    with store.lock:
        if role == "senior":
            mine = [r for r in store.requests if str(r["senior_id"]) == me]
            senior = store.senior(me)
            stats = store.public_senior(senior) if senior else {}
            return jsonify(clean({"requests": mine, "questions": store.questions,
                                  "items": [i for i in store.items if str(i["seller_id"]) == me],
                                  "points": store.points.get(me, 0), "me": stats}))
        return jsonify(clean({"requests": [r for r in store.requests if r["junior"] == me]}))


@app.post("/api/respond")
def respond():
    data = body()
    with store.lock:
        req = next((r for r in store.requests if str(r["id"]) == str(data.get("request_id"))), None)
        if not req:
            return jsonify({"error": "That request no longer exists."}), 404
        req["status"] = "accepted" if data.get("accept") else "declined"
        if req["status"] == "accepted":
            key = str(req["senior_id"])
            store.points[key] = store.points.get(key, 0) + 15
        return jsonify(clean(req))


@app.post("/api/answer")
def answer():
    data = body()
    advice = str(data.get("advice", "")).strip()[:1500]
    if len(advice) < 10:
        return jsonify({"error": "Write at least a sentence so juniors can use it."}), 400
    with store.lock:
        q = next((x for x in store.questions if str(x["id"]) == str(data.get("question_id"))), None)
        senior = store.senior(data.get("senior_id"))
        if not q or not senior:
            return jsonify({"error": "Someone already answered this one."}), 404
        row = store.orc.add_to_kb(q["question"], advice, senior["name"], senior["year"], q["course"],
                                  q["question"][:40], save=False)
        store.questions.remove(q)
        key = str(senior["id"])
        store.points[key] = store.points.get(key, 0) + 10
        return jsonify(clean({"tip": store.tip_view(row), "points": store.points[key]}))


@app.post("/api/listing")
def listing():
    data = body()
    text = str(data.get("text", "")).strip()[:300]
    image, mime = None, "image/jpeg"
    photo = str(data.get("image") or "")
    if photo.startswith("data:") and "," in photo:
        header, b64 = photo.split(",", 1)
        mime = header[5:].split(";")[0] or mime
        try:
            image = base64.b64decode(b64)
        except Exception:
            image = None
    if not text and not image:
        return jsonify({"error": "Add a photo or a line about the item."}), 400
    if not text and not store.orc.llm.online:
        return jsonify({"error": "Add a line about it too. Reading photos needs the AI, which is offline right now."}), 400
    with store.lock:
        result = store.orc.handle_listing(text, image, mime)
        if not text and result["item"].get("source") != "ai":
            return jsonify({"error": "Couldn't read that photo. Add a line about the item and try again."}), 400
        return jsonify(clean({"item": result["item"], "buyers": result["buyers"], "trace": result["trace"]}))


EMOJI = {"Textbook": "📘", "Drafting / EG kit": "📐", "Lab coat": "🥼", "Calculator": "🔢", "Cycle": "🚲",
         "Hostel essentials": "🛏️", "Electronics": "🔧", "Other": "📦"}


@app.post("/api/publish")
def publish():
    data = body()
    item = data.get("item") or {}
    with store.lock:
        senior = store.senior(data.get("senior_id"))
        if not senior or not item.get("title"):
            return jsonify({"error": "Create the listing first."}), 400
        try:
            price = max(0, int(data.get("price") or 0))
        except (TypeError, ValueError):
            price = 0
        new = {"id": store.new_id(), "title": str(item["title"])[:60], "category": item.get("category", "Other"),
               "emoji": EMOJI.get(item.get("category"), "📦"), "condition": item.get("condition", "Good"),
               "price": price, "seller_id": senior["id"], "course": item.get("course"),
               "description": str(item.get("description", ""))[:200], "sample": False, "fresh": True}
        store.items.insert(0, new)
        key = str(senior["id"])
        store.points[key] = store.points.get(key, 0) + 5
        return jsonify(clean(new))


@app.post("/api/helpful")
def helpful():
    tip_id = int(body().get("tip_id", 0))
    with store.lock:
        store.helpful[tip_id] = store.helpful.get(tip_id, 0) + 1
        return jsonify({"helpful": store.helpful[tip_id]})


@app.post("/api/reset")
def reset():
    global store
    store = Store()
    return jsonify({"ok": True})


def lan_ip():
    """The laptop's address on the hotspot, so a phone can open the app too."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    ip = lan_ip()
    print(f"\n  PassItOn is running:  http://localhost:{port}")
    if ip:
        print(f"  On a phone on the same Wi-Fi/hotspot:  http://{ip}:{port}\n")
    app.run(host="0.0.0.0", port=port, threaded=True, debug=False)
