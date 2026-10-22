"""Run from the project root with:  python -m tests.test_engine"""
from app.engine import review_text, highlight_html

SAMPLE = ("Our app is the #1 fastest in India, loved by everyone! "
          "We utilize cutting-edge AI-powered tools to leverage synergies. "
          "Click here to learn more!! "
          "Proof Line loads 40% faster than version 1.")


def run():
    r = review_text(SAMPLE)
    f = r["findings"]
    texts = [x["flagged_text"].lower() for x in f]
    assert "#1" in texts and "fastest" in texts, "claims not detected"
    unsupported = [x for x in f if x["status"] == "Unsupported"]
    assert len(unsupported) >= 2, "unsupported claims missing"
    supported = [x for x in f if x["status"] == "Supported"]
    assert any(x["flagged_text"] == "40%" for x in supported), "40% should match fact F-01"
    assert "utilize" in texts and "leverage" in texts and "synergies" in texts
    assert "ai-powered" in texts and "cutting-edge" in texts and "loved by everyone" in texts
    assert "click here" in texts and "proof line" in texts
    assert all(x["source"] and x["reason"] for x in f), "every finding must cite a source"
    assert r["summary"]["status"] == "Needs changes"
    clean = review_text("Proofline checks drafts against approved guidelines.")
    assert clean["summary"]["total"] == 0 and clean["summary"]["status"] == "Looks good"
    html_out = highlight_html(SAMPLE, f)
    assert "<mark" in html_out and "<script" not in html_out
    safe = highlight_html("<script>alert(1)</script> utilize", review_text("<script>alert(1)</script> utilize")["findings"])
    assert "<script>" not in safe, "output must be HTML-escaped"
    print("All engine tests passed:", r["summary"])


if __name__ == "__main__":
    run()
