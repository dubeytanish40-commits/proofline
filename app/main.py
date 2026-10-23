"""Proofline FastAPI web application and JSON API."""
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.engine import MAX_INPUT_CHARS, highlight_html, review_text
from app.storage import create_review, dashboard_stats, get_review, init_db, list_reviews, record_decision

BASE = Path(__file__).parent
app = FastAPI(
    title="Proofline API",
    description=("A transparent, rules-based content review prototype. Findings identify policy matches "
                 "and claims needing evidence; they are not independent fact verification."),
    version="2.0.0",
)
templates = Jinja2Templates(directory=str(BASE / "templates"))
SAMPLE = (
    "Our app is the #1 fastest in India, loved by everyone! "
    "We utilize cutting-edge AI-powered tools to leverage synergies. "
    "Click here to learn more!! "
    "Proof Line loads 40% faster than version 1."
)


class ReviewCreate(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS, description="Draft content to review")


class DecisionCreate(BaseModel):
    action: Literal["Approved", "Changes requested", "Rejected", "Reopened"]
    reviewer: str = Field(default="Reviewer", max_length=80)
    note: str = Field(default="", max_length=2000)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse, name="home")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "sample": SAMPLE, "text": "", "error": None,
        "stats": dashboard_stats(), "recent": list_reviews(5),
        "max_chars": MAX_INPUT_CHARS,
    })


@app.post("/review", response_class=HTMLResponse)
def submit_review(request: Request, text: str = Form(...)):
    if not text.strip():
        return templates.TemplateResponse(request, "index.html", {
            "sample": SAMPLE, "text": text, "error": "Please paste some content before reviewing.",
            "stats": dashboard_stats(), "recent": list_reviews(5), "max_chars": MAX_INPUT_CHARS,
        }, status_code=400)
    if len(text) > MAX_INPUT_CHARS:
        return templates.TemplateResponse(request, "index.html", {
            "sample": SAMPLE, "text": text[:MAX_INPUT_CHARS],
            "error": f"This draft exceeds the {MAX_INPUT_CHARS:,}-character limit.",
            "stats": dashboard_stats(), "recent": list_reviews(5), "max_chars": MAX_INPUT_CHARS,
        }, status_code=413)
    result = review_text(text)
    review = create_review(text, result)
    return RedirectResponse(url=f"/reviews/{review['id']}", status_code=303)


@app.get("/history", response_class=HTMLResponse)
def history(request: Request):
    return templates.TemplateResponse(request, "history.html", {
        "stats": dashboard_stats(), "reviews": list_reviews(100),
    })


@app.get("/reviews/{review_id}", response_class=HTMLResponse)
def review_detail(request: Request, review_id: int):
    review = get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review["highlighted"] = highlight_html(review["text"], review["findings"])
    return templates.TemplateResponse(request, "results.html", {
        "review": review, "result": {"summary": review["summary"], "word_count": review["word_count"]},
        "findings": review["findings"], "highlighted": review["highlighted"],
    })


@app.post("/reviews/{review_id}/decision")
def decide_review(
    review_id: int,
    action: str = Form(...),
    reviewer: str = Form("Reviewer"),
    note: str = Form(""),
):
    try:
        updated = record_decision(review_id, action, reviewer, note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Review not found")
    return RedirectResponse(url=f"/reviews/{review_id}", status_code=303)


@app.get("/reviews/{review_id}/export.json")
def export_review(review_id: int):
    review = get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return JSONResponse(content=review, headers={"Content-Disposition": f'attachment; filename="proofline-review-{review_id}.json"'})


@app.get("/health")
def health():
    init_db()
    return {"status": "ok", "service": "proofline", "version": app.version, "database": "ready"}


@app.post("/api/reviews", status_code=201, tags=["reviews"])
def api_create_review(payload: ReviewCreate):
    text = payload.text
    if not text.strip():
        raise HTTPException(status_code=422, detail="Draft text must not be empty or whitespace only.")
    result = review_text(text)
    review = create_review(text, result)
    return review


@app.get("/api/reviews", tags=["reviews"])
def api_list_reviews(limit: int = 20):
    return {"items": list_reviews(limit), "stats": dashboard_stats()}


@app.get("/api/reviews/{review_id}", tags=["reviews"])
def api_get_review(review_id: int):
    review = get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/api/reviews/{review_id}/decision", tags=["reviews"])
def api_decide_review(review_id: int, payload: DecisionCreate):
    try:
        updated = record_decision(review_id, payload.action, payload.reviewer, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Review not found")
    return updated
