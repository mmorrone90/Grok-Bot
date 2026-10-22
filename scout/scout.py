"""Sponsor CRM builder: Luma + Devpost + Companies House -> scored leads -> Twenty CRM (or CSV in mock mode)."""
import csv, json, os, httpx
from pathlib import Path
from shared import db

HERE = Path(__file__).parent; SAMPLE = HERE / "sample_data"
TECH_SIC = {"62012", "62090", "62020", "63110", "64191", "66190", "35140"}

def _load(name):
    return json.loads((SAMPLE / name).read_text())

def luma_companies(path=None):
    d = json.loads(Path(path).read_text()) if path else _load("luma_event.json")
    ev = d["event"]
    names = [s["name"] for s in ev.get("sponsors", [])] + d.get("guests_companies", [])
    return {n: {"luma": True, "already_sponsor": n in [s["name"] for s in ev.get("sponsors", [])]} for n in names}

def devpost_orgs():
    if os.getenv("DEVPOST_ENABLED") == "1":
        try:
            r = httpx.get("https://devpost.com/api/hackathons", params={"search": "London"}, timeout=10)
            return r.json()["hackathons"]
        except Exception:
            pass
    return _load("devpost_hackathons.json")["hackathons"]

def companies_house(name):
    key = os.getenv("COMPANIES_HOUSE_API_KEY")
    if key:
        try:
            r = httpx.get("https://api.company-information.service.gov.uk/search/companies", params={"q": name, "items_per_page": 1}, auth=(key, ""), timeout=10)
            it = r.json()["items"][0]
            return {"company_number": it["company_number"], "company_status": it["company_status"], "sic_codes": it.get("sic_codes", []),
                    "registered_office_address": {"locality": it.get("address", {}).get("locality", "")}}
        except Exception:
            pass
    return _load("companies_house.json").get(name, {})

def score(name, info, event_theme):
    s, why = 0.0, []
    if info.get("luma"): s += 25; why.append("attends London community events")
    if info.get("devpost"): s += 30; why.append(f"has run a hackathon ({info['devpost']})")
    ch = info.get("ch", {})
    if ch.get("company_status") == "active": s += 15; why.append("active UK company")
    if "London" in ch.get("registered_office_address", {}).get("locality", ""): s += 10; why.append("London HQ")
    if TECH_SIC & set(ch.get("sic_codes", [])): s += 15; why.append("tech/fintech SIC code")
    if event_theme and any(event_theme in t.lower() for t in info.get("themes", [])): s += 10; why.append(f"themes match '{event_theme}'")
    if info.get("already_sponsor"): s -= 40; why.append("already a sponsor here")
    return s, ", ".join(why)

def push_twenty(lead):
    url, key = os.getenv("TWENTY_API_URL"), os.getenv("TWENTY_API_KEY")
    if not (url and key):
        return "csv"
    try:
        httpx.post(f"{url.rstrip('/')}/rest/companies", headers={"Authorization": f"Bearer {key}"}, timeout=10,
                   json={"name": lead["name"], "tagline": lead["reason"][:200]}).raise_for_status()
        return "twenty"
    except Exception:
        return "csv"

def run(event="coding meetup", theme="", top=3):
    if db.is_paused("scout"):
        db.log("scout", "skipped", "scout paused"); return []
    cos = luma_companies()
    for h in devpost_orgs():
        o = cos.setdefault(h["organization_name"], {})
        o["devpost"] = h["title"]; o["themes"] = [t["name"] for t in h.get("themes", [])]
    leads = []
    for name, info in cos.items():
        info["ch"] = companies_house(name)
        s, why = score(name, info, theme)
        leads.append({"name": name, "source": "+".join(k for k in ("luma", "devpost") if info.get(k)),
                      "company_number": info["ch"].get("company_number") or "", "score": s, "reason": why, "event": event})
    leads.sort(key=lambda l: -l["score"]); best = leads[:top]
    out = HERE / "out"; out.mkdir(exist_ok=True)
    with open(out / "sponsor_leads.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(leads[0])); w.writeheader(); w.writerows(leads)
    for l in best:
        l["pushed_to"] = push_twenty(l)
        db.insert("leads", **l)
        db.log("scout", "lead", f"{l['name']} ({l['score']:.0f}): {l['reason']}")
        db.request_approval("scout", "sponsor_outreach", f"Email {l['name']} about sponsoring '{event}'",
                            {"lead": l, "draft": f"Hi {l['name']} team, we're hosting a {event} at Night Office and think you'd be a great fit as a sponsor..."})
    return best

if __name__ == "__main__":
    for l in run(): print(f"{l['score']:>4.0f}  {l['name']:<16} {l['reason']}")
