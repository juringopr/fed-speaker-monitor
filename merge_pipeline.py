# merge_pipeline.py

from pathlib import Path
from datetime import datetime
from collections import Counter
import json
import time

from processors import (
    deduplicate_events,
    calculate_momentum,
    calculate_model_stance,
    analyze_member_news,
    calculate_consensus,
    calculate_recent_signal,
    calculate_final_stance,
)

from crawlers.news import (
    search_member_news,
)

from exporters import (
    save_to_excel,
)


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
)

DATA_DIR = (
    PROJECT_ROOT
    / "data"
)

OFFICIAL_CACHE_PATH = (
    DATA_DIR
    / "official_cache.json"
)

INFOMAX_CACHE_PATH = (
    DATA_DIR
    / "infomax_cache.json"
)

FINAL_CACHE_PATH = (
    DATA_DIR
    / "final_events.json"
)


EVENT_SIMILARITY_THRESHOLD = 0.25
EVENT_DATE_TOLERANCE_DAYS = 1

CURRENT_STANCE_N = 5

NEWS_ENABLED = True
NEWS_LOOKBACK_DAYS = 90
NEWS_MAX_RESULTS = 10
NEWS_REQUEST_SLEEP = 0.35

RECENT_SIGNAL_LOOKBACK_DAYS = 90


# ============================================================
# JSON SAFE
# ============================================================

def json_safe(value):

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key):
                json_safe(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            json_safe(item)
            for item
            in value
        ]

    try:
        if hasattr(
            value,
            "isoformat",
        ):
            return value.isoformat()

    except Exception:
        pass

    return str(value)


# ============================================================
# LOAD CACHE
# ============================================================

def load_cache(path):

    if not path.exists():

        raise FileNotFoundError(
            f"캐시 파일이 없습니다: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        payload = json.load(file)

    articles = (
        payload.get("articles")
        or []
    )

    return (
        payload,
        articles,
    )


# ============================================================
# GROUP BY MEMBER
# ============================================================

def group_by_member(articles):

    grouped = {}

    for article in articles:

        member = (
            article.get(
                "member_name_en"
            )
        )

        if not member:
            continue

        grouped.setdefault(
            member,
            [],
        )

        grouped[
            member
        ].append(
            article
        )

    return grouped


# ============================================================
# SCORE -> LABEL
# ============================================================

def score_to_label(score):

    try:
        score = float(score)

    except (
        TypeError,
        ValueError,
    ):
        return "UNKNOWN"

    if score >= 4:
        return "HAWKISH"

    if score >= 1:
        return "NEUTRAL_HAWKISH"

    if score <= -4:
        return "DOVISH"

    if score <= -1:
        return "NEUTRAL_DOVISH"

    return "NEUTRAL"


# ============================================================
# LEGACY CURRENT STANCE
# ============================================================

def calculate_current_stance(articles):

    important = [
        item
        for item in articles
        if item.get(
            "fomc_relevance"
        )
        in [
            "HIGH",
            "MEDIUM",
        ]
    ]

    important.sort(
        key=lambda item: (
            item.get(
                "actual_speech_date"
            )
            or
            item.get(
                "speech_date"
            )
            or
            item.get(
                "event_date"
            )
            or
            item.get(
                "published_at"
            )
            or
            ""
        ),
        reverse=True,
    )

    recent = (
        important[
            :CURRENT_STANCE_N
        ]
    )

    scores = []

    for article in recent:

        value = (
            article.get(
                "hawk_dove_score"
            )
        )

        try:

            if value is not None:

                scores.append(
                    float(value)
                )

        except (
            TypeError,
            ValueError,
        ):
            pass

    if not scores:

        return {
            "score":
                None,

            "label":
                "UNKNOWN",

            "sample_count":
                0,
        }

    score = round(
        sum(scores)
        /
        len(scores),
        2,
    )

    return {
        "score":
            score,

        "label":
            score_to_label(
                score
            ),

        "sample_count":
            len(scores),
    }


# ============================================================
# MODEL STANCE
# ============================================================

def build_model_stances(grouped):

    results = {}

    for (
        member,
        articles,
    ) in grouped.items():

        try:

            results[
                member
            ] = (
                calculate_model_stance(
                    articles
                )
            )

        except Exception as exc:

            print(
                "[MODEL STANCE ERROR]",
                member,
                "|",
                exc,
            )

            results[
                member
            ] = {

                "model_stance":
                    "INSUFFICIENT",

                "model_score":
                    None,

                "model_confidence":
                    "INSUFFICIENT",

                "model_evidence_count":
                    0,

                "model_evidence":
                    [],

                "model_evidence_summary":
                    [],
            }

    return results


# ============================================================
# MOMENTUM
# ============================================================

def build_momentum(grouped):

    results = {}

    for (
        member,
        articles,
    ) in grouped.items():

        try:

            results[
                member
            ] = (
                calculate_momentum(
                    articles
                )
            )

        except Exception as exc:

            print(
                "[MOMENTUM ERROR]",
                member,
                "|",
                exc,
            )

            results[
                member
            ] = {

                "momentum_label":
                    "INSUFFICIENT",

                "momentum_score":
                    None,

                "momentum_confidence":
                    "INSUFFICIENT",
            }

    return results


# ============================================================
# NEWS
# ============================================================

def build_news_checks(grouped):

    results = {}

    if not NEWS_ENABLED:
        return results

    total = len(grouped)

    for index, (
        member,
        articles,
    ) in enumerate(
        grouped.items(),
        start=1,
    ):

        print(
            f"[NEWS {index}/{total}] "
            f"{member}"
        )

        current = (
            calculate_current_stance(
                articles
            )
        )

        try:

            news_items = (
                search_member_news(
                    member,
                    lookback_days=(
                        NEWS_LOOKBACK_DAYS
                    ),
                    max_results=(
                        NEWS_MAX_RESULTS
                    ),
                )
            )

            news_analysis = (
                analyze_member_news(
                    news_items
                )
            )

        except Exception as exc:

            print(
                "  [NEWS ERROR]",
                exc,
            )

            news_analysis = {

                "news_score":
                    None,

                "news_label":
                    "INSUFFICIENT",

                "news_count":
                    0,

                "news_usable_count":
                    0,

                "news_confidence":
                    "LOW",

                "news_articles":
                    [],
            }

        try:

            consensus = (
                calculate_consensus(
                    speech_score=(
                        current["score"]
                        if current["score"] is not None
                        else 0.0
                    ),
                    speech_label=(
                        current["label"]
                    ),
                    news_analysis=(
                        news_analysis
                    ),
                )
            )

        except Exception as exc:

            print(
                "  [CONSENSUS ERROR]",
                exc,
            )

            consensus = {}

        results[
            member
        ] = {

            "speech_current_score":
                current["score"],

            "speech_current_label":
                current["label"],

            "speech_sample_count":
                current["sample_count"],

            "news_score":
                news_analysis.get(
                    "news_score"
                ),

            "news_label":
                news_analysis.get(
                    "news_label"
                ),

            "news_count":
                news_analysis.get(
                    "news_count",
                    0,
                ),

            "news_usable_count":
                news_analysis.get(
                    "news_usable_count",
                    0,
                ),

            "news_confidence":
                news_analysis.get(
                    "news_confidence",
                    "LOW",
                ),

            "news_articles":
                news_analysis.get(
                    "news_articles"
                )
                or [],

            "consensus_score":
                consensus.get(
                    "consensus_score"
                ),

            "consensus_label":
                consensus.get(
                    "consensus_label"
                ),

            "cross_check":
                consensus.get(
                    "cross_check"
                ),
        }

        time.sleep(
            NEWS_REQUEST_SLEEP
        )

    return results


# ============================================================
# RECENT SIGNAL
# ============================================================

def build_recent_signals(
    grouped,
    model_results,
    news_results,
):

    results = {}

    for (
        member,
        articles,
    ) in grouped.items():

        model = (
            model_results.get(
                member,
                {}
            )
        )

        news = (
            news_results.get(
                member,
                {}
            )
        )

        model_evidence = (
            model.get(
                "model_evidence"
            )
            or []
        )

        try:

            results[
                member
            ] = (
                calculate_recent_signal(
                    events=articles,
                    news_analysis=news,
                    model_evidence=(
                        model_evidence
                    ),
                    lookback_days=(
                        RECENT_SIGNAL_LOOKBACK_DAYS
                    ),
                )
            )

        except Exception as exc:

            print(
                "[RECENT SIGNAL ERROR]",
                member,
                "|",
                exc,
            )

            results[
                member
            ] = {

                "recent_signal":
                    "INSUFFICIENT",

                "recent_signal_score":
                    None,

                "recent_signal_confidence":
                    "INSUFFICIENT",

                "recent_lookback_days":
                    RECENT_SIGNAL_LOOKBACK_DAYS,

                "aux_speech_score":
                    None,

                "aux_speech_label":
                    "INSUFFICIENT",

                "aux_speech_count":
                    0,

                "aux_speech_evidence":
                    [],

                "recent_news_score":
                    None,

                "recent_news_label":
                    "INSUFFICIENT",

                "recent_news_confidence":
                    "LOW",

                "recent_news_usable_count":
                    0,

                "recent_news_articles":
                    [],
            }

    return results


# ============================================================
# FINAL STANCE
# ============================================================

def build_final_stances(
    model_results,
    recent_results,
):

    results = {}

    members = (
        set(
            model_results.keys()
        )
        |
        set(
            recent_results.keys()
        )
    )

    for member in members:

        model = (
            model_results.get(
                member,
                {}
            )
        )

        recent = (
            recent_results.get(
                member,
                {}
            )
        )

        try:

            results[
                member
            ] = (
                calculate_final_stance(
                    model_result=model,
                    recent_result=recent,
                )
            )

        except Exception as exc:

            print(
                "[FINAL STANCE ERROR]",
                member,
                "|",
                exc,
            )

            results[
                member
            ] = {

                "final_stance":
                    "INSUFFICIENT",

                "final_score":
                    None,

                "final_confidence":
                    "INSUFFICIENT",

                "final_model_weight":
                    0.0,

                "final_recent_weight":
                    0.0,

                "final_signal_conflict":
                    False,

                "final_reason":
                    str(exc),
            }

    return results


# ============================================================
# CHECKS
# ============================================================

def print_model_stance_check(
    model_results,
):

    print()
    print(
        "=" * 90
    )
    print(
        "MODEL STANCE CHECK"
    )
    print(
        "=" * 90
    )

    for member in sorted(
        model_results.keys()
    ):

        result = (
            model_results[
                member
            ]
        )

        print(
            f"{member:<24}",
            "|",
            f"{result.get('model_stance', 'INSUFFICIENT'):<18}",
            "| score=",
            result.get(
                "model_score"
            ),
            "| confidence=",
            result.get(
                "model_confidence"
            ),
            "| evidence=",
            result.get(
                "model_evidence_count",
                0,
            ),
        )


def print_recent_signal_check(
    model_results,
    recent_results,
):

    print()
    print(
        "=" * 110
    )
    print(
        "RECENT SIGNAL CHECK"
    )
    print(
        "=" * 110
    )

    for member in sorted(
        recent_results.keys()
    ):

        recent = (
            recent_results[
                member
            ]
        )

        model = (
            model_results.get(
                member,
                {}
            )
        )

        print(
            f"{member:<24}",
            "| MODEL=",
            f"{model.get('model_stance', 'INSUFFICIENT'):<16}",
            "| RECENT=",
            f"{recent.get('recent_signal', 'INSUFFICIENT'):<16}",
            "| score=",
            recent.get(
                "recent_signal_score"
            ),
            "| conf=",
            recent.get(
                "recent_signal_confidence"
            ),
            "| aux=",
            recent.get(
                "aux_speech_count",
                0,
            ),
            "| news=",
            recent.get(
                "recent_news_usable_count",
                0,
            ),
        )


def print_final_stance_check(
    model_results,
    recent_results,
    final_results,
):

    print()
    print(
        "=" * 145
    )
    print(
        "MODEL / RECENT / FINAL CHECK"
    )
    print(
        "=" * 145
    )

    for member in sorted(
        final_results.keys()
    ):

        model = (
            model_results.get(
                member,
                {}
            )
        )

        recent = (
            recent_results.get(
                member,
                {}
            )
        )

        final = (
            final_results.get(
                member,
                {}
            )
        )

        print(
            f"{member:<24}"
            f" | MODEL={model.get('model_stance', 'INSUFFICIENT'):<16}"
            f" {str(model.get('model_score')):<7}"
            f" | RECENT={recent.get('recent_signal', 'INSUFFICIENT'):<16}"
            f" {str(recent.get('recent_signal_score')):<7}"
            f" | FINAL={final.get('final_stance', 'INSUFFICIENT'):<16}"
            f" {str(final.get('final_score')):<7}"
            f" | CONF={final.get('final_confidence', 'INSUFFICIENT'):<12}"
            f" | W={final.get('final_model_weight', 0):.2f}"
            f"/{final.get('final_recent_weight', 0):.2f}"
            f" | conflict={final.get('final_signal_conflict', False)}"
        )


# ============================================================
# ATTACH MEMBER LEVEL DATA
# ============================================================

def attach_member_level_data(
    events,
    model_results,
    recent_results,
    final_results,
    momentum_results,
    news_results,
):

    final_events = []

    for event in events:

        item = dict(event)

        member = (
            item.get(
                "member_name_en"
            )
        )

        model = (
            model_results.get(
                member,
                {}
            )
        )

        recent = (
            recent_results.get(
                member,
                {}
            )
        )

        final_stance = (
            final_results.get(
                member,
                {}
            )
        )

        momentum = (
            momentum_results.get(
                member,
                {}
            )
        )

        news = (
            news_results.get(
                member,
                {}
            )
        )

        item.update({

            # =================================================
            # MODEL
            # =================================================

            "model_stance":
                model.get(
                    "model_stance",
                    "INSUFFICIENT",
                ),

            "model_score":
                model.get(
                    "model_score"
                ),

            "model_confidence":
                model.get(
                    "model_confidence",
                    "INSUFFICIENT",
                ),

            "model_evidence_count":
                model.get(
                    "model_evidence_count",
                    0,
                ),

            # =================================================
            # RECENT SIGNAL
            # =================================================

            "recent_signal":
                recent.get(
                    "recent_signal",
                    "INSUFFICIENT",
                ),

            "recent_signal_score":
                recent.get(
                    "recent_signal_score"
                ),

            "recent_signal_confidence":
                recent.get(
                    "recent_signal_confidence",
                    "INSUFFICIENT",
                ),

            "recent_lookback_days":
                recent.get(
                    "recent_lookback_days",
                    RECENT_SIGNAL_LOOKBACK_DAYS,
                ),

            "aux_speech_score":
                recent.get(
                    "aux_speech_score"
                ),

            "aux_speech_label":
                recent.get(
                    "aux_speech_label",
                    "INSUFFICIENT",
                ),

            "aux_speech_count":
                recent.get(
                    "aux_speech_count",
                    0,
                ),

            "recent_news_score":
                recent.get(
                    "recent_news_score"
                ),

            "recent_news_label":
                recent.get(
                    "recent_news_label",
                    "INSUFFICIENT",
                ),

            "recent_news_confidence":
                recent.get(
                    "recent_news_confidence",
                    "LOW",
                ),

            "recent_news_usable_count":
                recent.get(
                    "recent_news_usable_count",
                    0,
                ),

            # =================================================
            # FINAL STANCE
            # =================================================

            "final_stance":
                final_stance.get(
                    "final_stance",
                    "INSUFFICIENT",
                ),

            "final_score":
                final_stance.get(
                    "final_score"
                ),

            "final_confidence":
                final_stance.get(
                    "final_confidence",
                    "INSUFFICIENT",
                ),

            "final_model_weight":
                final_stance.get(
                    "final_model_weight",
                    0.0,
                ),

            "final_recent_weight":
                final_stance.get(
                    "final_recent_weight",
                    0.0,
                ),

            "final_signal_conflict":
                final_stance.get(
                    "final_signal_conflict",
                    False,
                ),

            "final_reason":
                final_stance.get(
                    "final_reason",
                    "",
                ),

            # =================================================
            # MOMENTUM
            # =================================================

            "momentum_label":
                momentum.get(
                    "momentum_label",
                    "INSUFFICIENT",
                ),

            "momentum_score":
                momentum.get(
                    "momentum_score"
                ),

            "momentum_confidence":
                momentum.get(
                    "momentum_confidence",
                    "INSUFFICIENT",
                ),

            "momentum_recent_avg":
                momentum.get(
                    "recent_avg"
                ),

            "momentum_previous_avg":
                momentum.get(
                    "previous_avg"
                ),

            "momentum_recent_count":
                momentum.get(
                    "recent_count",
                    0,
                ),

            "momentum_previous_count":
                momentum.get(
                    "previous_count",
                    0,
                ),

            "momentum_total_important_count":
                momentum.get(
                    "total_important_count",
                    0,
                ),

            # =================================================
            # LEGACY CURRENT SPEECH
            # =================================================

            "speech_current_score":
                news.get(
                    "speech_current_score"
                ),

            "speech_current_label":
                news.get(
                    "speech_current_label"
                ),

            "speech_sample_count":
                news.get(
                    "speech_sample_count",
                    0,
                ),

            # =================================================
            # ORIGINAL NEWS
            # =================================================

            "news_score":
                news.get(
                    "news_score"
                ),

            "news_label":
                news.get(
                    "news_label",
                    "INSUFFICIENT",
                ),

            "news_article_count":
                news.get(
                    "news_count",
                    0,
                ),

            "news_usable_count":
                news.get(
                    "news_usable_count",
                    0,
                ),

            "news_confidence":
                news.get(
                    "news_confidence",
                    "LOW",
                ),

            "news_articles":
                news.get(
                    "news_articles"
                )
                or [],

            # =================================================
            # LEGACY CONSENSUS
            # =================================================

            "consensus_score":
                news.get(
                    "consensus_score"
                ),

            "consensus_label":
                news.get(
                    "consensus_label"
                ),

            "cross_check":
                news.get(
                    "cross_check"
                ),
        })

        final_events.append(
            item
        )

    return final_events


# ============================================================
# SAVE FINAL CACHE
# ============================================================

def save_final_cache(
    events,
    official_payload,
    infomax_payload,
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {

        "cache_type":
            "FINAL_EVENTS",

        "updated_at":
            datetime.now()
            .isoformat(
                timespec="seconds"
            ),

        "official_cache_updated_at":
            official_payload.get(
                "updated_at"
            ),

        "infomax_cache_updated_at":
            infomax_payload.get(
                "updated_at"
            ),

        "count":
            len(events),

        "events":
            json_safe(events),
    }

    with open(
        FINAL_CACHE_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return FINAL_CACHE_PATH


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=" * 90
    )
    print(
        "MERGE PIPELINE"
    )
    print(
        "=" * 90
    )

    (
        official_payload,
        official,
    ) = load_cache(
        OFFICIAL_CACHE_PATH
    )

    (
        infomax_payload,
        infomax,
    ) = load_cache(
        INFOMAX_CACHE_PATH
    )

    print(
        "OFFICIAL CACHE:",
        len(official),
    )

    print(
        "INFOMAX CACHE :",
        len(infomax),
    )

    combined = (
        official
        +
        infomax
    )

    print(
        "COMBINED      :",
        len(combined),
    )

    events = (
        deduplicate_events(
            combined,
            similarity_threshold=(
                EVENT_SIMILARITY_THRESHOLD
            ),
            date_tolerance_days=(
                EVENT_DATE_TOLERANCE_DAYS
            ),
        )
    )

    print(
        "EVENTS        :",
        len(events),
    )

    print(
        "MERGED        :",
        (
            len(combined)
            -
            len(events)
        ),
    )

    coverage = Counter(
        item.get(
            "source_coverage"
        )
        or
        "UNKNOWN"
        for item in events
    )

    print()
    print(
        "SOURCE COVERAGE"
    )

    for name in [
        "BOTH",
        "OFFICIAL",
        "INFOMAX",
        "OTHER",
        "UNKNOWN",
    ]:

        print(
            f"{name:<12}: "
            f"{coverage.get(name, 0)}"
        )

    grouped = (
        group_by_member(
            events
        )
    )

    print()
    print(
        "MEMBERS       :",
        len(grouped),
    )

    # ========================================================
    # MODEL
    # ========================================================

    print()
    print(
        "Calculating Model Stance..."
    )

    model_results = (
        build_model_stances(
            grouped
        )
    )

    print_model_stance_check(
        model_results
    )

    # ========================================================
    # MOMENTUM
    # ========================================================

    print()
    print(
        "Calculating Momentum..."
    )

    momentum_results = (
        build_momentum(
            grouped
        )
    )

    # ========================================================
    # NEWS
    # ========================================================

    print()
    print(
        "Running Google News cross-check..."
    )

    news_results = (
        build_news_checks(
            grouped
        )
    )

    # ========================================================
    # RECENT SIGNAL
    # ========================================================

    print()
    print(
        "Calculating Recent Signal..."
    )

    recent_results = (
        build_recent_signals(
            grouped,
            model_results,
            news_results,
        )
    )

    print_recent_signal_check(
        model_results,
        recent_results,
    )

    # ========================================================
    # FINAL STANCE
    # ========================================================

    print()
    print(
        "Calculating Final Stance..."
    )

    final_results = (
        build_final_stances(
            model_results,
            recent_results,
        )
    )

    print_final_stance_check(
        model_results,
        recent_results,
        final_results,
    )

    # ========================================================
    # ATTACH
    # ========================================================

    events = (
        attach_member_level_data(
            events,
            model_results,
            recent_results,
            final_results,
            momentum_results,
            news_results,
        )
    )

    # ========================================================
    # SAVE JSON
    # ========================================================

    final_path = (
        save_final_cache(
            events,
            official_payload,
            infomax_payload,
        )
    )

    # ========================================================
    # EXCEL
    # ========================================================

    try:

        excel_path = (
            save_to_excel(
                events
            )
        )

    except Exception as exc:

        print(
            "[EXCEL ERROR]",
            exc,
        )

        excel_path = None

    # ========================================================
    # COUNTS
    # ========================================================

    model_counts = Counter(
        result.get(
            "model_stance"
        )
        or
        "INSUFFICIENT"
        for result
        in model_results.values()
    )

    recent_counts = Counter(
        result.get(
            "recent_signal"
        )
        or
        "INSUFFICIENT"
        for result
        in recent_results.values()
    )

    final_counts = Counter(
        result.get(
            "final_stance"
        )
        or
        "INSUFFICIENT"
        for result
        in final_results.values()
    )

    final_confidence_counts = Counter(
        result.get(
            "final_confidence"
        )
        or
        "INSUFFICIENT"
        for result
        in final_results.values()
    )

    # ========================================================
    # DONE
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "MERGE DONE"
    )
    print(
        "=" * 90
    )

    print(
        "OFFICIAL :",
        len(official),
    )

    print(
        "INFOMAX  :",
        len(infomax),
    )

    print(
        "COMBINED :",
        len(combined),
    )

    print(
        "EVENTS   :",
        len(events),
    )

    print(
        "BOTH     :",
        coverage.get(
            "BOTH",
            0,
        ),
    )

    print()
    print(
        "MODEL STANCE"
    )

    for label in [
        "HAWKISH",
        "NEUTRAL_HAWKISH",
        "NEUTRAL",
        "NEUTRAL_DOVISH",
        "DOVISH",
        "INSUFFICIENT",
    ]:

        print(
            f"{label:<18}: "
            f"{model_counts.get(label, 0)}"
        )

    print()
    print(
        "RECENT SIGNAL"
    )

    for label in [
        "HAWKISH",
        "NEUTRAL_HAWKISH",
        "NEUTRAL",
        "NEUTRAL_DOVISH",
        "DOVISH",
        "INSUFFICIENT",
    ]:

        print(
            f"{label:<18}: "
            f"{recent_counts.get(label, 0)}"
        )

    print()
    print(
        "FINAL STANCE"
    )

    for label in [
        "HAWKISH",
        "NEUTRAL_HAWKISH",
        "NEUTRAL",
        "NEUTRAL_DOVISH",
        "DOVISH",
        "INSUFFICIENT",
    ]:

        print(
            f"{label:<18}: "
            f"{final_counts.get(label, 0)}"
        )

    print()
    print(
        "FINAL CONFIDENCE"
    )

    for label in [
        "HIGH",
        "MEDIUM",
        "LOW",
        "INSUFFICIENT",
    ]:

        print(
            f"{label:<12}: "
            f"{final_confidence_counts.get(label, 0)}"
        )

    print()
    print(
        "FINAL    :",
        final_path,
    )

    if excel_path:

        print(
            "EXCEL    :",
            excel_path,
        )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    main()