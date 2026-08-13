# processors/__init__.py

from .member_matcher import (
    match_member,
    enrich_with_member,
)

from .relevance_filter import (
    calculate_fomc_relevance,
    filter_by_relevance,
)

from .topic_classifier import (
    classify_topics,
)

from .hawk_dove import (
    score_hawk_dove,
)

from .deduplicator import (
    deduplicate_articles,
)


__all__ = [
    "match_member",
    "enrich_with_member",
    "calculate_fomc_relevance",
    "filter_by_relevance",
    "classify_topics",
    "score_hawk_dove",
    "deduplicate_articles",
]