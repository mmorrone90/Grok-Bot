"""Local SQLite store (offline fallback for Supabase). Same tables as supabase/schema.sql."""
import json, os, sqlite3, time
from pathlib import Path

DB_PATH = os.getenv("FRONTDESK_DB", str(Path(__file__).resolve().parent.parent / "data" / "frontdesk.db"))
BOTS = ["concierge", "pricer", "triage", "scout"]

SCHEMA = """
create table if not exists bots (name text primary key, paused integer default 0);
create table if not exists activity (id integer primary key autoincrement, ts real, bot text, kind text, summary text, payload text);
create table if not exists approvals (id integer primary key autoincrement, ts real, bot text, kind text, summary text, payload text, status text default 'pending', decided_at real);
create table if not exists bookings (id integer primary key autoincrement, ts real, customer text, space text, date text, hours real, segment text, community_price real, company_price real, quoted_price real, status text default 'quoted');
create table if not exists tasks (id integer primary key autoincrement, ts real, title text, category text, urgency text, owner text, source text, status text default 'open');
create table if not exists leads (id integer primary key autoincrement, ts real, name text, source text, company_number text, score real, reason text, event text, pushed_to text);
"""

def conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    for b in BOTS:
        c.execute("insert or ignore into bots(name) values (?)", (b,))
    c.commit()
    return c

def reset():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn().close()

def insert(table, **row):
    row.setdefault("ts", time.time())
    if "payload" in row and not isinstance(row["payload"], str):
        row["payload"] = json.dumps(row["payload"])
    with conn() as c:
        cur = c.execute(f"insert into {table} ({','.join(row)}) values ({','.join('?'*len(row))})", list(row.values()))
        return cur.lastrowid

def rows(sql, *args):
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]

def execute(sql, *args):
    with conn() as c:
        c.execute(sql, args)

def log(bot, kind, summary, payload=None):
    return insert("activity", bot=bot, kind=kind, summary=summary, payload=payload or {})

def is_paused(bot):
    r = rows("select paused from bots where name=?", bot)
    return bool(r and r[0]["paused"])

def set_paused(bot, paused):
    execute("update bots set paused=? where name=?", int(paused), bot)
    log(bot, "control", f"{bot} {'paused' if paused else 'resumed'} from dashboard")

def request_approval(bot, kind, summary, payload):
    aid = insert("approvals", bot=bot, kind=kind, summary=summary, payload=payload)
    log(bot, "approval_requested", summary, {"approval_id": aid})
    return aid
