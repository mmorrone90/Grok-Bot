"""FrontDesk OS control dashboard: uvicorn dashboard.app:app --port 8000"""
import json, time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from shared import db
from concierge.webhook import router
from concierge.bot import handle

app = FastAPI(title="FrontDesk OS")
app.include_router(router)

@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")

@app.get("/api/state")
def state():
    bk = db.rows("select * from bookings order by id desc")
    approved = [b for b in bk if b["status"] == "confirmed"]
    return {
        "bots": db.rows("select * from bots"),
        "activity": db.rows("select * from activity order by id desc limit 50"),
        "approvals": [dict(a, payload=json.loads(a["payload"] or "{}")) for a in db.rows("select * from approvals where status='pending' order by id")],
        "bookings": bk, "tasks": db.rows("select * from tasks order by id desc"), "leads": db.rows("select * from leads order by score desc"),
        "revenue": {"confirmed": sum(b["quoted_price"] for b in approved), "pipeline": sum(b["quoted_price"] for b in bk),
                    "community_gap": sum(b["company_price"] - b["quoted_price"] for b in bk)},
    }

@app.post("/api/bots/{name}/{action}")
def control(name: str, action: str):
    if name not in db.BOTS or action not in ("pause", "resume"):
        raise HTTPException(404)
    db.set_paused(name, action == "pause"); return {"ok": True}

@app.post("/api/approvals/{aid}/{decision}")
def decide(aid: int, decision: str):
    if decision not in ("approve", "reject"):
        raise HTTPException(404)
    a = db.rows("select * from approvals where id=?", aid)
    if not a: raise HTTPException(404)
    status = "approved" if decision == "approve" else "rejected"
    db.execute("update approvals set status=?, decided_at=? where id=?", status, time.time(), aid)
    p = json.loads(a[0]["payload"] or "{}")
    if a[0]["kind"] == "discounted_quote" and "booking_id" in p:
        db.execute("update bookings set status=? where id=?", "confirmed" if status == "approved" else "declined", p["booking_id"])
    db.log(a[0]["bot"], "approval_" + status, a[0]["summary"])
    return {"ok": True, "status": status}

class Msg(BaseModel):
    text: str; sender: str = "+447700900000"

@app.post("/api/simulate")
def simulate(m: Msg):
    return {"reply": handle(m.text, m.sender)}
