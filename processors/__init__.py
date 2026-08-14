# processors/__init__.py

from .member_matcher import (
    match_member,
    enrich_with_member,
)

from .relevance_filter import (
    calculate_fomc_relevance,
)

from .topic_classifier import (
    classify_topics,
)

from .hawk_dove import (
    score_hawk_dove,
    score_to_hawk_dove_label,
)

from .deduplicator import (
    deduplicate_articles,
)

from .news_stance import (
    score_news_text,
    analyze_member_news,
)

from .consensus import (
    calculate_consensus,
    cluster_news_articles,
    summarize_news_clusters,
)

from .momentum import (
    calculate_momentum,
    momentum_to_label,
    momentum_display,
    prepare_momentum_articles,
    attach_member_momentum,
)

from .event_key import (
    normalize_event_text,
    infer_event_date,
    extract_policy_fingerprint,
    build_event_key,
    build_event_signature_text,
    event_similarity,
    is_same_event,
    merge_event_group,
    deduplicate_events,
)

from .model_stance import (
    score_to_model_stance,
    is_verified_infomax_policy_speech,
    is_high_confidence_policy_event,
    select_model_evidence,
    calculate_model_score,
    calculate_model_confidence,
    calculate_model_stance,
)

from .recent_signal import (
    score_to_recent_signal,
    select_auxiliary_speech,
    calculate_auxiliary_speech_signal,
    normalize_news_signal,
    calculate_recent_signal_confidence,
    calculate_recent_signal,
)

from .final_stance import (
    score_to_final_stance,
    get_model_weight,
    get_recent_confidence_multiplier,
    signals_conflict,
    calculate_final_confidence,
    calculate_final_stance,
)

__all__ = [

    "match_member",
    "enrich_with_member",

    "calculate_fomc_relevance",

    "classify_topics",

    "score_hawk_dove",

    "deduplicate_articles",

    "score_news_text",
    "analyze_member_news",

    "calculate_consensus",
    "cluster_news_articles",
    "summarize_news_clusters",

    "calculate_momentum",
    "momentum_to_label",
    "momentum_display",
    "prepare_momentum_articles",
    "attach_member_momentum",

    "normalize_event_text",
    "infer_event_date",
    "extract_policy_fingerprint",
    "build_event_key",
    "build_event_signature_text",
    "event_similarity",
    "is_same_event",
    "merge_event_group",
    "deduplicate_events",

    "score_to_model_stance",
    "is_high_confidence_policy_event",
    "is_verified_infomax_policy_speech",
    "select_model_evidence",
    "calculate_model_score",
    "calculate_model_confidence",
    "calculate_model_stance",

    "score_to_recent_signal",
    "select_auxiliary_speech",
    "calculate_auxiliary_speech_signal",
    "normalize_news_signal",
    "calculate_recent_signal_confidence",
    "calculate_recent_signal",

    "score_to_final_stance",
    "get_model_weight",
    "get_recent_confidence_multiplier",
    "signals_conflict",
    "calculate_final_confidence",
    "calculate_final_stance",

]