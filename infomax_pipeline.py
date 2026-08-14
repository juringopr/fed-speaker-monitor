# infomax_pipeline.py

from pathlib import Path
from datetime import datetime, timedelta
import argparse
import json
import time

from crawlers.infomax import (
    crawl_infomax_member_news,
)

from processors.member_matcher import (
    load_members,
)

from processors import (
    calculate_fomc_relevance,
    classify_topics,
    score_hawk_dove,
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
    / "infomax_cache.json"
)

TARGET_YEAR = 2026

MAX_RESULTS_PER_MEMBER_FULL = 20
MAX_RESULTS_PER_MEMBER_INCREMENTAL = 10

# 기본 증분 검색 범위
INCREMENTAL_LOOKBACK_DAYS = 30

REQUEST_SLEEP = 0.10


# ============================================================
# ARGS
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "기존 캐시를 무시하고 "
            "2026년 전체를 다시 수집"
        ),
    )

    parser.add_argument(
        "--days",
        type=int,
        default=(
            INCREMENTAL_LOOKBACK_DAYS
        ),
        help=(
            "증분 업데이트 시 "
            "최근 몇 일까지 다시 확인할지"
        ),
    )

    return parser.parse_args()


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
# ALIASES
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
# DATE HELPERS
# ============================================================

def parse_date(
    value,
):

    if not value:
        return None

    try:

        return datetime.strptime(
            str(value)[:10],
            "%Y-%m-%d",
        )

    except Exception:

        return None


def article_effective_date(
    article,
):

    return (
        parse_date(
            article.get(
                "actual_speech_date"
            )
        )
        or
        parse_date(
            article.get(
                "published_at"
            )
        )
    )


# ============================================================
# CACHE LOAD
# ============================================================

def load_existing_cache():

    if not CACHE_PATH.exists():

        return {
            "cache_type":
                "INFOMAX",

            "updated_at":
                None,

            "year":
                TARGET_YEAR,

            "count":
                0,

            "articles":
                [],
        }

    try:

        with open(
            CACHE_PATH,
            "r",
            encoding="utf-8",
        ) as file:

            payload = json.load(
                file
            )

        if not isinstance(
            payload,
            dict,
        ):

            return {
                "cache_type":
                    "INFOMAX",

                "articles":
                    [],
            }

        payload.setdefault(
            "articles",
            [],
        )

        return payload

    except Exception as exc:

        print(
            "[CACHE LOAD ERROR]",
            exc,
        )

        return {
            "cache_type":
                "INFOMAX",

            "articles":
                [],
        }


# ============================================================
# CACHE SAVE
# ============================================================

def save_cache(
    articles,
    mode,
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {

        "cache_type":
            "INFOMAX",

        "updated_at":
            datetime.now()
            .isoformat(
                timespec="seconds"
            ),

        "year":
            TARGET_YEAR,

        "mode":
            mode,

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
# MEMBER META
# ============================================================

def attach_member_meta(
    article,
    member,
):

    item = dict(
        article
    )

    item.update({

        "member_name_en":
            member.get(
                "name_en"
            ),

        "member_name_ko":
            member.get(
                "name_ko"
            ),

        "member_role_en":
            member.get(
                "role_en"
            ),

        "member_role_ko":
            member.get(
                "role_ko"
            ),

        "member_fed":
            member.get(
                "fed"
            ),

        "member_voter":
            member.get(
                "voter"
            ),

        "member_vote_year":
            member.get(
                "vote_year"
            ),

        "member_priority":
            member.get(
                "priority"
            ),

        "member_match_score":
            100,

        "speaker_raw":
            member.get(
                "name_en"
            ),

        "source":
            "Yonhap Infomax",

        "source_type":
            "INFOMAX",
    })

    return item


# ============================================================
# ANALYZE ARTICLE
# ============================================================

def analyze_article(
    article,
    member,
):

    item = (
        attach_member_meta(
            article,
            member,
        )
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

    return item


# ============================================================
# ARTICLE ID / DEDUP
# ============================================================

def normalize_url(
    value,
):

    return (
        str(
            value
            or
            ""
        )
        .strip()
    )


def article_identity(
    article,
):
    """
    우선 URL로 식별.
    URL 없는 경우 member/date/title fallback.
    """

    url = normalize_url(
        article.get(
            "url"
        )
    )

    if url:

        return (
            "URL|"
            +
            url
        )

    member = str(
        article.get(
            "member_name_en"
        )
        or
        ""
    ).strip()

    date_value = (
        article.get(
            "published_at"
        )
        or
        article.get(
            "actual_speech_date"
        )
        or
        ""
    )

    title = str(
        article.get(
            "title"
        )
        or
        ""
    ).strip()

    return (
        f"FALLBACK|"
        f"{member}|"
        f"{date_value}|"
        f"{title}"
    )


# ============================================================
# MERGE CACHE ARTICLES
# ============================================================

def merge_cached_articles(
    old_articles,
    new_articles,
):
    """
    기존 cache 유지.

    동일 URL이 새로 수집되면
    신규 분석 결과로 교체.
    """

    merged = {}

    for article in (
        old_articles
        or []
    ):

        merged[
            article_identity(
                article
            )
        ] = article

    for article in (
        new_articles
        or []
    ):

        merged[
            article_identity(
                article
            )
        ] = article

    result = list(
        merged.values()
    )

    result.sort(
        key=lambda item: (
            item.get(
                "actual_speech_date"
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

    return result


# ============================================================
# MEMBER-SPECIFIC CUTOFF
# ============================================================

def build_member_cutoffs(
    old_articles,
    lookback_days,
):
    """
    위원별 기존 최신 날짜를 기준으로
    재검색 시작점 계산.

    예:
    기존 최신 기사 = 8/10
    --days 30
    -> 7/11 이후 결과만 신규 후보로 사용
    """

    latest_by_member = {}

    for article in (
        old_articles
        or []
    ):

        member = (
            article.get(
                "member_name_en"
            )
        )

        if not member:
            continue

        date_value = (
            article_effective_date(
                article
            )
        )

        if not date_value:
            continue

        previous = (
            latest_by_member.get(
                member
            )
        )

        if (
            previous is None
            or
            date_value
            >
            previous
        ):

            latest_by_member[
                member
            ] = date_value

    cutoffs = {}

    for member, latest in (
        latest_by_member.items()
    ):

        cutoffs[
            member
        ] = (
            latest
            -
            timedelta(
                days=lookback_days
            )
        )

    return cutoffs


# ============================================================
# SHOULD KEEP NEW RESULT
# ============================================================

def is_inside_incremental_window(
    article,
    cutoff,
):

    if cutoff is None:
        return True

    article_date = (
        article_effective_date(
            article
        )
    )

    if article_date is None:
        return True

    return (
        article_date
        >= cutoff
    )


# ============================================================
# MAIN
# ============================================================

def main():

    args = (
        parse_args()
    )

    full_mode = bool(
        args.full
    )

    lookback_days = max(
        1,
        int(
            args.days
        ),
    )

    mode = (
        "FULL"
        if full_mode
        else
        "INCREMENTAL"
    )

    print()
    print(
        "=" * 90
    )
    print(
        f"INFOMAX PIPELINE - {mode}"
    )
    print(
        "=" * 90
    )

    # ========================================================
    # LOAD OLD CACHE
    # ========================================================

    existing_payload = (
        load_existing_cache()
    )

    existing_articles = (
        existing_payload.get(
            "articles"
        )
        or
        []
    )

    if full_mode:

        base_articles = []

        member_cutoffs = {}

        max_results = (
            MAX_RESULTS_PER_MEMBER_FULL
        )

        print(
            "Existing cache ignored."
        )

    else:

        base_articles = (
            existing_articles
        )

        member_cutoffs = (
            build_member_cutoffs(
                existing_articles,
                lookback_days,
            )
        )

        max_results = (
            MAX_RESULTS_PER_MEMBER_INCREMENTAL
        )

        print(
            "Existing cache:",
            len(
                existing_articles
            )
        )

        print(
            "Lookback days :",
            lookback_days
        )

    # ========================================================
    # MEMBERS
    # ========================================================

    members = (
        load_members()
    )

    total_members = len(
        members
    )

    new_processed = []

    existing_ids = {
        article_identity(
            article
        )
        for article
        in existing_articles
    }

    total_found = 0
    total_window = 0
    total_new = 0
    total_replaced = 0

    # ========================================================
    # MEMBER LOOP
    # ========================================================

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

        if not name_en:
            continue

        aliases = (
            parse_aliases(
                member.get(
                    "aliases"
                )
            )
        )

        cutoff = (
            None
            if full_mode
            else
            member_cutoffs.get(
                name_en
            )
        )

        print()
        print(
            f"[INFOMAX "
            f"{index}/{total_members}] "
            f"{name_en}"
        )

        if cutoff:

            print(
                "  CUTOFF :",
                cutoff.strftime(
                    "%Y-%m-%d"
                )
            )

        else:

            print(
                "  CUTOFF : none"
            )

        # ====================================================
        # CRAWL
        # ====================================================

        try:

            articles = (
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
                        max_results
                    ),

                    year=(
                        TARGET_YEAR
                    ),
                )
            )

        except Exception as exc:

            print(
                "  [ERROR]",
                exc,
            )

            continue

        total_found += len(
            articles
        )

        # ====================================================
        # WINDOW FILTER
        # ====================================================

        articles = [
            article
            for article
            in articles
            if is_inside_incremental_window(
                article,
                cutoff,
            )
        ]

        total_window += len(
            articles
        )

        accepted = 0
        skipped_old = 0

        # ====================================================
        # ANALYZE
        # ====================================================

        for article in articles:

            temp = dict(
                article
            )

            temp[
                "member_name_en"
            ] = name_en

            identity = (
                article_identity(
                    temp
                )
            )

            # FULL 모드는 전부 분석
            # INCREMENTAL에서는 기존 URL이면
            # 재분석해서 replace하도록 둠.
            # 이렇게 해야 hawk_dove 로직 수정도
            # 최근 기사에 반영 가능.
            was_existing = (
                identity
                in existing_ids
            )

            item = (
                analyze_article(
                    article,
                    member,
                )
            )

            new_processed.append(
                item
            )

            accepted += 1

            if was_existing:

                total_replaced += 1

            else:

                total_new += 1

        print(
            "  FOUND   :",
            len(
                articles
            )
        )

        print(
            "  ANALYZED:",
            accepted
        )

        time.sleep(
            REQUEST_SLEEP
        )

    # ========================================================
    # MERGE OLD + NEW
    # ========================================================

    if full_mode:

        final_articles = (
            merge_cached_articles(
                [],
                new_processed,
            )
        )

    else:

        final_articles = (
            merge_cached_articles(
                base_articles,
                new_processed,
            )
        )

    # ========================================================
    # CACHE
    # ========================================================

    cache_path = (
        save_cache(
            final_articles,
            mode,
        )
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    high_count = sum(
        1
        for item
        in final_articles
        if item.get(
            "fomc_relevance"
        )
        == "HIGH"
    )

    medium_count = sum(
        1
        for item
        in final_articles
        if item.get(
            "fomc_relevance"
        )
        == "MEDIUM"
    )

    hawkish_count = sum(
        1
        for item
        in final_articles
        if item.get(
            "hawk_dove_label"
        )
        in [
            "HAWKISH",
            "NEUTRAL_HAWKISH",
        ]
    )

    dovish_count = sum(
        1
        for item
        in final_articles
        if item.get(
            "hawk_dove_label"
        )
        in [
            "DOVISH",
            "NEUTRAL_DOVISH",
        ]
    )

    print()
    print(
        "=" * 90
    )
    print(
        "INFOMAX DONE"
    )
    print(
        "=" * 90
    )

    print(
        "MODE          :",
        mode
    )

    print(
        "OLD CACHE     :",
        len(
            existing_articles
        )
    )

    print(
        "SEARCH FOUND  :",
        total_found
    )

    print(
        "IN WINDOW     :",
        total_window
    )

    print(
        "NEW           :",
        total_new
    )

    print(
        "REANALYZED    :",
        total_replaced
    )

    print(
        "FINAL CACHE   :",
        len(
            final_articles
        )
    )

    print(
        "HIGH          :",
        high_count
    )

    print(
        "MEDIUM        :",
        medium_count
    )

    print(
        "HAWKISH       :",
        hawkish_count
    )

    print(
        "DOVISH        :",
        dovish_count
    )

    print(
        "CACHE         :",
        cache_path
    )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    main()