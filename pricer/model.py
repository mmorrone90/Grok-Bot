"""Train + explain the LightGBM pricing model."""
import lightgbm as lgb, numpy as np, pandas as pd
from pathlib import Path
from .generate_data import generate, OUT, SPACES, SEGMENTS

MODEL = Path(__file__).parent / "model.txt"
FEATURES = ["space", "segment", "day_of_week", "start_hour", "hours", "lead_days", "repeat_bookings", "attendees"]
CATS = {"space": list(SPACES), "segment": SEGMENTS}
LABELS = {"space": "the space", "segment": "customer type", "day_of_week": "day of week", "start_hour": "start time",
          "hours": "length of booking", "lead_days": "how far ahead it's booked", "repeat_bookings": "booking history",
          "attendees": "group size"}
DAYS = "Mon Tue Wed Thu Fri Sat Sun".split()

def _prep(df):
    X = df[FEATURES].copy()
    for c, cats in CATS.items():
        X[c] = pd.Categorical(X[c], categories=cats)
    return X

def train(verbose=True):
    df = pd.read_csv(OUT) if OUT.exists() else generate()
    X, y = _prep(df), df["price"]
    n = int(len(df) * .8)
    m = lgb.LGBMRegressor(n_estimators=300, learning_rate=.05, num_leaves=31, verbose=-1)
    m.fit(X[:n], y[:n])
    mape = float(np.mean(np.abs(m.predict(X[n:]) - y[n:]) / y[n:]))
    m.booster_.save_model(str(MODEL))
    if verbose:
        print(f"trained on {n} bookings, holdout MAPE {mape:.1%}, saved {MODEL.name}")
    return mape

_booster = None
def _model():
    global _booster
    if _booster is None:
        if not MODEL.exists():
            train(verbose=False)
        _booster = lgb.Booster(model_file=str(MODEL))
    return _booster

def predict(req):
    b = _model(); X = _prep(pd.DataFrame([req]))
    return float(b.predict(X)[0]), b.predict(X, pred_contrib=True)[0]

def quote(req):
    """Return community vs company price and a plain-English explanation."""
    req = {**{"day_of_week": 4, "start_hour": 18, "hours": 3, "lead_days": 7, "repeat_bookings": 0, "attendees": 40}, **req}
    price, contrib = predict(req)
    company, _ = predict({**req, "segment": "company"})
    parts = sorted(zip(FEATURES, contrib[:-1]), key=lambda t: -abs(t[1]))[:3]
    why = [f"{LABELS[f]} {'adds' if v > 0 else 'takes off'} £{abs(v):.0f}" for f, v in parts]
    discount = 1 - price / company if company else 0
    seg = req["segment"]
    text = (f"£{price:.0f} for {req['hours']:g}h in the {req['space'].replace('_', ' ')} on {DAYS[req['day_of_week']]} "
            f"({seg} rate). The company rate would be £{company:.0f}, so that's {discount:.0%} off. "
            f"Biggest factors: {'; '.join(why)}.")
    return {"segment": seg, "quoted_price": round(price, 2), "company_price": round(company, 2),
            "community_discount": round(discount, 3), "explanation": text,
            "contributions": {f: round(float(v), 2) for f, v in zip(FEATURES, contrib[:-1])},
            "baseline": round(float(contrib[-1]), 2), "request": req}
