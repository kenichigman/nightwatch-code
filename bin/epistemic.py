#!/usr/bin/env python3
"""Epistemic-qualifier families: the shared logic dependency for the
local tier's qualifier gate.

If a family matches the SOURCE, the output must match the same family —
checked by qualifier_gate(). Families are near-synonym groups, not single
tokens: "UNVERIFIED single-report" in the source is satisfied by "single
unconfirmed report" in the output, but NOT by silence. Patterns are bounded
so a paraphrase with an inserted adjective still matches, while unrelated
text cannot.

This lives in its own leaf module (no sibling imports) so that both
local_summarize.py and mechanical_gate.py can import it without creating
an import cycle through the pre-flight chain.
"""
import re

EPISTEMIC = {
    "unverified": r"unverified|unconfirmed|not\s+(?:yet\s+)?(?:verified|confirmed)|could\s+not\s+be\s+verified",
    "single-report": r"single[\w\s-]{0,24}(?:report|source)|lone\s+report|sole\s+report|\bone\s+report\b",
    "rumor": r"rumo[u]?r(?:ed|s)?\b",
    "alleged": r"alleg(?:ed|edly|ation)",
}


def _present(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def qualifier_gate(src: str, out: str) -> list:
    """Return the names of qualifier families the source carries but the
    output dropped. Empty list = gate passes."""
    missing = []
    for canon, pattern in EPISTEMIC.items():
        if _present(src, pattern) and not _present(out, pattern):
            missing.append(canon)
    return missing
