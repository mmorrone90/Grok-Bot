"""Small pricing API: uvicorn pricer.api:app --port 8001"""
from fastapi import FastAPI
from pydantic import BaseModel
from .model import quote

app = FastAPI(title="FrontDesk OS Pricer")

class Req(BaseModel):
    space: str = "hall"; segment: str = "community"; day_of_week: int = 4; start_hour: int = 18
    hours: float = 3; lead_days: int = 7; repeat_bookings: int = 0; attendees: int = 40

@app.post("/quote")
def post_quote(r: Req):
    return quote(r.model_dump())
