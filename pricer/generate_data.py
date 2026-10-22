"""Synthetic booking history for a community venue (stand-in for real Night Office data)."""
import numpy as np, pandas as pd
from pathlib import Path

SPACES = {"hall": 120, "studio": 60, "meeting_room": 35, "desk": 12}  # base £/hour
SEGMENTS = ["community", "nonprofit", "startup", "company"]
OUT = Path(__file__).parent / "data" / "bookings.csv"

def generate(n=4000, seed=7):
    r = np.random.default_rng(seed)
    space = r.choice(list(SPACES), n, p=[.25, .25, .3, .2])
    seg = r.choice(SEGMENTS, n, p=[.35, .2, .2, .25])
    dow = r.integers(0, 7, n); hour = r.integers(8, 22, n)
    hours = r.choice([1, 2, 3, 4, 6, 8], n)
    lead = r.integers(0, 60, n); repeat = r.poisson(1.5, n)
    attendees = r.integers(2, 150, n)
    base = np.array([SPACES[s] for s in space]) * hours
    peak = ((dow >= 4) | (hour >= 17)).astype(float)
    seg_mult = pd.Series(seg).map({"community": .55, "nonprofit": .6, "startup": .8, "company": 1.0}).values
    price = base * seg_mult * (1 + .25 * peak) * (1 - np.minimum(repeat, 5) * .02) * (1 + .1 * (lead < 3)) \
        * (1 + attendees / 600) * r.normal(1, .05, n)
    return pd.DataFrame(dict(space=space, segment=seg, day_of_week=dow, start_hour=hour, hours=hours,
                             lead_days=lead, repeat_bookings=repeat, attendees=attendees, price=price.round(2)))

if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    df = generate(); df.to_csv(OUT, index=False)
    print(f"wrote {len(df)} bookings to {OUT}")
