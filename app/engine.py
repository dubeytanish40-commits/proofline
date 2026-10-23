"""Deterministic, explainable checks for the Proofline content-review prototype.

The engine flags potential policy issues; it does not independently verify facts on
 the public web and must not be treated as an automated truth detector.
"""
from datetime import date
import html
import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
MAX_INPUT_CHARS = 20_000


def load_json(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def split_sentences(text):
    """Return sentence fragments and their original [start, end) offsets."""
    out = []
    for m in re.finditer(r".+?(?:[.!?]+(?=\s|$)|$)", text, flags=re.MULTILINE):
        raw = m.group()
        s = raw.strip()
        if not s:
            continue
        start = m.start() + (len(raw) - len(raw.lstrip()))
        out.append((s, start, start + len(s)))
    return out


def _finding(category, severity, text, start, end, reason, rule_id, source,
             suggestion=None, status=None, evidence_status=None, evidence=None):
    item = {
        "category": category,
        "severity": severity,
        "flagged_text": text,
        "start": start,
        "end": end,
        "reason": reason,
        "rule_id": rule_id,
        "source": source,
        "suggestion": suggestion,
        "status": status,
        "method": "Deterministic rule match",
        "match_basis": "Configured guideline/rule; not an AI truth score",
    }
    if evidence_status:
        item["evidence_status"] = evidence_status
    if evidence:
        item["evidence"] = evidence
    return item


def check_brand_name(text, g):
    out = []
    correct = g["brand"]["correct_spelling"]
    for m in re.finditer(r"\bproof[\s\-]?line\b", text, flags=re.IGNORECASE):
        if m.group() != correct:
            out.append(_finding(
                "terminology", "medium", m.group(), m.start(), m.end(),
                f'The product name must be written "{correct}".',
                g["brand"]["rule_id"], g["brand"]["source"], suggestion=correct))
    return out


def check_terminology(text, g):
    out = []
    for entry in g["terminology"]:
        pattern = r"\b" + re.escape(entry["avoid"]) + r"\b"
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            out.append(_finding(
                "terminology", "medium", m.group(), m.start(), m.end(),
                f'"{entry["avoid"]}" is on the avoid list. Preferred wording: "{entry["prefer"]}".',
                entry["rule_id"], entry["source"], suggestion=entry["prefer"]))
    return out


def check_tone(text, g):
    out = []
    t = g["tone"]
    for phrase in t["hype_words"]:
        for m in re.finditer(r"\b" + re.escape(phrase) + r"\b", text, flags=re.IGNORECASE):
            out.append(_finding(
                "tone", "medium", m.group(), m.start(), m.end(),
                f'"{phrase}" may sound boastful. The configured brand voice is confident but not boastful.',
                t["hype_rule"]["rule_id"], t["hype_rule"]["source"]))
    bangs = [m.start() for m in re.finditer(r"!", text)]
    for pos in bangs[1:]:
        out.append(_finding(
            "tone", "low", "!", pos, pos + 1,
            "Use at most one exclamation mark per piece of content.",
            t["exclamation_rule"]["rule_id"], t["exclamation_rule"]["source"]))
    for m in re.finditer(r"\b[A-Z]{4,}\b", text):
        if m.group() not in t["allowed_caps"]:
            out.append(_finding(
                "tone", "low", m.group(), m.start(), m.end(),
                "Avoid writing words in all capitals; it may read as shouting.",
                t["caps_rule"]["rule_id"], t["caps_rule"]["source"],
                suggestion=m.group().capitalize()))
    return out


def _fact_is_current(fact, today=None):
    valid_until = fact.get("valid_until")
    if not valid_until:
        return True
    try:
        return date.fromisoformat(valid_until) >= (today or date.today())
    except (TypeError, ValueError):
        return False


def _matching_fact(sentence, claim_match, facts):
    """Match a claim only when its own text overlaps fact keywords in that sentence."""
    sentence_lower = sentence.casefold()
    claim_lower = claim_match.casefold()
    for fact in facts:
        keywords = fact.get("keywords", [])
        if not keywords or not _fact_is_current(fact):
            continue
        if all(str(k).casefold() in sentence_lower for k in keywords) and any(
            str(k).casefold() in claim_lower for k in keywords
        ):
            return fact
    return None


def check_claims(text, g, facts):
    """Flag promotional claims and label whether a configured fact matched.

    A missing match means "needs evidence", not "false". The matching is based on
    local keywords in a sample fact library and is not independent fact verification.
    """
    out = []
    c = g["claims"]
    seen = set()
    for sentence, s_start, _ in split_sentences(text):
        for pat in c["patterns"]:
            for m in re.finditer(pat, sentence, flags=re.IGNORECASE):
                start, end = s_start + m.start(), s_start + m.end()
                if (start, end) in seen:
                    continue
                seen.add((start, end))
                fact = _matching_fact(sentence, m.group(), facts)
                if fact:
                    out.append(_finding(
                        "claim", "info", m.group(), start, end,
                        f'Matched configured fact {fact["id"]}: {fact["text"]}',
                        c["rule_id"], f'{fact["source"]} ({fact["id"]})',
                        status="Matched approved fact", evidence_status="matched_approved_fact",
                        evidence={"id": fact["id"], "text": fact["text"], "source": fact["source"],
                                  "valid_until": fact.get("valid_until")}))
                else:
                    out.append(_finding(
                        "claim", "high", m.group(), start, end,
                        "No matching current fact was found in the configured fact library. This does not prove the claim is false; add evidence or have a reviewer verify it.",
                        c["rule_id"], c["source"], status="Needs evidence",
                        evidence_status="no_matching_approved_fact"))
    return out


def check_readability(text, g):
    out = []
    r = g["readability"]
    for s, start, end in split_sentences(text):
        n = len(s.split())
        if n > r["max_sentence_words"]:
            out.append(_finding(
                "readability", "low", s, start, end,
                f"This sentence has {n} words; the configured limit is {r['max_sentence_words']}.",
                r["rule_id"], r["source"]))
    return out


def check_accessibility(text, g):
    out = []
    a = g["accessibility"]
    for phrase in a["phrases"]:
        for m in re.finditer(r"\b" + re.escape(phrase) + r"\b", text, flags=re.IGNORECASE):
            out.append(_finding(
                "accessibility", "medium", m.group(), m.start(), m.end(),
                f'"{phrase}" is not descriptive link text; readers using assistive technology need to know where a link goes.',
                a["rule_id"], a["source"],
                suggestion="Use link text that describes the destination"))
    return out


def review_text(text, guidelines=None, facts=None):
    """Run configured checks and return findings plus a deterministic summary."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if len(text) > MAX_INPUT_CHARS:
        raise ValueError(f"Text is too long; the limit is {MAX_INPUT_CHARS:,} characters.")
    g = guidelines or load_json("guidelines.json")
    f = facts if facts is not None else load_json("facts.json")
    findings = []
    findings += check_brand_name(text, g)
    findings += check_terminology(text, g)
    findings += check_tone(text, g)
    findings += check_claims(text, g, f)
    findings += check_readability(text, g)
    findings += check_accessibility(text, g)
    # Stable order: position first, then severity, then most-specific text.
    findings.sort(key=lambda x: (x["start"], SEVERITY_ORDER[x["severity"]], x["end"] - x["start"]))
    for i, item in enumerate(findings, 1):
        item["id"] = i
    counts = {k: sum(1 for x in findings if x["severity"] == k) for k in SEVERITY_ORDER}
    counts["total"] = len(findings)
    counts["claims_needing_evidence"] = sum(
        1 for x in findings if x.get("evidence_status") == "no_matching_approved_fact")
    counts["matched_facts"] = sum(
        1 for x in findings if x.get("evidence_status") == "matched_approved_fact")
    counts["status"] = "Needs review" if counts["high"] else (
        "Needs changes" if counts["medium"] else ("Minor suggestions" if counts["low"] else "Looks good"))
    return {"findings": findings, "summary": counts, "word_count": len(text.split())}


def highlight_html(text, findings):
    """Create escaped HTML for non-overlapping highlights; all findings remain listed."""
    parts, cursor = [], 0
    candidates = sorted(
        (f for f in findings if f["severity"] != "info"),
        key=lambda x: (x["start"], SEVERITY_ORDER[x["severity"]], x["end"] - x["start"]))
    for f in candidates:
        start, end = f["start"], f["end"]
        if start < cursor or start < 0 or end > len(text) or end <= start:
            continue
        parts.append(html.escape(text[cursor:start]))
        label = html.escape(f'#{f["id"]}: {f["reason"]}', quote=True)
        parts.append(f'<mark class="sev-{f["severity"]}" tabindex="0" title="{label}">'
                     f'{html.escape(text[start:end])}</mark>')
        cursor = end
    parts.append(html.escape(text[cursor:]))
    return "".join(parts).replace("\n", "<br>\n")
