"""Coordination agent: turn a match into an actual meeting.

Tools it uses: the senior's free slots, the list of campus spots, the clock.
It picks the earliest slot that fits, a spot, and drafts the WhatsApp message.
"""
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def next_slots(availability, now=None, min_gap_hours=2):
    """'Mon 17:00;Thu 18:30' -> upcoming datetimes, soonest first."""
    now = now or datetime.now(IST)
    slots = []
    for part in str(availability).split(";"):
        part = part.strip()
        if not part:
            continue
        try:
            day, hhmm = part.split()
            weekday = DAYS.index(day[:3].lower())
            hour, minute = [int(x) for x in hhmm.split(":")]
        except Exception:
            continue
        days_ahead = (weekday - now.weekday()) % 7
        when = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if when < now + timedelta(hours=min_gap_hours):
            when += timedelta(days=7)
        slots.append(when)
    return sorted(slots)


def plan_meeting(junior_name, senior, intake_result, question, places, llm=None, now=None):
    urgent = intake_result.get("urgency") == "high"
    slots = next_slots(senior.get("availability", ""), now=now, min_gap_hours=1 if urgent else 2)
    slot = slots[0] if slots else None
    spot = senior.get("preferred_spot") if senior.get("preferred_spot") in places else (places[0] if places else "Library")
    when_text = slot.strftime("%a %d %b, %I:%M %p") if slot else "a time that suits you"
    topic = intake_result.get("topic") or question[:60]
    course = intake_result.get("course") or "this"

    message = None
    if llm is not None and llm.online:
        message = llm.text(
            f"Write a short, polite WhatsApp message (max 4 lines, no emojis) from a first-year VIT student "
            f"named {junior_name} to a senior named {senior['name']}, asking for 20 minutes of help with "
            f"'{topic}' in {course}, proposing {when_text} at {spot}. Mention they found the senior on PassItOn. "
            f"Return only the message."
        )
    if not message:
        about = f"with {course}" if intake_result.get("course") else "with a question"
        message = (
            f"Hi {senior['name']}! I'm {junior_name}, a first year. I found you on PassItOn. "
            f"Could you spare 20 minutes to help me {about}? My question: \"{question.strip()}\" "
            f"Would {when_text} at {spot} work? Thanks a lot!"
        )
    message = message.strip()
    phone = str(senior.get("phone", "") or "").strip()
    wa_link = f"https://wa.me/{phone}?text={quote(message)}" if phone and phone.lower() != "nan" else None
    warning = None
    if urgent and slot and (slot - (now or datetime.now(IST))).total_seconds() > 48 * 3600:
        warning = f"{senior['name']}'s next free slot is more than 2 days away. If your exam is sooner, go back and pick another senior."
    return {
        "warning": warning,
        "slot": slot.isoformat() if slot else None,
        "when_text": when_text,
        "spot": spot,
        "message": message,
        "wa_link": wa_link,
        "other_slots": [s.strftime("%a %d %b, %I:%M %p") for s in slots[1:3]],
    }
