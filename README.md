# Proofline — Explainable content review before publication

Proofline is a hackathon prototype for reviewing draft content against a configured set of brand guidelines, terminology rules, accessibility checks, and an approved-fact library. The system highlights detected issues, explains which configured rule triggered, records a human review decision, and maintains a review event log.

**Important limitation:** Proofline currently uses deterministic pattern and keyword matching over a sample fact library. It does not browse the public web, establish the truth of claims, or call an AI model. A claim marked **Needs evidence** is not necessarily false, and a keyword match to an approved fact is not independent verification. Human review remains required.

## Features implemented

- Responsive web interface for submitting content and reviewing findings.
- Rule-based checks for product spelling, preferred terminology, promotional language, exclamation marks, all-caps wording, sentence length, descriptive link text, and claim patterns.
- Explicit claim evidence states: **Matched approved fact** or **Needs evidence**. The latter is not a verdict of falsity.
- Fact match details include configured record ID, text, source, and validity date.
- SQLite storage for submitted review text, findings, summary, current review status, timestamps, and decisions.
- Human decision workflow: approve, request changes, reject, or reopen a review.
- Append-only event log for submissions and decisions.
- Review history, dashboard counts, and per-review JSON export.
- JSON API and interactive OpenAPI docs at `/docs`.
- Input length validation and HTML-escaped highlighted draft output.
- Unit/regression tests for core rules, persistence and HTTP/API workflows.
- GitHub Actions CI workflow runs all three test suites on pushes and pull requests to `main`.

## Technology stack

- **Backend:** Python, FastAPI, Pydantic
- **Frontend:** Jinja2 templates, HTML, CSS, small amount of vanilla JavaScript
- **Persistence:** SQLite via Python standard library (`sqlite3`)
- **Hosting:** Render (deployment configured outside the repository)
- **Testing:** Python assertion-based regression suites

## Run locally (Windows)

```powershell
cd proofline
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. API documentation is at `http://127.0.0.1:8000/docs`; health check is at `/health`.

## Run locally (macOS/Linux)

```bash
cd proofline
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run tests

Install the test client first with `python -m pip install -r requirements-dev.txt`, then run:

```bash
python -m tests.test_engine
python -m tests.test_storage
python -m tests.test_api
```

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service and database health check |
| `POST` | `/api/reviews` | Analyse and save a draft; JSON body: `{"text":"Draft text"}` |
| `GET` | `/api/reviews?limit=20` | List recent reviews and dashboard counters |
| `GET` | `/api/reviews/{id}` | Read a saved review with findings and event history |
| `POST` | `/api/reviews/{id}/decision` | Record a human decision and note |
| `GET` | `/reviews/{id}/export.json` | Download a review record as JSON |
| `GET` | `/docs` | Interactive OpenAPI documentation |

Example decision request:

```json
{
  "action": "Changes requested",
  "reviewer": "Content Reviewer",
  "note": "Please attach a current source for the percentage claim."
}
```

Allowed actions: `Approved`, `Changes requested`, `Rejected`, `Reopened`.

## Configuration

- `PROOFLINE_DB_PATH` (optional): file path for the SQLite database. Defaults to `proofline.db` in the project root.
- Policy and sample fact data live in `app/data/guidelines.json` and `app/data/facts.json`.
- Each fact can include an ISO `valid_until` date. Expired/invalidly dated facts are not used to support a claim.
- Draft input is limited to 20,000 characters.

## Deployment notes

Build command for Render: `pip install -r requirements.txt`

Start command for Render: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

The application can be redeployed from the connected GitHub repository. **SQLite file durability depends on the hosting filesystem.** If the host's filesystem is ephemeral, review records can be lost on redeploy/restart; use a managed persistent database for production or durable hosted use. The current prototype has no authentication, role-based access control, or multi-user tenancy; reviewer display names are not verified identities. Do not submit sensitive or confidential content.

## What is still planned (not implemented)

- Authentication and role-based permissions
- Managed persistent database for production deployment
- Independent external-source retrieval and evidence provenance verification
- AI-assisted semantic claim extraction, with provider and evaluation disclosures
- File upload, team review assignments, and richer exports

Do not describe planned items as completed features in a submission.

## AI assistance disclosure

An AI assistant helped review and develop parts of the code and documentation. The developer is responsible for understanding, verifying, and presenting the implementation. The running application does not call an external AI model; all checks are deterministic rules and local keyword matching.

## Demo content and facts

The provided fact and guideline files are sample configuration used to demonstrate the workflow. Replace them with reviewed, permissioned, up-to-date sources before using this system for real publication decisions.
