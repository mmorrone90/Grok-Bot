#!/usr/bin/env bash
# One-shot: install deps (first run), train pricer, run the end-to-end demo.
set -e; cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
.venv/bin/python -m pricer.train
.venv/bin/python demo.py
