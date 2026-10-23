"""Small SQLite persistence layer for review records and an append-only decision log."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _db_path():
    configured = os.environ.get("PROOFLINE_DB_PATH")
    return Path(configured) if configured else PROJECT_ROOT / "proofline.db"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
      CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending review',
        word_count INTEGER NOT NULL,
        summary_json TEXT NOT NULL,
        findings_json TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS review_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
        action TEXT NOT NULL,
        reviewer TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at DESC);
      CREATE INDEX IF NOT EXISTS idx_events_review_id ON review_events(review_id, id);
    """)
    return conn


def init_db():
    conn = _connect()
    conn.close()


def create_review(text, result):
    now = _now()
    conn = _connect()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO reviews(text, created_at, updated_at, status, word_count, summary_json, findings_json) "
                "VALUES (?, ?, ?, 'Pending review', ?, ?, ?)",
                (text, now, now, result["word_count"], json.dumps(result["summary"], ensure_ascii=False),
                 json.dumps(result["findings"], ensure_ascii=False)))
            review_id = cur.lastrowid
            conn.execute(
                "INSERT INTO review_events(review_id, action, reviewer, note, created_at) VALUES (?, ?, ?, ?, ?)",
                (review_id, "Submitted", "System", "Content submitted for guideline review.", now))
        return get_review(review_id)
    finally:
        conn.close()


def _decode_review(row):
    if row is None:
        return None
    item = dict(row)
    item["summary"] = json.loads(item.pop("summary_json"))
    item["findings"] = json.loads(item.pop("findings_json"))
    return item


def get_review(review_id, include_events=True):
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        item = _decode_review(row)
        if item and include_events:
            item["events"] = [dict(r) for r in conn.execute(
                "SELECT id, action, reviewer, note, created_at FROM review_events WHERE review_id = ? ORDER BY id",
                (review_id,)).fetchall()]
        return item
    finally:
        conn.close()


def list_reviews(limit=20):
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, created_at, updated_at, status, word_count, summary_json, substr(text, 1, 240) AS preview "
            "FROM reviews ORDER BY id DESC LIMIT ?", (max(1, min(int(limit), 100)),)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json"))
            item["preview"] = item["preview"].replace("\n", " ")
            result.append(item)
        return result
    finally:
        conn.close()


def dashboard_stats():
    conn = _connect()
    try:
        rows = conn.execute("SELECT status, COUNT(*) AS n FROM reviews GROUP BY status").fetchall()
        by_status = {r["status"]: r["n"] for r in rows}
        total = sum(by_status.values())
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
        recent = conn.execute("SELECT COUNT(*) FROM reviews WHERE created_at >= ?", (cutoff,)).fetchone()[0]
        return {"total_reviews": total, "last_7_days": recent, "pending": by_status.get("Pending review", 0),
                "approved": by_status.get("Approved", 0), "needs_changes": by_status.get("Changes requested", 0),
                "rejected": by_status.get("Rejected", 0)}
    finally:
        conn.close()


def record_decision(review_id, action, reviewer="Reviewer", note=""):
    allowed = {"Approved", "Changes requested", "Rejected", "Reopened"}
    if action not in allowed:
        raise ValueError("Unsupported decision")
    reviewer = (reviewer or "Reviewer").strip()[:80] or "Reviewer"
    note = (note or "").strip()[:2000]
    now = _now()
    conn = _connect()
    try:
        with conn:
            row = conn.execute("SELECT id FROM reviews WHERE id = ?", (review_id,)).fetchone()
            if row is None:
                return None
            status = "Pending review" if action == "Reopened" else action
            conn.execute("UPDATE reviews SET status = ?, updated_at = ? WHERE id = ?", (status, now, review_id))
            conn.execute(
                "INSERT INTO review_events(review_id, action, reviewer, note, created_at) VALUES (?, ?, ?, ?, ?)",
                (review_id, action, reviewer, note, now))
        return get_review(review_id)
    finally:
        conn.close()
