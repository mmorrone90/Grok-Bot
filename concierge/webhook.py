"""WhatsApp Cloud API + Chatwoot webhooks (mounted by the dashboard app)."""
import os
from fastapi import APIRouter, Request, Response
from .bot import handle

router = APIRouter()

@router.get("/webhook/whatsapp")
def verify(request: Request):
    p = request.query_params
    if p.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN", "change-me"):
        return Response(p.get("hub.challenge", ""))
    return Response(status_code=403)

@router.post("/webhook/whatsapp")
async def whatsapp(request: Request):
    body = await request.json(); replies = []
    for e in body.get("entry", []):
        for c in e.get("changes", []):
            for m in c.get("value", {}).get("messages", []):
                if m.get("type") == "text":
                    replies.append(handle(m["text"]["body"], m.get("from", "unknown")))
    return {"replies": replies}

@router.post("/webhook/chatwoot")
async def chatwoot(request: Request):
    b = await request.json()
    if b.get("event") == "message_created" and b.get("message_type") == "incoming":
        return {"content": handle(b.get("content", ""), str(b.get("sender", {}).get("phone_number") or b.get("sender", {}).get("id")))}
    return {"ignored": True}
