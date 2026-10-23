# PassItOn

A VIT-only app where juniors get help from seniors, built by team **oops** for ConvergeX 2026 (Track 4: AI for Society; Problem Statement 2: AI-Based Smart Campus Management, student services).

- **Juniors:** ask anything and get a senior's tip instantly; swipe through seniors who can help (right = ask, left = skip); grab lab coats, calculators and hostel stuff from seniors in the market; see matches with a meeting time, place and a drafted message.
- **Seniors:** swipe through questions the AI couldn't answer and answer them once (every later junior gets that answer instantly); accept or decline juniors who swiped right on them; pass on items with a photo; earn points towards rewards.

## How it works

| Piece | What it does |
|---|---|
| `static/` | The phone app (HTML, CSS, JS, bundled fonts) |
| `server.py` | Serves the app and a small JSON API; keeps live state shared by both phones |
| `agents/intake.py` | Safety (blocks cheating) and understanding the question |
| `agents/ask.py` | Answers only from seniors' tips; hands off when not confident |
| `agents/match.py` | Ranks seniors: course done, topic fit, rating, reply rate, free soon |
| `agents/coordination.py` | Picks a time and campus spot, drafts the message |
| `agents/listing.py` | Photo or text to a listing, matched to juniors who want it |
| `agents/orchestrator.py` | Runs the agents in order and records the trace ("How the AI got this") |
| `eval.py` | Accuracy test: `python eval.py` |

All seniors, tips and listings in `data/` are samples for the demo. Survey results (27 real responses) are in `data/survey/`.
