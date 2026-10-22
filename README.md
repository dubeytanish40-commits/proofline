# Proofline

Every claim, proven before it is published.

Proofline reviews content before publication against an organisation's approved guidelines and facts. Every finding shows a reason and the source it came from, and humans make every final decision.

Built for the Inkloom AI problem statement (We Code Coders hackathon), team Codecrack, solo entry by Tanish Dubey.

## Run it locally

```
python -m venv .venv
.venv\Scripts\activate          (Windows)   |   source .venv/bin/activate   (Mac/Linux)
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

## Run the tests

```
python -m tests.test_engine
```

## Structure

- `app/engine.py`: the review engine (rule-based checks, claim matching, highlighting)
- `app/data/guidelines.json`: sample brand guidelines and rules (each rule has an id and a source)
- `app/data/facts.json`: sample approved facts used to support claims
- `app/main.py`: FastAPI web app
- `app/templates/`: HTML pages
- `tests/`: engine tests

## Status

Version 1 (stage 1): paste text, get cited findings. Login, roles and approval workflow are being added next.

## AI assistance disclosure

An AI assistant (Claude by Anthropic) helped plan and write parts of this code and documentation. The developer reviewed, ran and is responsible for the project. This version uses no external AI service at runtime; AI-assisted checks are planned for Round 3 and will be disclosed here.

## Libraries

FastAPI, Uvicorn, Jinja2, python-multipart.
