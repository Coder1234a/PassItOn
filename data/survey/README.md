# Survey data

Collected with a Google Form (built by `design/create_vit_survey.gs`) on 21 to 22 Oct 2026, shared via Instagram and WhatsApp.

| File | Rows | What it is |
|---|---|---|
| `survey_real_anonymised.csv` | 27 | Real responses (24 first years, 3 seniors). Contact details removed; `left_contact` says whether they left one. **The only file to quote.** |
| `survey_synthetic.csv` | 80 | SIMULATED rows (60 first years, 20 seniors) sampled from the real answer distributions (seed 2026). For testing only. No invented quotes. |
| `survey_combined.csv` | 107 | Both, with a `source` column (`real` / `synthetic`). IDs start with R (real) or S (synthetic). |
| `survey_summary.json` | | Headline numbers, real-only and combined, plus the real free-text quotes. |

Junior-only columns: help_freq, help_with, looked_where, ease_finding_senior_1to5, usefulness_1to5, bought_new, would_pay, frustration.
Senior-only columns: senior_asked_freq, senior_would_answer, senior_motivation, senior_has_items, senior_passes_how.
Multi-select answers are comma-separated option texts.
