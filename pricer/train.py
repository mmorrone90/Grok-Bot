from pricer.generate_data import generate, OUT
from pricer.model import train
OUT.parent.mkdir(exist_ok=True); generate().to_csv(OUT, index=False); print(f"generated {OUT}")
train()
