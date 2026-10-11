"""
search.py
---------
Matches the terms a user types (for example "discount abuse" or
"low stock") to the queries in the catalog.

Each keyword or phrase that appears in the search text adds to a query's
score. Multi-word phrases count double because they are more specific.
Results come back ranked, so the user picks from the best matches instead
of the app guessing a single answer.
"""

import re

from analyst.queries import CATALOG, Query


def _keyword_pattern(keyword: str) -> re.Pattern:
    # Whole word match with an optional plural, so "order" matches "orders"
    # but "age" does not match "average".
    return re.compile(r"\b" + re.escape(keyword.lower()) + r"(s|es)?\b")


_PATTERNS: dict[str, list[tuple[re.Pattern, int]]] = {
    q.key: [(_keyword_pattern(kw), 2 if " " in kw else 1) for kw in q.keywords]
    for q in CATALOG
}


def score_query(text: str, query: Query) -> int:
    """How strongly the search text matches one query. 0 means no match."""
    text = text.lower()
    return sum(weight for pattern, weight in _PATTERNS[query.key] if pattern.search(text))


def search(text: str, limit: int = 5) -> list[Query]:
    """
    Return up to `limit` matching queries, best match first.
    Ties keep catalog order. An empty list means nothing matched.
    """
    if not text or not text.strip():
        return []

    scored = [(score_query(text, q), i, q) for i, q in enumerate(CATALOG)]
    matches = [(s, i, q) for s, i, q in scored if s > 0]
    matches.sort(key=lambda item: (-item[0], item[1]))
    return [q for _, _, q in matches[:limit]]
