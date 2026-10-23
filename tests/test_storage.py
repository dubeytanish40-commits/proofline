"""Storage regression tests. Run: python -m tests.test_storage"""
import os
from pathlib import Path
import tempfile

from app.engine import review_text
from app import storage


def run():
    previous = os.environ.get("PROOFLINE_DB_PATH")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["PROOFLINE_DB_PATH"] = str(Path(tmp) / "test.db")
        storage.init_db()
        review = storage.create_review("A #1 product claim.", review_text("A #1 product claim."))
        assert review["id"] == 1
        assert review["status"] == "Pending review"
        assert len(review["events"]) == 1 and review["events"][0]["action"] == "Submitted"
        assert len(storage.list_reviews()) == 1
        approved = storage.record_decision(review["id"], "Approved", "Demo Reviewer", "Evidence checked for demo.")
        assert approved["status"] == "Approved"
        assert len(approved["events"]) == 2
        assert approved["events"][1]["reviewer"] == "Demo Reviewer"
        assert storage.dashboard_stats()["approved"] == 1
        assert storage.get_review(99999) is None
        assert storage.record_decision(99999, "Rejected") is None
        try:
            storage.record_decision(review["id"], "Random")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid decisions must be rejected")
    if previous is None:
        os.environ.pop("PROOFLINE_DB_PATH", None)
    else:
        os.environ["PROOFLINE_DB_PATH"] = previous
    print("All storage tests passed: create, persist, decision log, statistics, and validation")


if __name__ == "__main__":
    run()
