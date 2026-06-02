#!/bin/bash
cd "$(dirname "$0")"
./venv/bin/python -m uvicorn app:app --reload --port 8000
