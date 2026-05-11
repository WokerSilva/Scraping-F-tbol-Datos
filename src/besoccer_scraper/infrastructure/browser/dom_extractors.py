from __future__ import annotations

import re


def extract_competition_matches_from_html(html: str) -> dict[str, object]:
    source = html or ""
    options = re.findall(r"<option[^>]*value=\"([^\"]*)\"[^>]*>(.*?)</option>", source, re.I | re.S)
    round_options = [{"value": v.strip(), "text": re.sub(r"<[^>]+>", "", t).strip(), "selected": ("selected" in t.lower())} for v, t in options]

    global_anchors = re.findall(r'href=\"([^\"]*/partido/[^\"]*)\"', source, re.I)
    scope_match = re.search(r'<div[^>]*id=\"mod_mainCompetitionRounds\"[^>]*>(.*?)</div>', source, re.I | re.S)
    if not scope_match:
        scope_match = re.search(r'<main[^>]*>(.*?)</main>', source, re.I | re.S)
    scope_html = scope_match.group(1) if scope_match else ""
    scoped_anchors = re.findall(r'href=\"([^\"]*/partido/[^\"]*)\"', scope_html, re.I)

    matches = []
    seen = set()
    for href in scoped_anchors:
        sid = href.rstrip('/').split('/')[-1]
        if sid in seen:
            continue
        seen.add(sid)
        matches.append({"url": href, "source_match_id": sid, "scope_hint": "#mod_mainCompetitionRounds"})

    return {
        "round_options": round_options,
        "matches": matches,
        "diagnostics": {
            "match_anchor_count_global": len(global_anchors),
            "match_anchor_count_scoped": len(scoped_anchors),
            "scope_found": bool(scope_match),
        },
    }
