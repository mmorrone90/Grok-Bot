# Front Desk & Revenue (Hackathon 2026-10-22, Track 5)

Answer inbound in chat, price bookings fairly, and find sponsors.

## What to build
- **Pricing engine** trained on a venue's real booking history. It quotes each request and explains the difference between community and company pricing (LightGBM).
- **Inbound bot** that replies in WhatsApp, qualifies the request, then books a call (Cal.com) or sends the quote.
- **Front desk** that turns every chat message into a task with an owner and a priority, and logs what it couldn't handle.
- **Sponsor CRM** that scrapes Luma event hosts and Devpost organisers, sizes them with Companies House and drafts the email. It runs in Zero or Twenty.

## Winning demo
A chat request comes in, gets qualified, priced from past bookings and quoted, then matched to a likely sponsor with a drafted email.

## Stack
Zero, Supabase, Grok Bot, Cursor. Starters: Chatwoot, Twenty, Frappe CRM, Cal.com, LightGBM.

## Data
- Luma event JSON: `https://api.lu.ma/event/get?event_api_id=...`
- Devpost: `https://devpost.com/api/hackathons?status[]=upcoming&search=london`
- Companies House: free API key
- BuilderBase discovery API
- Night Office redacted booking history (ask on the night)

## Judging
Prices that make sense on held-out bookings, fast and correct replies, sponsor matches that fit, and whether a venue would really use it.

## License
MIT
