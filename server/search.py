"""Fuzzy text search — pure, dependency-free scoring.

Like `planner`, this is deliberately pure logic over plain inputs so it can be unit
tested exhaustively with no database. `fuzzy_score` ranks how well a query matches a
candidate string; `rank_recipes` applies it across recipes and orders the results.

Scoring tiers (higher = better), all case-insensitive:
    1.00  exact match
    0.95  candidate starts with the query
    0.90  query appears as a substring
    ≤0.50 query is a subsequence (chars in order, possibly gapped); the tighter the
          span, the higher the score
    0.00  not a subsequence at all
"""

from __future__ import annotations

from . import schemas


def fuzzy_score(query: str, text: str) -> float:
    q = query.strip().lower()
    t = text.strip().lower()
    if not q:
        return 0.0
    if q == t:
        return 1.0
    if t.startswith(q):
        return 0.95
    if q in t:
        return 0.90

    # subsequence check: every char of q appears in t, in order
    matched = 0
    first = last = None
    for i, ch in enumerate(t):
        if matched < len(q) and ch == q[matched]:
            if first is None:
                first = i
            last = i
            matched += 1
    if matched < len(q) or first is None:
        return 0.0

    span = last - first + 1
    compactness = len(q) / span  # 1.0 when the matched chars are contiguous
    return round(0.5 * compactness, 4)


def rank_recipes(
    query: str, recipes: list[schemas.Recipe], *, threshold: float = 0.0
) -> list[tuple[float, schemas.Recipe]]:
    """Score each recipe by its name and return matches sorted best-first.

    Ties (equal score) break alphabetically by name for stable output.
    """
    scored = [(fuzzy_score(query, r.name), r) for r in recipes]
    matches = [(s, r) for s, r in scored if s > threshold]
    matches.sort(key=lambda sr: (-sr[0], sr[1].name.lower()))
    return matches
