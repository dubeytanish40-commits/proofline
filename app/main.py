from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.engine import highlight_html, review_text

BASE = Path(__file__).parent
app = FastAPI(title="Proofline")
templates = Jinja2Templates(directory=str(BASE / "templates"))

SAMPLE = (
    "Our app is the #1 fastest in India, loved by everyone! "
    "We utilize cutting-edge AI-powered tools to leverage synergies. "
    "Click here to learn more!! "
    "Proof Line loads 40% faster than version 1."
)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"sample": SAMPLE, "text": ""})


@app.post("/review", response_class=HTMLResponse)
def review(request: Request, text: str = Form(...)):
    result = review_text(text)
    return templates.TemplateResponse(request, "results.html", {
        "text": text,
        "result": result,
        "findings": result["findings"],
        "highlighted": highlight_html(text, result["findings"]),
    })


@app.get("/health")
def health():
    return {"status": "ok"}
