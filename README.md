# PassItOn

A VIT-only AI help network for ConvergeX 2026 (Track 4: AI for Society). A junior asks a question; AI agents answer it from seniors' tips, or match the junior with the right senior and set up the meeting.

## Run it (Windows, about 10 minutes)

1. Install Python 3.11 or newer from python.org. Tick **"Add Python to PATH"** during install.
2. Unzip this folder, open it, click the address bar, type `cmd` and press Enter.
3. Run:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. (Optional but recommended) Turn the AI on: copy `.streamlit\secrets.toml.example` to `.streamlit\secrets.toml` and paste a free Gemini key from https://aistudio.google.com/apikey
5. Start it:
   ```
   streamlit run app.py
   ```
   It opens in your browser at http://localhost:8501

Mac/Linux: use `source venv/bin/activate` instead of `venv\Scripts\activate`.

**No key? It still works.** Without a key the app runs in offline mode: the same flow, with rules instead of AI writing the answers. The sidebar shows which mode you're in.

## Try these

- Ask: `DSA CAT is tomorrow and recursion confuses me` → instant answer from a senior's tip
- Click **Still stuck? Talk to a senior** → senior cards → **Pick** → time, place and a drafted message
- Ask: `how do I apply for a semester exchange abroad` → no tip covers it, so it hands off to seniors and lands in the **Senior inbox**
- In **Senior inbox**, write an answer and approve it → ask the same question again → now answered instantly (the flywheel)
- **Pass it on**: type `mini drafter used one semester` (or upload a photo) → listing + juniors who want it
- **Insights**: real survey results (27 responses) and the questions the AI couldn't answer, grouped by course
- **Under the hood**: every agent step for your last action
- Ask: `please do my DA assignment` → refused by the Safety agent

## Files

| File | What it is | Owner |
|---|---|---|
| `app.py` | All the screens | Shravya |
| `agents/orchestrator.py` | Runs agents in order, records the trace | Anikeit |
| `agents/intake.py` | Safety check + understanding the question | Anikeit |
| `agents/ask.py` | Answers from seniors' tips, decides confidence | Anikeit |
| `agents/match.py` | Ranks seniors | Rishika |
| `agents/coordination.py` | Picks a slot and spot, drafts the message | Aditya |
| `agents/listing.py` | Photo/text to listing, matches juniors | Aditya |
| `llm.py` | Gemini wrapper with safe fallbacks | Anikeit |
| `retrieval.py` | Text similarity search | Rishika |
| `eval.py` | Accuracy test → numbers for the slides | Rishika |
| `data/knowledge.csv` | Senior tips (**replace samples with real ones**) | Rishika |
| `data/seniors.csv` | Senior profiles (**replace samples with real ones**) | Rishika |
| `data/wanted.csv` | Juniors' "looking for" requests | Rishika |
| `data/places.csv` | Campus meeting spots | Rishika |
| `data/test_questions.csv` | 47 questions for `eval.py` (41 covered, 6 off-topic) | Rishika |
| `data/survey/` | Survey: real (anonymised), synthetic, combined, summary | Rishika |

## Measure it

```
python eval.py
```
Prints how often the right tip ranks first and whether out-of-scope questions are handed off. Try another threshold with `python eval.py 0.25`.

## Deploy (free)

Push the folder to a GitHub repo (the `.gitignore` keeps your key out), then go to https://share.streamlit.io, pick the repo and `app.py`, and paste the key under **Advanced settings → Secrets** in the same format as the example file.

## Notes

- All 40 tips and 10 senior profiles are placeholders (`sample = True` in `knowledge.csv`). Replace them with real seniors' tips (with permission). Tips added through the Senior inbox are saved with `sample = False`.
- Survey: only `survey_real_anonymised.csv` is real (27 responses). `survey_synthetic.csv` is simulated from the real answer patterns for testing; never quote it as survey results. The Insights tab shows real data unless you switch on "Include simulated responses".
- Phone numbers in `seniors.csv` are optional. If filled (country code, no `+`, e.g. `919876543210`), the app shows an **Open in WhatsApp** button.
- Edits made in the Senior inbox are saved to `data/knowledge.csv` when running locally.
