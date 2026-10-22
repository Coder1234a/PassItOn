"""PassItOn: the app screens. Run with:  streamlit run app.py"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from agents.orchestrator import DEFAULT_THRESHOLD, Orchestrator

st.set_page_config(page_title="PassItOn", page_icon="🎓", layout="centered")


@st.cache_resource
def get_orchestrator():
    # One shared instance, so a tip a senior approves on one laptop shows up for everyone.
    return Orchestrator()


orc = get_orchestrator()
ss = st.session_state
ss.setdefault("result", None)
ss.setdefault("question", "")
ss.setdefault("qbox", "")  # what's typed in the question box (keyed, so typing is never lost)
ss.setdefault("flash", None)  # one-time success message shown after a rerun
ss.setdefault("card", 0)
ss.setdefault("skipped", [])
ss.setdefault("plan", None)
ss.setdefault("trace", [])
ss.setdefault("listing", None)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("PassItOn")
    st.caption("VIT's seniors, one question away.")
    junior_name = st.text_input("Your name", value="Rahul")
    if orc.llm.online:
        st.success(f"AI online ({orc.llm.model})")
    else:
        st.warning("Offline mode: rules only")
    if orc.llm.last_error:
        st.caption(orc.llm.last_error)
    threshold = st.slider(
        "Confidence threshold", 0.05, 0.60, DEFAULT_THRESHOLD, 0.01,
        help="If the best senior tip scores below this, the AI hands off to a real senior instead of answering.",
    )


def reset_flow():
    ss.card, ss.skipped, ss.plan = 0, [], None


def start_over():
    # Runs before the page redraws, so it can safely clear the question box.
    ss.result, ss.question, ss.qbox = None, "", ""
    reset_flow()


tab_ask, tab_items, tab_inbox, tab_insights, tab_hood = st.tabs(
    ["Ask", "Pass it on", "Senior inbox", "Insights", "Under the hood"]
)

# ---------------- Ask ----------------
with tab_ask:
    st.subheader("Ask anything about VIT life")
    st.caption("Courses, CAT/FAT prep, FFCS, labs, clubs, internships. Answers come from seniors' approved tips.")
    question = st.text_area(
        "Your question", key="qbox", height=90,
        placeholder="e.g. DSA CAT is on Thursday and recursion makes no sense. What should I focus on?",
    )
    if st.button("Ask", type="primary", width="stretch") and question.strip():
        ss.question = question.strip()
        with st.spinner("Agents at work..."):
            ss.result = orc.handle_question(ss.question, threshold)
        ss.trace = ss.result["trace"]
        reset_flow()

    r = ss.result
    if r and r["status"] == "blocked":
        st.error(r["message"])
    elif r:
        info, ans = r["intake"], r["answer"]
        st.caption(
            f"Understood as: **{info.get('course') or 'General'}** · {info.get('type')} · urgency {info.get('urgency')}"
        )
        if ans["confident"]:
            with st.container(border=True):
                st.markdown("**Answer from seniors' knowledge**")
                st.write(ans["text"])
                names = ", ".join(f"{t['senior_name']} ({t['senior_year']}, {t['course']})" for t in ans["sources"])
                st.caption(f"Based on tips from {names} · match score {ans['best_score']}")
                if any(str(t.get("sample")).lower() == "true" for t in ans["sources"]):
                    st.caption("Demo sample: this tip was written by our team to show the flow. "
                               "In the pilot, only real seniors' approved tips are used.")
            if not r["seniors"] and st.button("Still stuck? Talk to a senior"):
                r["seniors"] = orc.more_seniors(ss.question, info, [])
                ss.trace = ss.trace + [{"agent": "Match", "action": f"junior asked for a senior, showing top {len(r['seniors'])}",
                                        "detail": ", ".join(f"{s['name']} ({s['score']})" for s in r["seniors"]), "ms": 0}]
                reset_flow()
                st.rerun()
        else:
            st.info("No senior has answered this exact question yet, so we won't guess. "
                    "Here are the seniors best placed to help. Your question has also been sent to the Senior inbox.")

        # ---- Senior cards: pick or skip, one at a time ----
        if r["seniors"] and not ss.plan:
            if ss.card < len(r["seniors"]):
                sen = r["seniors"][ss.card]
                with st.container(border=True):
                    st.markdown(f"### {sen['name']}")
                    st.caption(f"{sen['year']} · {sen['branch']} · rated {sen['rating']}/5")
                    st.write("Why this senior: " + ", ".join(sen["reasons"]))
                    st.caption(f"Strong on: {sen['strengths']}")
                    st.caption(f"Card {ss.card + 1} of {len(r['seniors'])} · match score {sen['score']}")
                    b1, b2 = st.columns(2)
                    if b1.button("Skip", width="stretch"):
                        ss.skipped.append(sen["id"])
                        ss.card += 1
                        st.rerun()
                    if b2.button("Pick", type="primary", width="stretch"):
                        ss.plan = orc.plan(junior_name, sen, info, ss.question)
                        ss.plan["senior"] = sen
                        ss.trace = ss.trace + ss.plan["trace"]
                        st.rerun()
            else:
                st.write("You've seen the top matches.")
                if st.button("Show more seniors"):
                    seen = ss.skipped
                    r["seniors"] = orc.more_seniors(ss.question, info, seen)
                    ss.card = 0
                    st.rerun()

        # ---- Meeting plan from the Coordination agent ----
        if ss.plan:
            p = ss.plan
            st.success(f"Matched with {p['senior']['name']}!")
            if p.get("warning"):
                st.warning(p["warning"])
            with st.container(border=True):
                st.markdown(f"**When:** {p['when_text']}  \n**Where:** {p['spot']}")
                if p["other_slots"]:
                    st.caption("Other free slots: " + "; ".join(p["other_slots"]))
                st.markdown("**Message drafted for you** (copy it with the icon on the right):")
                st.code(p["message"], language=None, wrap_lines=True)
                if p["wa_link"]:
                    st.link_button("Open in WhatsApp", p["wa_link"])
            st.button("Start over", on_click=start_over)

# ---------------- Pass it on ----------------
with tab_items:
    st.subheader("Pass it on")
    st.caption("Seniors: snap a photo of a book, drafter, lab coat or cycle. The AI writes the listing and finds juniors who need it.")
    note = st.text_input("A line about it (optional)", placeholder="e.g. Mini drafter, used one semester")
    photo = st.file_uploader("Photo", type=["jpg", "jpeg", "png"])
    if st.button("Create listing", type="primary") and (note or photo):
        with st.spinner("Listing agent at work..."):
            data = photo.getvalue() if photo else None
            mime = photo.type if photo else "image/jpeg"
            ss.listing = orc.handle_listing(note, data, mime)
        ss.trace = ss.listing["trace"]
    if ss.listing:
        item = ss.listing["item"]
        with st.container(border=True):
            st.markdown(f"### {item.get('title')}")
            st.write(f"{item.get('category')} · condition: {item.get('condition')} · "
                     f"{item.get('suggested_credits')} credits suggested")
            if item.get("course"):
                st.caption(f"Useful for: {item['course']}")
            st.write(item.get("description", ""))
        buyers = ss.listing["buyers"]
        if buyers:
            st.markdown("**Juniors looking for this:**")
            for b in buyers:
                st.write(f"- {b['junior_name']}: wants \"{b['item']}\" (up to {b['max_credits']} credits)")
        else:
            st.caption("No junior has asked for this yet. It stays listed until someone does.")

# ---------------- Senior inbox (the flywheel) ----------------
with tab_inbox:
    st.subheader("Senior inbox")
    st.caption("Questions the AI couldn't answer. A senior answers once, and every future junior gets it instantly.")
    if ss.flash:
        st.success(ss.flash)
        ss.flash = None
    if not orc.pending:
        st.write("Nothing waiting. Ask something the knowledge base doesn't cover, and it will appear here.")
    for i, p in enumerate(list(orc.pending)):
        with st.container(border=True):
            st.markdown(f"**{p['question']}**")
            st.caption(f"Course: {p.get('course') or 'General'}")
            names = orc.seniors["name"].tolist() if not orc.seniors.empty else ["Senior"]
            who = st.selectbox("Answering as", names, key=f"who{i}")
            advice = st.text_area("Your advice", key=f"adv{i}", height=80)
            if st.button("Approve and add to knowledge base", key=f"ok{i}") and advice.strip():
                sen = orc.seniors[orc.seniors["name"] == who].iloc[0] if not orc.seniors.empty else {"year": ""}
                row = orc.add_to_kb(p["question"], advice, who, sen["year"], p.get("course"), p.get("topic"))
                orc.pending.remove(p)
                ss.flash = f"Saved as tip #{row['id']}. Ask the same question on the Ask tab: it's now answered instantly."
                st.rerun()

# ---------------- Insights (survey + unmet needs) ----------------
SURVEY_DIR = Path(__file__).resolve().parent / "data" / "survey"


@st.cache_data
def load_survey():
    real = SURVEY_DIR / "survey_real_anonymised.csv"
    combined = SURVEY_DIR / "survey_combined.csv"
    return (pd.read_csv(real) if real.exists() else pd.DataFrame(),
            pd.read_csv(combined) if combined.exists() else pd.DataFrame())


SURVEY_OPTIONS = {
    "help_with": ["FFCS: choosing slots, courses or timetable", "Exam prep (CAT / FAT, past papers, what to focus on)",
                  "Projects, clubs or hackathons", "Hostel / mess / campus life",
                  "Internships, coding prep or career direction",
                  "Buying things I need (books, EG kit, lab coat, calculator, cycle, etc.)",
                  "Lab work, records or viva", "Understanding a subject / concept"],
    "bought_new": ["Lab coat", "Scientific calculator", "Mattress / bucket / hostel essentials",
                   "Engineering Graphics / drafting kit", "Textbooks", "Cycle"],
}
SHORT = {"FFCS: choosing slots, courses or timetable": "FFCS",
         "Exam prep (CAT / FAT, past papers, what to focus on)": "Exam prep",
         "Projects, clubs or hackathons": "Projects & clubs", "Hostel / mess / campus life": "Hostel & campus",
         "Internships, coding prep or career direction": "Internships & careers",
         "Buying things I need (books, EG kit, lab coat, calculator, cycle, etc.)": "Buying things",
         "Lab work, records or viva": "Labs", "Understanding a subject / concept": "Concepts",
         "Mattress / bucket / hostel essentials": "Hostel essentials",
         "Engineering Graphics / drafting kit": "EG kit"}


def count_options(series, col):
    return pd.Series({SHORT.get(o, o): int(series.fillna("").str.contains(o, regex=False).sum())
                      for o in SURVEY_OPTIONS[col]}).sort_values(ascending=False)


def ranked_bars(counts):
    # Horizontal bars, biggest at the top, with the count printed on each bar.
    data = counts.rename_axis("option").reset_index(name="first_years")
    base = alt.Chart(data).encode(
        y=alt.Y("option:N", sort="-x", title=None, axis=alt.Axis(labelOverlap=False, labelLimit=220)),
        x=alt.X("first_years:Q", title="First years", axis=alt.Axis(tickMinStep=1)),
    )
    bars = base.mark_bar(color="#1f6feb")
    labels = base.mark_text(align="left", dx=4).encode(text="first_years:Q")
    st.altair_chart((bars + labels).properties(height=36 * len(data)), width="stretch")


with tab_insights:
    st.subheader("Why PassItOn")
    real_df, combined_df = load_survey()
    if real_df.empty:
        st.write("No survey data found in data/survey/.")
    else:
        use_sim = st.toggle("Include simulated responses", value=False,
                            help="Simulated rows are generated from the real answer patterns, for testing only. "
                                 "Quote only real numbers in the pitch.")
        df = combined_df if use_sim else real_df
        juniors = df[df["year"] == "1st year"]
        n = len(juniors)
        if use_sim:
            st.warning(f"Showing {len(real_df)} real + {len(df) - len(real_df)} SIMULATED responses. "
                       "Do not quote these numbers as survey results.")
        else:
            st.caption(f"Real responses from VIT students: {len(df)} ({n} first years, {len(df) - n} seniors), "
                       "collected 21 to 22 Oct 2026.")
        often = juniors["help_freq"].isin(["2–5 times", "More than 5 times"]).sum()
        useful = (juniors["usefulness_1to5"] >= 4).sum()
        free = (juniors["would_pay"] == "No, it should be free").sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Needed a senior 2+ times last month", f"{often}/{n} ({often / n:.0%})")
        c2.metric("Rated the idea 4 or 5 out of 5", f"{useful}/{n} ({useful / n:.0%})")
        c3.metric("Want senior help to be free", f"{free}/{n} ({free / n:.0%})")
        st.markdown("**What first years needed help with** (number of first years)")
        ranked_bars(count_options(juniors["help_with"], "help_with"))
        st.markdown("**What they bought new that a senior could have passed on**")
        ranked_bars(count_options(juniors["bought_new"], "bought_new"))
        st.markdown(f"**How easy it was to find the right senior** (1 = very hard, average "
                    f"{juniors['ease_finding_senior_1to5'].mean():.1f})")
        st.bar_chart(juniors["ease_finding_senior_1to5"].value_counts().reindex([1, 2, 3, 4, 5], fill_value=0))
        quotes = [q for q in real_df["frustration"].dropna().astype(str) if q.strip()]
        if quotes:
            st.markdown("**In their words** (real, anonymous)")
            for q in quotes[:6]:
                st.markdown(f"> {q}")

    st.divider()
    st.subheader("Unmet needs right now")
    st.caption("Questions the AI handed off, grouped by course: what seniors should write tips about next.")
    needs = orc.unmet_needs()
    if needs.empty:
        st.write("None yet. Ask something the knowledge base doesn't cover.")
    else:
        st.dataframe(needs, width="stretch", hide_index=True)

# ---------------- Under the hood ----------------
with tab_hood:
    st.subheader("Under the hood")
    st.caption("Every agent step for your last action, so you can see exactly what the AI did.")
    if ss.trace:
        st.dataframe(pd.DataFrame(ss.trace), width="stretch", hide_index=True)
    else:
        st.write("Ask a question first.")
    with st.expander("The agents"):
        st.markdown(
            "- **Safety**: blocks cheating and abuse before anything runs.\n"
            "- **Intake**: turns the question into course, type and urgency.\n"
            "- **Ask**: retrieves senior tips and answers only from them; hands off when not confident.\n"
            "- **Match**: ranks seniors by course done, topic fit, rating and response rate.\n"
            "- **Coordination**: picks a slot and campus spot, drafts the message.\n"
            "- **Listing**: photo to listing, matched to juniors' requests.\n"
            "- **Insights**: groups unanswered questions by course (Insights tab).\n"
            "- **Orchestrator**: runs them in order, max 6 steps, and records this trace."
        )
    with st.expander(f"Knowledge base ({len(orc.kb)} tips)"):
        st.dataframe(orc.kb, width="stretch", hide_index=True)
    with st.expander(f"Seniors ({len(orc.seniors)})"):
        st.dataframe(orc.seniors, width="stretch", hide_index=True)

# Stats go last so they include whatever just happened above.
with st.sidebar:
    st.divider()
    s = orc.stats
    c1, c2 = st.columns(2)
    c1.metric("Questions", s["questions"])
    c2.metric("Answered by AI", s["answered_by_ai"])
    c1.metric("Sent to seniors", s["handed_off"])
    c2.metric("Tips in knowledge base", len(orc.kb))
