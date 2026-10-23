"""Engine regression tests. Run: python -m tests.test_engine"""
from app.engine import MAX_INPUT_CHARS, highlight_html, review_text

SAMPLE = ("Our app is the #1 fastest in India, loved by everyone! "
          "We utilize cutting-edge AI-powered tools to leverage synergies. "
          "Click here to learn more!! "
          "Proof Line loads 40% faster than version 1.")


def run():
    r = review_text(SAMPLE)
    f = r["findings"]
    texts = [x["flagged_text"].lower() for x in f]
    assert "#1" in texts and "fastest" in texts, "claims not detected"
    needs_evidence = [x for x in f if x.get("evidence_status") == "no_matching_approved_fact"]
    assert len(needs_evidence) >= 2, "claims requiring evidence missing"
    assert all("does not prove" in x["reason"].lower() for x in needs_evidence), "absence of evidence must not mean false"
    matched = [x for x in f if x.get("evidence_status") == "matched_approved_fact"]
    assert any(x["flagged_text"] == "40%" for x in matched), "40% should match fact F-01"
    assert not any(x["flagged_text"] == "#1" and x.get("evidence_status") == "matched_approved_fact" for x in matched), "unrelated fact must not support #1"
    assert "utilize" in texts and "leverage" in texts and "synergies" in texts
    assert "ai-powered" in texts and "cutting-edge" in texts and "loved by everyone" in texts
    assert "click here" in texts and "proof line" in texts
    assert all(x["source"] and x["reason"] for x in f), "every finding must cite a source"
    assert r["summary"]["status"] == "Needs review"
    assert r["summary"]["claims_needing_evidence"] >= 2
    clean = review_text("Proofline checks drafts against approved guidelines.")
    assert clean["summary"]["total"] == 0 and clean["summary"]["status"] == "Looks good"
    html_out = highlight_html(SAMPLE, f)
    assert "<mark" in html_out and "<script" not in html_out
    unsafe_text = "<script>alert(1)</script> utilize"
    safe = highlight_html(unsafe_text, review_text(unsafe_text)["findings"])
    assert "<script>" not in safe and "&lt;script&gt;" in safe, "output must be HTML-escaped"
    assert review_text("" )["summary"]["total"] == 0
    try:
        review_text("a" * (MAX_INPUT_CHARS + 1))
    except ValueError:
        pass
    else:
        raise AssertionError("overlong inputs must be rejected")
    print("All engine tests passed:", r["summary"])


if __name__ == "__main__":
    run()
