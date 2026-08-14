# official_pipeline.py

from pathlib import Path
from datetime import datetime
import json

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

CACHE_PATH = (
    DATA_DIR
    / "official_cache.json"
)

TARGET_YEAR = 2026

INITIAL_FETCH_BODY = False

BODY_FETCH_LIMIT = None

MAX_WORKERS = 6


# ============================================================
# JSON SAFE
# ============================================================

def json_safe(
    value,
):

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

    return str(
        value
    )


# ============================================================
# SOURCE TYPE
# ============================================================

def assign_official_source_type(
    article,
):

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
# SAVE CACHE
# ============================================================

def save_cache(
    articles,
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {

        "cache_type":
            "OFFICIAL",

        "updated_at":
            datetime.now()
            .isoformat(
                timespec="seconds"
            ),

        "year":
            TARGET_YEAR,

        "count":
            len(
                articles
            ),

        "articles":
            json_safe(
                articles
            ),
    }

    with open(
        CACHE_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return CACHE_PATH


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=" * 90
    )
    print(
        "OFFICIAL PIPELINE"
    )
    print(
        "=" * 90
    )

    # ========================================================
    # 1. CRAWL BOARD
    # ========================================================

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

    # ========================================================
    # 2. CRAWL REGIONAL
    # ========================================================

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

    raw = (
        board
        +
        regional
    )

    raw = [
        assign_official_source_type(
            item
        )
        for item
        in raw
    ]

    print()
    print(
        "BOARD    :",
        len(
            board
        )
    )

    print(
        "REGIONAL :",
        len(
            regional
        )
    )

    print(
        "RAW      :",
        len(
            raw
        )
    )

    # ========================================================
    # 3. MEMBER MATCH
    # ========================================================

    enriched = [
        enrich_with_member(
            article
        )
        for article
        in raw
    ]

    matched_count = sum(
        1
        for item
        in enriched
        if item.get(
            "member_name_en"
        )
    )

    print(
        "MATCHED  :",
        matched_count
    )

    # ========================================================
    # 4. FIRST RELEVANCE PASS
    # ========================================================

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
    # 5. BODY FETCH
    # ========================================================

    print()
    print(
        "Fetching official bodies..."
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

    body_fetched = sum(
        1
        for item
        in with_body
        if item.get(
            "body_fetched"
        )
    )

    body_failed = (
        len(
            with_body
        )
        -
        body_fetched
    )

    # ========================================================
    # 6. FINAL ANALYSIS
    # ========================================================

    processed = []

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

        processed.append(
            item
        )

    # ========================================================
    # 7. OFFICIAL INTERNAL DEDUP
    # ========================================================

    before_dedup = len(
        processed
    )

    processed = (
        deduplicate_articles(
            processed
        )
    )

    # ========================================================
    # 8. CACHE
    # ========================================================

    cache_path = (
        save_cache(
            processed
        )
    )

    high_count = sum(
        1
        for item
        in processed
        if item.get(
            "fomc_relevance"
        )
        == "HIGH"
    )

    medium_count = sum(
        1
        for item
        in processed
        if item.get(
            "fomc_relevance"
        )
        == "MEDIUM"
    )

    print()
    print(
        "=" * 90
    )
    print(
        "OFFICIAL DONE"
    )
    print(
        "=" * 90
    )

    print(
        "RAW          :",
        len(
            raw
        )
    )

    print(
        "BODY FETCHED :",
        body_fetched
    )

    print(
        "BODY FAILED  :",
        body_failed
    )

    print(
        "BEFORE DEDUP :",
        before_dedup
    )

    print(
        "FINAL        :",
        len(
            processed
        )
    )

    print(
        "HIGH         :",
        high_count
    )

    print(
        "MEDIUM       :",
        medium_count
    )

    print(
        "CACHE        :",
        cache_path
    )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    main()