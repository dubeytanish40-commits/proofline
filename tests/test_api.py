"""Web/API smoke tests. Run: python -m tests.test_api (installs requirements-dev.txt)."""
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app


def run():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.dict(os.environ, {"PROOFLINE_DB_PATH": str(Path(tmp) / "api-test.db")}):
            with TestClient(app) as client:
                home = client.get("/")
                assert home.status_code == 200 and "Proofline" in home.text
                health = client.get("/health")
                assert health.status_code == 200 and health.json()["database"] == "ready"

                created = client.post("/api/reviews", json={"text": "Our product is the #1 best service."})
                assert created.status_code == 201, created.text
                review_id = created.json()["id"]
                assert created.json()["status"] == "Pending review"

                detail = client.get(f"/api/reviews/{review_id}")
                assert detail.status_code == 200 and len(detail.json()["events"]) == 1
                decision = client.post(f"/api/reviews/{review_id}/decision", json={
                    "action": "Changes requested", "reviewer": "API Test", "note": "Please add evidence."
                })
                assert decision.status_code == 200, decision.text
                assert decision.json()["status"] == "Changes requested"
                assert len(decision.json()["events"]) == 2

                listing = client.get("/api/reviews")
                assert listing.status_code == 200 and listing.json()["stats"]["total_reviews"] == 1
                export = client.get(f"/reviews/{review_id}/export.json")
                assert export.status_code == 200 and export.json()["id"] == review_id
                detail_page = client.get(f"/reviews/{review_id}")
                assert detail_page.status_code == 200 and "Audit trail" in detail_page.text
                history = client.get("/history")
                assert history.status_code == 200 and f"#{review_id}" in history.text
                docs = client.get("/docs")
                assert docs.status_code == 200
                bad = client.post("/api/reviews", json={"text": "   "})
                assert bad.status_code == 422
                missing = client.get("/api/reviews/999999")
                assert missing.status_code == 404
                invalid_decision = client.post(f"/api/reviews/{review_id}/decision", json={
                    "action": "Not a real decision"
                })
                assert invalid_decision.status_code == 422
                form = client.post("/review", data={"text": "Proofline checks brand wording."}, follow_redirects=False)
                assert form.status_code == 303 and "/reviews/" in form.headers["location"]
    print("All web/API tests passed: pages, create/read/decide, history, export, validation and errors")


if __name__ == "__main__":
    run()
