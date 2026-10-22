"""Turn chat messages into front-desk tasks. Rules first, optional LLM hook (LLM_API_URL)."""
import json, os, re, httpx
from shared import db

RULES = [  # (pattern, title, category, urgency, owner)
    (r"\b(broken|not working|leak|fire|flood|smoke|injur)", None, "facilities", "high", "facilities"),
    (r"\bprojector|screen|hdmi|wifi|wi-fi|mic\b", None, "av", "medium", "tech"),
    (r"\bfood|catering|drinks|pizza|alcohol", "Confirm food & drink policy", "catering", "low", "front_desk"),
    (r"\binvoice|refund|pay|receipt", "Handle payment query", "finance", "medium", "finance"),
    (r"\bkey|access|door|lock", "Sort building access", "access", "medium", "front_desk"),
]

def _llm(text):
    url = os.getenv("LLM_API_URL")
    if not url:
        return None
    try:
        r = httpx.post(url, timeout=15, headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY','')}"}, json={
            "model": os.getenv("LLM_MODEL", "default"),
            "messages": [{"role": "user", "content": "Return JSON list of tasks {title,category,urgency,owner} for: " + text}]})
        return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception:
        return None

def tasks_for(text):
    t = text.lower(); out = []
    for pat, title, cat, urg, owner in RULES:
        if re.search(pat, t):
            out.append({"title": title or f"Fix: {text[:60]}", "category": cat, "urgency": urg, "owner": owner})
    seen, uniq = set(), []
    for x in out:
        if x["title"] not in seen: seen.add(x["title"]); uniq.append(x)
    return uniq or (_llm(text) or [])

def booking_tasks(space, attendees, event_type):
    tasks = [{"title": f"Set up chairs in the {space} ({attendees} seats)", "category": "setup", "urgency": "medium", "owner": "front_desk"}]
    if event_type in ("meetup", "hackathon", "talk"):
        tasks.append({"title": "Test projector + Wi-Fi guest network", "category": "av", "urgency": "low", "owner": "tech"})
    return tasks

def create(tasks, source):
    if db.is_paused("triage"):
        db.log("triage", "skipped", "triage paused, tasks not created"); return []
    for t in tasks:
        db.insert("tasks", source=source, **t)
        db.log("triage", "task_created", f"[{t['urgency']}] {t['title']} -> {t['owner']}")
    return tasks

if __name__ == "__main__":
    import sys
    print(json.dumps(create(tasks_for(" ".join(sys.argv[1:]) or "the projector is broken in room 2"), "cli"), indent=2))
