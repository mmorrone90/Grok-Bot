"""End-to-end FrontDesk OS demo, fully offline. Run: make demo  (or python demo.py)"""
import json
from shared import db
from pricer.model import MODEL, train
from concierge.bot import handle
from dashboard.app import decide

MSG = "can I book the hall Friday for a coding meetup?"
db.reset()
if not MODEL.exists():
    train()
print(f"\n[WhatsApp] guest: {MSG}")
print(f"[concierge] {handle(MSG)}")
q = db.rows("select payload from activity where kind='quote' order by id desc limit 1")[0]
print(f"[pricer] {json.loads(q['payload'])['explanation']}")
ap = db.rows("select * from approvals where status='pending' order by id")
print("[dashboard] approval queue:"); [print(f"   #{a['id']} {a['bot']}: {a['summary']}") for a in ap]
quote_ap = next(a for a in ap if a["kind"] == "discounted_quote")
decide(quote_ap["id"], "approve"); print(f"[dashboard] staff approved #{quote_ap['id']} -> booking confirmed")
print("[triage] tasks:"); [print(f"   [{t['urgency']}] {t['title']} -> {t['owner']}") for t in db.rows("select * from tasks")]
print("[scout] suggested sponsors:"); [print(f"   {l['name']} ({l['score']:.0f}) {l['reason']}") for l in db.rows("select * from leads order by score desc")]
print("\nOpen the dashboard with `make dashboard` (or .venv/bin/uvicorn dashboard.app:app --port 8000) -> http://localhost:8000")
