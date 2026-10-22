PY=.venv/bin/python
.PHONY: install train demo dashboard pricer-api
install:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
train:
	$(PY) -m pricer.train
demo:
	$(PY) demo.py
dashboard:
	.venv/bin/uvicorn dashboard.app:app --port 8000 --reload
pricer-api:
	.venv/bin/uvicorn pricer.api:app --port 8001
