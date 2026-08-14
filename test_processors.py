# test_processors.py

from collections import Counter
from pprint import pprint

import time


# ============================================================
# CRAWLERS
# ============================================================

from crawlers import (
    crawl_fed_board,
    crawl_regional_fed,
    fetch_article_bodies,
)

from crawlers.news import (
    search_member_news,
)

from crawlers.infomax import (
    crawl_infomax_member_news,
)


# ============================================================
# PROCESSORS
# ============================================================

from processors import (
    enrich_with_member,
    calculate_fomc_relevance,
    classify_topics,
    score_hawk_dove,
    deduplicate_articles,

    analyze_member_news,
    calculate_consensus,

    calculate_momentum,

    deduplicate_events,
)

from processors.member_matcher import (
    load_members,
)


# ============================================================
# EXPORT
# ============================================================

from exporters import (
    save_to_excel,
)


# ============================================================
# CONFIG
# ============================================================

TARGET_YEAR = 2026

INITIAL_FETCH_BODY = False

BODY_FETCH_LIMIT = None

MAX_WORKERS = 6


# ============================================================
# INFOMAX CONFIG
# ============================================================

INFOMAX_ENABLED = True

INFOMAX_MAX_RESULTS_PER_MEMBER = 20

INFOMAX_REQUEST_SLEEP = 0.30


# ============================================================
# GOOGLE NEWS CONFIG
# ============================================================

NEWS_LOOKBACK_DAYS = 90

NEWS_MAX_RESULTS = 10

NEWS_REQUEST_SLEEP = 0.5

CURRENT_STANCE_N = 5


# ============================================================
# EVENT DEDUP CONFIG
# ============================================================

EVENT_SIMILARITY_THRESHOLD = 0.32

EVENT_DATE_TOLERANCE_DAYS = 1


# ============================================================
# SCORE -> LABEL
# ============================================================

def score_to_label(
    score,
):

    if score is None:
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
# MEMBER ALIASES
# ============================================================

def parse_aliases(
    value,
):

    if value is None:
        return []

    value = str(
        value
    ).strip()

    if not value:
        return []

    return [
        item.strip()
        for item
        in value.split("|")
        if item.strip()
    ]


# ============================================================
# OFFICIAL SOURCE TYPE
# ============================================================

def assign_official_source_type(
    article,
):
    """
    기존 공식 크롤러 결과에 source_type이 없을 수 있으므로
    event dedup 전에 명시적으로 붙인다.
    """

    item = dict(
        article
    )

    if item.get(
        "source_type"
    ):

        return item

    source = str(
        item.get(
            "source"
        )
        or
        ""
    ).lower()

    url = str(
        item.get(
            "url"
        )
        or
        ""
    ).lower()

    # Board
    if (
        "federalreserve.gov"
        in url
        or
        "board of governors"
        in source
    ):

        item[
            "source_type"
        ] = "FED_BOARD"

    else:

        item[
            "source_type"
        ] = "REGIONAL_FED"

    return item


# ============================================================
# CURRENT SPEECH STANCE
# ============================================================

def calculate_speaker_speech_stance(
    articles,
):
    """
    현재 Event Dataset에서
    최근 HIGH/MEDIUM 최대 5건의 Hawk/Dove 평균.

    따라서 Event Dedup 이후에는
    Official + Infomax 보완 발언이 함께 반영될 수 있음.
    """

    if not articles:

        return {
            "speech_score":
                0.0,

            "speech_label":
                "NEUTRAL",

            "speech_sample_count":
                0,
        }

    articles = sorted(
        articles,
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

    important = [
        item
        for item
        in articles
        if item.get(
            "fomc_relevance"
        )
        in [
            "HIGH",
            "MEDIUM",
        ]
    ]

    recent = important[
        :CURRENT_STANCE_N
    ]

    scores = []

    for item in recent:

        value = (
            item.get(
                "hawk_dove_score"
            )
        )

        try:

            if value is not None:

                scores.append(
                    float(
                        value
                    )
                )

        except (
            TypeError,
            ValueError,
        ):

            continue

    if scores:

        speech_score = (
            sum(
                scores
            )
            /
            len(
                scores
            )
        )

    else:

        speech_score = 0.0

    speech_score = round(
        speech_score,
        2,
    )

    return {

        "speech_score":
            speech_score,

        "speech_label":
            score_to_label(
                speech_score
            ),

        "speech_sample_count":
            len(
                scores
            ),
    }


# ============================================================
# GROUP ARTICLES
# ============================================================

def group_articles_by_member(
    articles,
):

    grouped = {}

    for item in articles:

        member = (
            item.get(
                "member_name_en"
            )
        )

        if not member:
            continue

        grouped.setdefault(
            member,
            []
        )

        grouped[
            member
        ].append(
            item
        )

    return grouped


# ============================================================
# INFOMAX CRAWLING
# ============================================================

def crawl_all_infomax_members():
    """
    fed_members.csv에 있는 위원을 기준으로
    2026년 Infomax 통화정책 기사 수집.
    """

    if not INFOMAX_ENABLED:
        return []

    print()
    print(
        "=" * 90
    )
    print(
        "7. INFOMAX CRAWLING"
    )
    print(
        "=" * 90
    )

    members = (
        load_members()
    )

    results = []

    total_members = len(
        members
    )

    for index, member in enumerate(
        members,
        start=1,
    ):

        name_en = (
            member.get(
                "name_en"
            )
        )

        name_ko = (
            member.get(
                "name_ko"
            )
        )

        aliases = (
            parse_aliases(
                member.get(
                    "aliases"
                )
            )
        )

        if not name_en:
            continue

        print()
        print(
            f"[INFOMAX MEMBER "
            f"{index}/{total_members}] "
            f"{name_en}"
        )

        try:

            items = (
                crawl_infomax_member_news(

                    member_name_en=(
                        name_en
                    ),

                    member_name_ko=(
                        name_ko
                    ),

                    aliases=(
                        aliases
                    ),

                    max_results=(
                        INFOMAX_MAX_RESULTS_PER_MEMBER
                    ),

                    year=(
                        TARGET_YEAR
                    ),
                )
            )

        except Exception as exc:

            print(
                "[INFOMAX MEMBER FAIL]",
                name_en,
                "|",
                exc,
            )

            items = []

        # ====================================================
        # MEMBER META 보강
        # ====================================================

        for article in items:

            item = dict(
                article
            )

            item[
                "member_name_en"
            ] = (
                name_en
            )

            item[
                "member_name_ko"
            ] = (
                name_ko
            )

            item[
                "member_role_en"
            ] = (
                member.get(
                    "role_en"
                )
            )

            item[
                "member_role_ko"
            ] = (
                member.get(
                    "role_ko"
                )
            )

            item[
                "member_fed"
            ] = (
                member.get(
                    "fed"
                )
            )

            item[
                "member_voter"
            ] = (
                member.get(
                    "voter"
                )
            )

            item[
                "member_vote_year"
            ] = (
                member.get(
                    "vote_year"
                )
            )

            item[
                "member_priority"
            ] = (
                member.get(
                    "priority"
                )
            )

            item[
                "member_match_score"
            ] = 100

            item[
                "source_type"
            ] = "INFOMAX"

            item[
                "source"
            ] = "Yonhap Infomax"

            results.append(
                item
            )

        print(
            "  FOUND:",
            len(
                items
            )
        )

        time.sleep(
            INFOMAX_REQUEST_SLEEP
        )

    print()
    print(
        "INFOMAX RAW TOTAL:",
        len(
            results
        )
    )

    return results


# ============================================================
# PROCESS INFOMAX
# ============================================================

def process_infomax_articles(
    articles,
):

    print()
    print(
        "=" * 90
    )
    print(
        "8. INFOMAX ANALYSIS"
    )
    print(
        "=" * 90
    )

    processed = []

    for article in articles:

        item = dict(
            article
        )

        # ====================================================
        # RELEVANCE
        # ====================================================

        item.update(
            calculate_fomc_relevance(
                item
            )
        )

        # ====================================================
        # TOPICS
        # ====================================================

        item[
            "topics"
        ] = (
            classify_topics(
                item
            )
        )

        # ====================================================
        # HAWK / DOVE
        # ====================================================

        item.update(
            score_hawk_dove(
                item
            )
        )

        processed.append(
            item
        )

    relevance_counter = Counter(
        item.get(
            "fomc_relevance"
        )
        or
        "UNKNOWN"
        for item
        in processed
    )

    print(
        "INFOMAX FINAL :",
        len(
            processed
        )
    )

    print(
        "INFOMAX HIGH  :",
        relevance_counter.get(
            "HIGH",
            0,
        )
    )

    print(
        "INFOMAX MEDIUM:",
        relevance_counter.get(
            "MEDIUM",
            0,
        )
    )

    print(
        "INFOMAX LOW   :",
        relevance_counter.get(
            "LOW",
            0,
        )
    )

    return processed


# ============================================================
# MOMENTUM
# ============================================================

def build_momentum_results(
    processed,
):

    print()
    print(
        "=" * 90
    )
    print(
        "13. MOMENTUM ANALYSIS"
    )
    print(
        "=" * 90
    )

    grouped = (
        group_articles_by_member(
            processed
        )
    )

    member_results = {}

    for (
        member_name,
        member_articles,
    ) in grouped.items():

        result = (
            calculate_momentum(
                member_articles
            )
        )

        member_results[
            member_name
        ] = result

        print(
            f"{member_name:<25}"
            f" Momentum="
            f"{str(result.get('momentum_label')):<25}"
            f" Score="
            f"{str(result.get('momentum_score')):<8}"
            f" Confidence="
            f"{result.get('momentum_confidence')}"
        )

    return member_results


# ============================================================
# ATTACH MOMENTUM
# ============================================================

def attach_momentum_results(
    articles,
    member_results,
):

    results = []

    for article in articles:

        item = dict(
            article
        )

        member = (
            item.get(
                "member_name_en"
            )
        )

        momentum = (
            member_results.get(
                member
            )
        )

        if not momentum:

            item.update({

                "momentum_score":
                    None,

                "momentum_label":
                    "INSUFFICIENT",

                "momentum_confidence":
                    "INSUFFICIENT",

                "momentum_recent_avg":
                    None,

                "momentum_previous_avg":
                    None,

                "momentum_recent_count":
                    0,

                "momentum_previous_count":
                    0,

                "momentum_total_important_count":
                    0,
            })

        else:

            item.update({

                "momentum_score":
                    momentum.get(
                        "momentum_score"
                    ),

                "momentum_label":
                    momentum.get(
                        "momentum_label"
                    ),

                "momentum_confidence":
                    momentum.get(
                        "momentum_confidence"
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
            })

        results.append(
            item
        )

    return results


# ============================================================
# GOOGLE NEWS CROSS CHECK
# ============================================================

def build_news_cross_checks(
    processed,
):

    print()
    print(
        "=" * 90
    )
    print(
        "14. GOOGLE NEWS CROSS CHECK"
    )
    print(
        "=" * 90
    )

    grouped = (
        group_articles_by_member(
            processed
        )
    )

    member_results = {}

    total = len(
        grouped
    )

    for index, (
        member_name,
        member_articles,
    ) in enumerate(
        grouped.items(),
        start=1,
    ):

        # ====================================================
        # OFFICIAL + INFOMAX EVENT STANCE
        # ====================================================

        speech = (
            calculate_speaker_speech_stance(
                member_articles
            )
        )

        print()
        print(
            f"[NEWS {index}/{total}] "
            f"{member_name}"
        )

        print(
            "  Base:",
            speech[
                "speech_label"
            ],
            speech[
                "speech_score"
            ],
        )

        # ====================================================
        # GOOGLE NEWS
        # ====================================================

        try:

            news_items = (
                search_member_news(
                    member_name,
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

        # ====================================================
        # CONSENSUS
        # ====================================================

        consensus = (
            calculate_consensus(

                speech_score=(
                    speech[
                        "speech_score"
                    ]
                ),

                speech_label=(
                    speech[
                        "speech_label"
                    ]
                ),

                news_analysis=(
                    news_analysis
                ),
            )
        )

        consensus[
            "news_article_count"
        ] = (
            news_analysis.get(
                "news_count",
                0,
            )
        )

        consensus[
            "news_usable_count"
        ] = (
            news_analysis.get(
                "news_usable_count",
                0,
            )
        )

        consensus[
            "speech_sample_count"
        ] = (
            speech[
                "speech_sample_count"
            ]
        )

        member_results[
            member_name
        ] = consensus

        print(
            "  News :",
            consensus.get(
                "news_label"
            ),
            consensus.get(
                "news_score"
            ),
            "| confidence:",
            consensus.get(
                "news_confidence"
            ),
        )

        print(
            "  Final:",
            consensus.get(
                "consensus_label"
            ),
            consensus.get(
                "consensus_score"
            ),
        )

        print(
            "  Check:",
            consensus.get(
                "cross_check"
            ),
        )

        time.sleep(
            NEWS_REQUEST_SLEEP
        )

    return member_results


# ============================================================
# ATTACH NEWS
# ============================================================

def attach_cross_checks(
    articles,
    member_results,
):

    results = []

    for article in articles:

        item = dict(
            article
        )

        member = (
            item.get(
                "member_name_en"
            )
        )

        cross = (
            member_results.get(
                member
            )
        )

        if not cross:

            item.update({

                "speech_current_score":
                    None,

                "speech_current_label":
                    None,

                "speech_sample_count":
                    0,

                "news_score":
                    None,

                "news_label":
                    "INSUFFICIENT",

                "news_article_count":
                    0,

                "news_usable_count":
                    0,

                "news_cluster_count":
                    0,

                "news_confidence":
                    "LOW",

                "consensus_score":
                    None,

                "consensus_label":
                    None,

                "cross_check":
                    "NEWS_INSUFFICIENT",

                "news_clusters":
                    [],
            })

        else:

            item.update({

                "speech_current_score":
                    cross.get(
                        "speech_score"
                    ),

                "speech_current_label":
                    cross.get(
                        "speech_label"
                    ),

                "speech_sample_count":
                    cross.get(
                        "speech_sample_count",
                        0,
                    ),

                "news_score":
                    cross.get(
                        "news_score"
                    ),

                "news_label":
                    cross.get(
                        "news_label"
                    ),

                "news_article_count":
                    cross.get(
                        "news_article_count",
                        0,
                    ),

                "news_usable_count":
                    cross.get(
                        "news_usable_count",
                        0,
                    ),

                "news_cluster_count":
                    cross.get(
                        "news_cluster_count",
                        0,
                    ),

                "news_confidence":
                    cross.get(
                        "news_confidence",
                        "LOW",
                    ),

                "consensus_score":
                    cross.get(
                        "consensus_score"
                    ),

                "consensus_label":
                    cross.get(
                        "consensus_label"
                    ),

                "cross_check":
                    cross.get(
                        "cross_check"
                    ),

                "news_clusters":
                    cross.get(
                        "news_clusters"
                    )
                    or [],
            })

        results.append(
            item
        )

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # 1. OFFICIAL CRAWLING
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "1. OFFICIAL CRAWLING"
    )
    print(
        "=" * 90
    )

    try:

        board = (
            crawl_fed_board(
                year=TARGET_YEAR,
                fetch_body=(
                    INITIAL_FETCH_BODY
                ),
            )
        )

    except Exception as exc:

        print(
            "[FED BOARD ERROR]",
            exc,
        )

        board = []

    try:

        regional = (
            crawl_regional_fed(
                year=TARGET_YEAR,
                fetch_body=(
                    INITIAL_FETCH_BODY
                ),
            )
        )

    except Exception as exc:

        print(
            "[REGIONAL ERROR]",
            exc,
        )

        regional = []

    official_raw = (
        board
        +
        regional
    )

    official_raw = [
        assign_official_source_type(
            item
        )
        for item
        in official_raw
    ]

    print(
        "Fed Board :",
        len(
            board
        )
    )

    print(
        "Regional  :",
        len(
            regional
        )
    )

    print(
        "RAW TOTAL :",
        len(
            official_raw
        )
    )

    # ========================================================
    # 2. MEMBER MATCHING
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "2. MEMBER MATCHING"
    )
    print(
        "=" * 90
    )

    enriched = [
        enrich_with_member(
            article
        )
        for article
        in official_raw
    ]

    matched = [
        item
        for item
        in enriched
        if item.get(
            "member_name_en"
        )
    ]

    unmatched = [
        item
        for item
        in enriched
        if not item.get(
            "member_name_en"
        )
    ]

    print(
        "MATCHED   :",
        len(
            matched
        )
    )

    print(
        "UNMATCHED :",
        len(
            unmatched
        )
    )

    # ========================================================
    # 3. FIRST PASS
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "3. OFFICIAL FIRST PASS"
    )
    print(
        "=" * 90
    )

    first_pass = []

    for article in enriched:

        item = dict(
            article
        )

        item.update(
            calculate_fomc_relevance(
                item
            )
        )

        item[
            "topics"
        ] = (
            classify_topics(
                item
            )
        )

        first_pass.append(
            item
        )

    # ========================================================
    # 4. BODY FETCH
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "4. OFFICIAL BODY FETCH"
    )
    print(
        "=" * 90
    )

    with_body = (
        fetch_article_bodies(

            first_pass,

            relevance_levels=[
                "HIGH",
                "MEDIUM",
                "LOW",
            ],

            max_articles=(
                BODY_FETCH_LIMIT
            ),

            max_workers=(
                MAX_WORKERS
            ),
        )
    )

    body_success = sum(
        1
        for item
        in with_body
        if item.get(
            "body_fetched"
        )
    )

    body_failed = [
        item
        for item
        in with_body
        if not item.get(
            "body_fetched"
        )
    ]

    print(
        "BODY FETCHED:",
        body_success
    )

    print(
        "BODY FAILED :",
        len(
            body_failed
        )
    )

    # ========================================================
    # 5. OFFICIAL ANALYSIS
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "5. OFFICIAL FINAL ANALYSIS"
    )
    print(
        "=" * 90
    )

    official_processed = []

    for article in with_body:

        item = dict(
            article
        )

        item.update(
            calculate_fomc_relevance(
                item
            )
        )

        item[
            "topics"
        ] = (
            classify_topics(
                item
            )
        )

        item.update(
            score_hawk_dove(
                item
            )
        )

        official_processed.append(
            item
        )

    # ========================================================
    # 6. OFFICIAL DEDUP
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "6. OFFICIAL DEDUPLICATION"
    )
    print(
        "=" * 90
    )

    before = len(
        official_processed
    )

    official_processed = (
        deduplicate_articles(
            official_processed
        )
    )

    print(
        "BEFORE:",
        before
    )

    print(
        "AFTER :",
        len(
            official_processed
        )
    )

    # ========================================================
    # 7. INFOMAX CRAWL
    # ========================================================

    infomax_raw = (
        crawl_all_infomax_members()
    )

    # ========================================================
    # 8. INFOMAX ANALYSIS
    # ========================================================

    infomax_processed = (
        process_infomax_articles(
            infomax_raw
        )
    )

    # ========================================================
    # 9. COMBINE OFFICIAL + INFOMAX
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "9. COMBINE OFFICIAL + INFOMAX"
    )
    print(
        "=" * 90
    )

    combined = (
        official_processed
        +
        infomax_processed
    )

    print(
        "OFFICIAL:",
        len(
            official_processed
        )
    )

    print(
        "INFOMAX :",
        len(
            infomax_processed
        )
    )

    print(
        "COMBINED:",
        len(
            combined
        )
    )

    # ========================================================
    # 10. EVENT DEDUP
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "10. EVENT DEDUPLICATION"
    )
    print(
        "=" * 90
    )

    processed = (
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
        "BEFORE EVENT DEDUP:",
        len(
            combined
        )
    )

    print(
        "AFTER EVENT DEDUP :",
        len(
            processed
        )
    )

    print(
        "MERGED EVENTS     :",
        (
            len(
                combined
            )
            -
            len(
                processed
            )
        )
    )

    # ========================================================
    # 11. SOURCE COVERAGE
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "11. SOURCE COVERAGE"
    )
    print(
        "=" * 90
    )

    coverage_counter = Counter(
        item.get(
            "source_coverage"
        )
        or
        "UNKNOWN"
        for item
        in processed
    )

    for label in [
        "BOTH",
        "OFFICIAL",
        "INFOMAX",
        "OTHER",
        "UNKNOWN",
    ]:

        print(
            f"{label:<12}"
            f"{coverage_counter.get(label, 0):>5}"
        )

    # ========================================================
    # 12. FINAL ANALYSIS COUNTS
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "12. FINAL EVENT DATASET"
    )
    print(
        "=" * 90
    )

    relevance_counter = Counter(
        item.get(
            "fomc_relevance"
        )
        or
        "UNKNOWN"
        for item
        in processed
    )

    hawk_counter = Counter(
        item.get(
            "hawk_dove_label"
        )
        or
        "UNKNOWN"
        for item
        in processed
    )

    print(
        "FINAL:",
        len(
            processed
        )
    )

    print(
        "HIGH:",
        relevance_counter.get(
            "HIGH",
            0,
        )
    )

    print(
        "MEDIUM:",
        relevance_counter.get(
            "MEDIUM",
            0,
        )
    )

    print(
        "LOW:",
        relevance_counter.get(
            "LOW",
            0,
        )
    )

    print()

    for label in [
        "HAWKISH",
        "NEUTRAL_HAWKISH",
        "NEUTRAL",
        "NEUTRAL_DOVISH",
        "DOVISH",
    ]:

        print(
            f"{label:<25}"
            f"{hawk_counter.get(label, 0):>5}"
        )

    # ========================================================
    # 13. MOMENTUM
    # ========================================================

    momentum_results = (
        build_momentum_results(
            processed
        )
    )

    processed = (
        attach_momentum_results(
            processed,
            momentum_results,
        )
    )

    # ========================================================
    # 14. GOOGLE NEWS CROSS CHECK
    # ========================================================

    member_cross_checks = (
        build_news_cross_checks(
            processed
        )
    )

    # ========================================================
    # 15. ATTACH CROSS CHECK
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "15. ATTACH NEWS CONSENSUS"
    )
    print(
        "=" * 90
    )

    processed = (
        attach_cross_checks(
            processed,
            member_cross_checks,
        )
    )

    # ========================================================
    # 16. SCHMID CHECK
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "16. JEFFREY SCHMID CHECK"
    )
    print(
        "=" * 90
    )

    schmid_items = [
        item
        for item
        in processed
        if item.get(
            "member_name_en"
        )
        == "Jeffrey Schmid"
    ]

    schmid_items = sorted(
        schmid_items,
        key=lambda item: (
            item.get(
                "published_at"
            )
            or
            ""
        ),
        reverse=True,
    )

    print(
        "SCHMID EVENTS:",
        len(
            schmid_items
        )
    )

    for item in schmid_items:

        pprint({

            "date":
                item.get(
                    "published_at"
                ),

            "title":
                item.get(
                    "title"
                ),

            "coverage":
                item.get(
                    "source_coverage"
                ),

            "sources":
                item.get(
                    "event_sources"
                ),

            "relevance":
                item.get(
                    "fomc_relevance"
                ),

            "stance":
                item.get(
                    "hawk_dove_label"
                ),

            "score":
                item.get(
                    "hawk_dove_score"
                ),

            "event_id":
                item.get(
                    "event_id"
                ),
        })

    # ========================================================
    # 17. MEMBER SUMMARY
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "17. MEMBER SUMMARY"
    )
    print(
        "=" * 90
    )

    grouped = (
        group_articles_by_member(
            processed
        )
    )

    for member_name in sorted(
        grouped.keys()
    ):

        member_articles = (
            grouped[
                member_name
            ]
        )

        speech = (
            calculate_speaker_speech_stance(
                member_articles
            )
        )

        momentum = (
            momentum_results.get(
                member_name,
                {}
            )
        )

        cross = (
            member_cross_checks.get(
                member_name,
                {}
            )
        )

        coverages = {
            item.get(
                "source_coverage"
            )
            for item
            in member_articles
            if item.get(
                "source_coverage"
            )
        }

        print(
            f"{member_name:<25}"
            f" Base={str(speech.get('speech_label')):<18}"
            f" Momentum={str(momentum.get('momentum_label')):<25}"
            f" News={str(cross.get('news_label')):<18}"
            f" Final={str(cross.get('consensus_label')):<18}"
            f" Sources={','.join(sorted(coverages))}"
        )

    # ========================================================
    # 18. EXPORT
    # ========================================================

    print()
    print(
        "=" * 90
    )
    print(
        "18. EXPORT EXCEL"
    )
    print(
        "=" * 90
    )

    try:

        excel_path = (
            save_to_excel(
                processed
            )
        )

        print(
            "EXCEL:",
            excel_path
        )

    except Exception as exc:

        print(
            "[EXCEL EXPORT ERROR]",
            exc,
        )

        excel_path = None

    # ========================================================
    # DONE
    # ========================================================

    final_unmatched = [
        item
        for item
        in processed
        if not item.get(
            "member_name_en"
        )
    ]

    print()
    print(
        "=" * 90
    )
    print(
        "DONE"
    )
    print(
        "=" * 90
    )

    print(
        "OFFICIAL RAW  :",
        len(
            official_raw
        )
    )

    print(
        "INFOMAX RAW   :",
        len(
            infomax_raw
        )
    )

    print(
        "COMBINED      :",
        len(
            combined
        )
    )

    print(
        "EVENT FINAL   :",
        len(
            processed
        )
    )

    print(
        "MATCHED       :",
        (
            len(
                processed
            )
            -
            len(
                final_unmatched
            )
        )
    )

    print(
        "UNMATCHED     :",
        len(
            final_unmatched
        )
    )

    print(
        "BODY FETCHED  :",
        body_success
    )

    print(
        "BODY FAILED   :",
        len(
            body_failed
        )
    )

    print(
        "HIGH          :",
        relevance_counter.get(
            "HIGH",
            0,
        )
    )

    print(
        "MEDIUM        :",
        relevance_counter.get(
            "MEDIUM",
            0,
        )
    )

    print(
        "MOMENTUM      :",
        len(
            momentum_results
        )
    )

    print(
        "SPEAKERS NEWS :",
        len(
            member_cross_checks
        )
    )

    print(
        "BOTH          :",
        coverage_counter.get(
            "BOTH",
            0,
        )
    )

    print(
        "OFFICIAL ONLY :",
        coverage_counter.get(
            "OFFICIAL",
            0,
        )
    )

    print(
        "INFOMAX ONLY  :",
        coverage_counter.get(
            "INFOMAX",
            0,
        )
    )

    if excel_path:

        print(
            "EXCEL         :",
            excel_path
        )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    main()