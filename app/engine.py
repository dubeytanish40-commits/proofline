"""Proofline review engine (Round 2, version 1).

Rules first: every check below is a fixed rule, so results are fast, repeatable
and always point to the guideline they came from ("no source, no finding").
AI-assisted checks are planned for Round 3.
"""
import html
import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def load_json(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def split_sentences(text):
    """Return a list of (sentence, start, end) for each sentence in the text."""
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
             suggestion=None, status=None):
    return {
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
        "method": "Rule-based",
        "confidence": 1.0,
    }


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
                f'"{phrase}" sounds boastful. Our voice is confident but not boastful.',
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
                "Avoid writing words in all capitals; it reads as shouting.",
                t["caps_rule"]["rule_id"], t["caps_rule"]["source"], suggestion=m.group().capitalize()))
    return out


def check_claims(text, g, facts):
    """Find promotional claims and match each to an approved fact."""
    out = []
    c = g["claims"]
    seen = set()
    for sentence, s_start, s_end in split_sentences(text):
        lowered = sentence.lower()
        fact = next((f for f in facts if all(k.lower() in lowered for k in f["keywords"])), None)
        for pat in c["patterns"]:
            for m in re.finditer(pat, sentence, flags=re.IGNORECASE):
                start, end = s_start + m.start(), s_start + m.end()
                if (start, end) in seen:
                    continue
                seen.add((start, end))
                if fact:
                    out.append(_finding(
                        "claim", "info", m.group(), start, end,
                        f'Supported by approved fact {fact["id"]}: {fact["text"]}',
                        c["rule_id"], f'{fact["source"]} ({fact["id"]})', status="Supported"))
                else:
                    out.append(_finding(
                        "claim", "high", m.group(), start, end,
                        "This promotional claim has no approved fact behind it. Remove it or add evidence.",
                        c["rule_id"], c["source"], status="Unsupported"))
    return out


def check_readability(text, g):
    out = []
    r = g["readability"]
    for s, start, end in split_sentences(text):
        n = len(s.split())
        if n > r["max_sentence_words"]:
            out.append(_finding(
                "readability", "low", s, start, end,
                f'This sentence has {n} words; the limit is {r["max_sentence_words"]}.',
                r["rule_id"], r["source"]))
    return out


def check_accessibility(text, g):
    out = []
    a = g["accessibility"]
    for phrase in a["phrases"]:
        for m in re.finditer(r"\b" + re.escape(phrase) + r"\b", text, flags=re.IGNORECASE):
            out.append(_finding(
                "accessibility", "medium", m.group(), m.start(), m.end(),
                f'"{phrase}" is not descriptive link text; screen-reader users need to know where a link goes.',
                a["rule_id"], a["source"], suggestion="Use link text that describes the destination"))
    return out


def review_text(text, guidelines=None, facts=None):
    """Run every check and return findings plus a summary."""
    g = guidelines or load_json("guidelines.json")
    f = facts if facts is not None else load_json("facts.json")
    findings = []
    findings += check_brand_name(text, g)
    findings += check_terminology(text, g)
    findings += check_tone(text, g)
    findings += check_claims(text, g, f)
    findings += check_readability(text, g)
    findings += check_accessibility(text, g)
    findings.sort(key=lambda x: (x["start"], SEVERITY_ORDER[x["severity"]]))
    for i, item in enumerate(findings, 1):
        item["id"] = i
    counts = {k: sum(1 for x in findings if x["severity"] == k) for k in SEVERITY_ORDER}
    counts["total"] = len(findings)
    counts["status"] = "Needs changes" if (counts["high"] or counts["medium"]) else (
        "Minor suggestions" if counts["low"] else "Looks good")
    return {"findings": findings, "summary": counts, "word_count": len(text.split())}


def highlight_html(text, findings):
    """Return the text as safe HTML with flagged spans wrapped in <mark>."""
    parts, cursor = [], 0
    for f in sorted(findings, key=lambda x: (x["start"], -(x["end"] - x["start"]))):
        if f["severity"] == "info" or f["start"] < cursor:
            continue
        parts.append(html.escape(text[cursor:f["start"]]))
        label = html.escape(f'#{f["id"]}: {f["reason"]}', quote=True)
        parts.append(f'<mark class="sev-{f["severity"]}" title="{label}">'
                     f'{html.escape(text[f["start"]:f["end"]])}</mark>')
        cursor = f["end"]
    parts.append(html.escape(text[cursor:]))
    return "".join(parts).replace("\n", "<br>")
