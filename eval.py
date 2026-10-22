"""Measure how well the Ask agent works. Run:  python eval.py

data/test_questions.csv has a question and the id of the tip that SHOULD answer it.
Leave expected_tip_id empty when no tip covers it: then the right behaviour is
to hand off to a senior instead of answering.

Prints numbers for the results slide.
"""
import sys

import pandas as pd

from agents.orchestrator import DATA, DEFAULT_THRESHOLD, Orchestrator

threshold = float(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_THRESHOLD
orc = Orchestrator()
orc.llm.client = None  # test retrieval + confidence only, so results don't depend on the API
tests = pd.read_csv(DATA / "test_questions.csv", dtype=str).fillna("")

top1 = top3 = covered = handoff_ok = handoff_total = 0
rows = []
for _, t in tests.iterrows():
    out = orc.handle_question(t["question"], threshold)
    if out["status"] != "ok":
        rows.append((t["question"], "blocked", ""))
        continue
    ids = [str(x["id"]) for x in out["tips"]]
    confident = out["answer"]["confident"]
    if t["expected_tip_id"]:
        covered += 1
        top1 += ids[:1] == [t["expected_tip_id"]]
        top3 += t["expected_tip_id"] in ids
        verdict = "correct" if ids[:1] == [t["expected_tip_id"]] and confident else "MISS"
    else:
        handoff_total += 1
        handoff_ok += not confident
        verdict = "handed off (correct)" if not confident else "ANSWERED (should hand off)"
    rows.append((t["question"], verdict, ", ".join(ids)))

for q, v, ids in rows:
    print(f"{v:28} | {q}  [{ids}]")
print("\n--- results (threshold", threshold, ") ---")
if covered:
    print(f"Right tip ranked first:  {top1}/{covered} ({top1 / covered:.0%})")
    print(f"Right tip in top 3:      {top3}/{covered} ({top3 / covered:.0%})")
if handoff_total:
    print(f"Correctly handed off:    {handoff_ok}/{handoff_total}")
