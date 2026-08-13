# test_processors.py

from collections import Counter
from pprint import pprint

from crawlers import (
    crawl_fed_board,
    crawl_regional_fed,
    fetch_article_bodies,
)

from processors import (
    enrich_with_member,
    calculate_fomc_relevance,
    classify_topics,
    score_hawk_dove,
    deduplicate_articles,
)

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
# MAIN
# ============================================================

def main():

    # ========================================================
    # 1. CRAWLING
    # ========================================================

    print()
    print("=" * 90)
    print("1. CRAWLING")
    print("=" * 90)

    try:

        board = crawl_fed_board(
            year=TARGET_YEAR,
            fetch_body=INITIAL_FETCH_BODY,
        )

    except Exception as exc:

        print(
            "[FED BOARD ERROR]",
            exc
        )

        board = []

    try:

        regional = crawl_regional_fed(
            year=TARGET_YEAR,
            fetch_body=INITIAL_FETCH_BODY,
        )

    except Exception as exc:

        print(
            "[REGIONAL ERROR]",
            exc
        )

        regional = []

    articles = (
        board
        + regional
    )

    print()
    print(
        "Fed Board :",
        len(board)
    )

    print(
        "Regional  :",
        len(regional)
    )

    print(
        "RAW TOTAL :",
        len(articles)
    )

    # ========================================================
    # 2. MEMBER MATCHING
    # ========================================================

    print()
    print("=" * 90)
    print("2. MEMBER MATCHING")
    print("=" * 90)

    enriched = [
        enrich_with_member(
            article
        )
        for article
        in articles
    ]

    matched = [
        item
        for item in enriched
        if item.get(
            "member_name_en"
        )
    ]

    unmatched = [
        item
        for item in enriched
        if not item.get(
            "member_name_en"
        )
    ]

    print(
        "MATCHED   :",
        len(matched)
    )

    print(
        "UNMATCHED :",
        len(unmatched)
    )

    # ========================================================
    # 3. FIRST PASS - TITLE BASED
    # ========================================================

    print()
    print("=" * 90)
    print("3. FIRST PASS - TITLE RELEVANCE")
    print("=" * 90)

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
        ] = classify_topics(
            item
        )

        first_pass.append(
            item
        )

    first_counter = Counter(
        item.get(
            "fomc_relevance"
        )
        or "UNKNOWN"
        for item in first_pass
    )

    print(
        "HIGH   :",
        first_counter.get(
            "HIGH",
            0
        )
    )

    print(
        "MEDIUM :",
        first_counter.get(
            "MEDIUM",
            0
        )
    )

    print(
        "LOW    :",
        first_counter.get(
            "LOW",
            0
        )
    )

    # ========================================================
    # 4. ARTICLE BODY FETCH - ALL
    # ========================================================

    print()
    print("=" * 90)
    print("4. ARTICLE BODY FETCH - ALL ARTICLES")
    print("=" * 90)

    with_body = fetch_article_bodies(
        first_pass,

        relevance_levels=[
            "HIGH",
            "MEDIUM",
            "LOW",
        ],

        max_articles=BODY_FETCH_LIMIT,

        max_workers=MAX_WORKERS,
    )

    body_success = sum(
        1
        for item in with_body
        if item.get(
            "body_fetched"
        )
    )

    body_failed = [
        item
        for item in with_body
        if not item.get(
            "body_fetched"
        )
    ]

    print()
    print(
        "BODY FETCHED:",
        body_success
    )

    print(
        "BODY FAILED :",
        len(body_failed)
    )

    # ========================================================
    # 5. FINAL BODY ANALYSIS
    # ========================================================

    print()
    print("=" * 90)
    print("5. FINAL BODY ANALYSIS")
    print("=" * 90)

    processed = []

    for article in with_body:

        item = dict(
            article
        )

        # ----------------------------------------------------
        # relevance
        # ----------------------------------------------------

        item.update(
            calculate_fomc_relevance(
                item
            )
        )

        # ----------------------------------------------------
        # topic
        # ----------------------------------------------------

        item[
            "topics"
        ] = classify_topics(
            item
        )

        # ----------------------------------------------------
        # hawk / dove
        # 문장 단위 분석
        # ----------------------------------------------------

        item.update(
            score_hawk_dove(
                item
            )
        )

        processed.append(
            item
        )

    # ========================================================
    # 6. DEDUPLICATION
    # ========================================================

    print()
    print("=" * 90)
    print("6. DEDUPLICATION")
    print("=" * 90)

    before_dedup = len(
        processed
    )

    processed = deduplicate_articles(
        processed
    )

    after_dedup = len(
        processed
    )

    print(
        "BEFORE DEDUP :",
        before_dedup
    )

    print(
        "AFTER DEDUP  :",
        after_dedup
    )

    print(
        "REMOVED      :",
        before_dedup
        - after_dedup
    )

    # ========================================================
    # 7. FINAL FOMC RELEVANCE
    # ========================================================

    print()
    print("=" * 90)
    print("7. FINAL FOMC RELEVANCE")
    print("=" * 90)

    relevance_counter = Counter(
        item.get(
            "fomc_relevance"
        )
        or "UNKNOWN"
        for item in processed
    )

    for label in [
        "HIGH",
        "MEDIUM",
        "LOW",
        "UNKNOWN",
    ]:

        print(
            f"{label:<10}"
            f"{relevance_counter.get(label, 0):>5}건"
        )

    # ========================================================
    # 8. TOPICS
    # ========================================================

    print()
    print("=" * 90)
    print("8. TOPICS")
    print("=" * 90)

    topic_counter = Counter()

    for item in processed:

        topics = (
            item.get(
                "topics"
            )
            or []
        )

        for topic in topics:

            topic_counter[
                topic
            ] += 1

    for topic, count in (
        topic_counter.most_common()
    ):

        print(
            f"{topic:<25}"
            f"{count:>5}건"
        )

    # ========================================================
    # 9. HAWK / DOVE
    # ========================================================

    print()
    print("=" * 90)
    print("9. HAWK / DOVE")
    print("=" * 90)

    hawk_counter = Counter(
        item.get(
            "hawk_dove_label"
        )
        or "UNKNOWN"
        for item in processed
    )

    hawk_order = [
        "HAWKISH",
        "NEUTRAL_HAWKISH",
        "NEUTRAL",
        "NEUTRAL_DOVISH",
        "DOVISH",
        "UNKNOWN",
    ]

    for label in hawk_order:

        print(
            f"{label:<25}"
            f"{hawk_counter.get(label, 0):>5}건"
        )

    # ========================================================
    # 10. IMPORTANT SAMPLE
    # ========================================================

    important_items = [
        item
        for item in processed
        if item.get(
            "fomc_relevance"
        )
        in [
            "HIGH",
            "MEDIUM",
        ]
    ]

    important_items.sort(
        key=lambda item: (
            item.get(
                "published_at"
            )
            or ""
        ),
        reverse=True
    )

    print()
    print("=" * 90)
    print("10. IMPORTANT ARTICLE SAMPLE")
    print("=" * 90)

    print(
        "HIGH + MEDIUM:",
        len(important_items)
    )

    for item in important_items[:30]:

        pprint({
            "date":
                item.get(
                    "published_at"
                ),

            "member":
                item.get(
                    "member_name_en"
                ),

            "title":
                item.get(
                    "title"
                ),

            "relevance":
                item.get(
                    "fomc_relevance"
                ),

            "relevance_score":
                item.get(
                    "fomc_relevance_score"
                ),

            "topics":
                item.get(
                    "topics"
                ),

            "hawk_dove":
                item.get(
                    "hawk_dove_label"
                ),

            "hawk_score":
                item.get(
                    "hawk_dove_score"
                ),

            "hawk_confidence":
                item.get(
                    "hawk_dove_confidence"
                ),

            "hawkish_score":
                item.get(
                    "hawkish_score"
                ),

            "dovish_score":
                item.get(
                    "dovish_score"
                ),

            "hawk_evidence":
                (
                    item.get(
                        "hawk_evidence_sentences"
                    )
                    or []
                )[:3],

            "dove_evidence":
                (
                    item.get(
                        "dove_evidence_sentences"
                    )
                    or []
                )[:3],

            "text_length":
                len(
                    item.get(
                        "text"
                    )
                    or ""
                ),

            "source":
                item.get(
                    "source"
                ),
        })

        print(
            "-" * 90
        )

    # ========================================================
    # 11. BODY FETCH FAILURES
    # ========================================================

    print()
    print("=" * 90)
    print("11. BODY FETCH FAILURES")
    print("=" * 90)

    print(
        "FAILED:",
        len(body_failed)
    )

    for item in body_failed[:30]:

        pprint({
            "date":
                item.get(
                    "published_at"
                ),

            "member":
                item.get(
                    "member_name_en"
                ),

            "source":
                item.get(
                    "source"
                ),

            "title":
                item.get(
                    "title"
                ),

            "error":
                item.get(
                    "body_fetch_error"
                ),

            "url":
                item.get(
                    "url"
                ),
        })

    # ========================================================
    # 12. UNMATCHED
    # ========================================================

    print()
    print("=" * 90)
    print("12. UNMATCHED")
    print("=" * 90)

    final_unmatched = [
        item
        for item in processed
        if not item.get(
            "member_name_en"
        )
    ]

    print(
        "UNMATCHED:",
        len(final_unmatched)
    )

    for item in final_unmatched:

        pprint({
            "date":
                item.get(
                    "published_at"
                ),

            "speaker_raw":
                item.get(
                    "speaker_raw"
                ),

            "title":
                item.get(
                    "title"
                ),

            "relevance":
                item.get(
                    "fomc_relevance"
                ),

            "hawk_dove":
                item.get(
                    "hawk_dove_label"
                ),

            "url":
                item.get(
                    "url"
                ),
        })

    # ========================================================
    # 13. EXPORT EXCEL
    # ========================================================

    print()
    print("=" * 90)
    print("13. EXPORT EXCEL")
    print("=" * 90)

    try:

        excel_path = save_to_excel(
            processed
        )

        print(
            "EXCEL:",
            excel_path
        )

    except Exception as exc:

        print(
            "[EXCEL EXPORT ERROR]",
            exc
        )

        excel_path = None

    # ========================================================
    # DONE
    # ========================================================

    print()
    print("=" * 90)
    print("DONE")
    print("=" * 90)

    print(
        "RAW          :",
        len(articles)
    )

    print(
        "MATCHED      :",
        len(matched)
    )

    print(
        "UNMATCHED    :",
        len(final_unmatched)
    )

    print(
        "BODY FETCHED :",
        body_success
    )

    print(
        "BODY FAILED  :",
        len(body_failed)
    )

    print(
        "FINAL        :",
        len(processed)
    )

    print(
        "HIGH         :",
        relevance_counter.get(
            "HIGH",
            0
        )
    )

    print(
        "MEDIUM       :",
        relevance_counter.get(
            "MEDIUM",
            0
        )
    )

    if excel_path:

        print(
            "EXCEL        :",
            excel_path
        )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    main()