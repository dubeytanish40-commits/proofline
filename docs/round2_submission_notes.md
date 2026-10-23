# Proofline - Round 2 submission notes

## Project summary

Proofline is a content-review prototype that helps a human reviewer identify possible publication risks before a draft is published. It checks text against a configurable sample policy set covering terminology, brand spelling, promotional language, readability, accessibility wording, and claims that need evidence. Findings show the triggering rule and configured source. Each review is stored with its scan summary, findings, reviewer decision, and decision history.

## Implemented in this build

- Responsive web interface for draft submission and highlighted findings.
- FastAPI backend with validation and JSON endpoints.
- Deterministic review engine backed by editable JSON guideline and sample fact files.
- Claim results distinguish a keyword match to a configured fact from a claim that needs evidence. Missing evidence is not classified as false.
- SQLite storage for saved reviews, statuses, timestamps, and reviewer-decision events.
- Human workflow with approve, request changes, reject, and reopen decisions.
- Review-history dashboard, summary counters, and JSON export.
- OpenAPI/Swagger documentation at `/docs` and health endpoint at `/health`.
- Regression tests for engine, persistence, and web/API workflows; GitHub Actions runs them on pushes and pull requests.
- Render deployment configuration with a start command using the assigned `$PORT`.

## Technology and implementation

- Python 3.11+ compatible application code
- FastAPI and Pydantic for HTTP routes, validation, and OpenAPI
- Jinja2 templates, HTML, CSS, and vanilla JavaScript for the browser interface
- SQLite / `sqlite3` for local review persistence and event records
- JSON files for sample rules, guidelines, and approved-fact records
- Python test modules and GitHub Actions CI
- Render for the hosted demo

## Round 2 build progress / changes from the initial single-page version

The starting prototype accepted a text draft and displayed rule-based findings. This build adds stored review records, a dashboard and history page, reviewer decisions with notes, a review event log, per-review JSON export, API endpoints, input validation, clearer evidence statuses, automated regression tests, and CI. The implementation remains deterministic and transparent; no external AI service or public-web fact-checking service is called by the running app.

## Known limits to disclose

- The guideline and fact files are example configuration for demonstrating the workflow, not authoritative real-world data.
- A keyword match indicates a match to the configured fact text; it does not independently prove the claim.
- The public prototype has no authentication, permissions, or tenant separation. Reviewer names are labels, not verified identities. Do not use it for confidential drafts.
- SQLite persistence depends on the hosting filesystem. On an ephemeral host, records can be lost on restart or redeployment.
- There is no external-source retrieval, LLM semantic analysis, team assignment, or production-grade security in this version.

## Three proposed Round 3 improvements

1. **Secure collaboration and durable data:** implement sign-in, roles, reviewer assignments, audit access controls, and a managed database with documented retention and migration behaviour.
2. **Evidence retrieval and provenance:** connect a curated source library or approved source APIs, preserve source URLs and retrieval timestamps, display exact supporting passages, handle expired sources, and separate “supported”, “contradicted”, and “not yet verified” using explicit evidence criteria.
3. **Evaluated AI-assisted review:** add optional semantic claim extraction and context-aware suggested rewrites, compare outputs against a labelled evaluation set, measure precision/recall and reviewer corrections, disclose the model/provider, and keep all publication decisions human-approved.

## Demo links

- Live application: https://proofline-d6lm.onrender.com
- Source repository: https://github.com/dubeytanish40-commits/proofline
- Interactive API documentation after the upgraded build is deployed: append `/docs` to the live app URL.

Before submission, verify the deployed version, ensure the repository contains the matching source, and replace these links if the organizer requires a different format. Do not describe planned Round 3 work as already implemented.
