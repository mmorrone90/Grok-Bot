"""Concierge: inbound WhatsApp bot. Answers FAQs, spots booking requests, hands off when unsure."""
import os, re, httpx
from datetime import date, timedelta
from shared import db
from pricer.model import quote
from triage import triage
from scout import scout

FAQ = {
    r"open|hours|opening": "We're open Mon-Fri 8am-11pm and weekends 10am-10pm.",
    r"wifi|wi-fi|internet": "Guest Wi-Fi is 'NightOffice-Guest', password at the front desk.",
    r"where|address|location": "We're at Night Office, London. Step-free entrance on the side street.",
    r"food|drink|catering": "You're welcome to bring food; no glass on the roof terrace please.",
}
SPACES = {"hall": "hall", "studio": "studio", "meeting room": "meeting_room", "room": "meeting_room", "desk": "desk"}
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
EVENTS = ["meetup", "hackathon", "talk", "workshop", "party", "offsite"]
COMMUNITY_WORDS = ["meetup", "community", "charity", "nonprofit", "non-profit", "volunteer", "hackathon"]

def parse_booking(text):
    t = text.lower()
    if not re.search(r"\bbook|reserve|hire|rent\b", t):
        return None
    space = next((v for k, v in SPACES.items() if k in t), "meeting_room")
    dow = next((i for i, d in enumerate(DAYS) if d in t), 4)
    m = re.search(r"(\d+)\s*(people|attendees|guests|pax)", t)
    ev = next((e for e in EVENTS if e in t), "event")
    seg = "community" if any(w in t for w in COMMUNITY_WORDS) else ("company" if re.search(r"offsite|company|corporate|team", t) else "startup")
    d = date.today(); d += timedelta(days=(dow - d.weekday()) % 7 or 7)
    return {"space": space, "day_of_week": dow, "date": d.isoformat(), "attendees": int(m.group(1)) if m else 40,
            "event_type": ev, "segment": seg, "hours": 3, "start_hour": 18}

def send_whatsapp(to, text):
    tok, pid = os.getenv("WHATSAPP_TOKEN"), os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    if not (tok and pid):
        return "mock"
    httpx.post(f"https://graph.facebook.com/v20.0/{pid}/messages", headers={"Authorization": f"Bearer {tok}"}, timeout=10,
               json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}})
    return "sent"

def handoff(sender, text):
    db.log("concierge", "handoff", f"Handed {sender} to a human: '{text[:60]}'")
    url = os.getenv("CHATWOOT_URL")
    if url:
        pass  # In live mode Chatwoot already holds the conversation; we'd toggle its status to 'open' via the API.
    return "Good question, let me get someone from the team to help. They'll reply here shortly."

def handle(text, sender="+447700900000"):
    """Process one inbound message end to end. Returns the reply sent to the guest."""
    if db.is_paused("concierge"):
        db.log("concierge", "skipped", "concierge paused, message left for staff"); return None
    db.log("concierge", "inbound", f"{sender}: {text}")
    b = parse_booking(text)
    if b:
        if db.is_paused("pricer"):
            reply = handoff(sender, text)
        else:
            q = quote({k: b[k] for k in ("space", "segment", "day_of_week", "start_hour", "hours", "attendees")})
            bid = db.insert("bookings", customer=sender, space=b["space"], date=b["date"], hours=b["hours"], segment=b["segment"],
                            community_price=q["quoted_price"], company_price=q["company_price"], quoted_price=q["quoted_price"])
            db.log("pricer", "quote", q["explanation"], q)
            if q["community_discount"] > 0.15:
                db.request_approval("pricer", "discounted_quote", f"{b['segment'].title()} rate £{q['quoted_price']:.0f} "
                                    f"({q['community_discount']:.0%} off £{q['company_price']:.0f}) for {sender}",
                                    {"booking_id": bid, "quote": q, "sender": sender})
                reply = (f"Yes, the {b['space'].replace('_',' ')} looks free {DAYS[b['day_of_week']].title()} {b['date']}! "
                         f"For a {b['event_type']} we offer our community rate, around £{q['quoted_price']:.0f} for 3 hours. "
                         "A team member will confirm the quote in a few minutes.")
            else:
                reply = f"The {b['space'].replace('_',' ')} is free on {b['date']}. {q['explanation']} Reply YES to book."
            triage.create(triage.booking_tasks(b["space"], b["attendees"], b["event_type"]), f"booking:{bid}")
            scout.run(event=f"{b['event_type']} on {b['date']}")
    else:
        hit = next((a for p, a in FAQ.items() if re.search(p, text.lower())), None)
        tasks = triage.tasks_for(text)
        if tasks:
            triage.create(tasks, f"chat:{sender}")
            reply = "Thanks for letting us know, I've logged it with the team."
        else:
            reply = hit or handoff(sender, text)
    db.log("concierge", "reply", f"-> {sender}: {reply}", {"delivery": send_whatsapp(sender, reply)})
    return reply

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(handle(" ".join(sys.argv[1:])))
    else:
        print("Concierge mock WhatsApp. Type a message (Ctrl-D to quit).")
        for line in sys.stdin:
            print("bot>", handle(line.strip()))
