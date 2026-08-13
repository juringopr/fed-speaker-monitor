# crawlers/regional_fed.py

import re
from pathlib import Path

import pandas as pd

from .regional import (
    REGIONAL_ADAPTERS,
)


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "fed_members.csv"
)


# ============================================================
# LOAD MEMBERS
# ============================================================

def load_members():

    if not DATA_PATH.exists():

        raise FileNotFoundError(
            f"fed_members.csv를 찾을 수 없습니다: "
            f"{DATA_PATH}"
        )

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp949",
        "euc-kr",
    ]

    last_error = None

    for encoding in encodings:

        try:

            df = pd.read_csv(
                DATA_PATH,
                encoding=encoding,
            )

            df = df.where(
                pd.notnull(df),
                None,
            )

            return df

        except UnicodeDecodeError as exc:

            last_error = exc

    if last_error:
        raise last_error

    raise RuntimeError(
        "fed_members.csv를 읽지 못했습니다."
    )


# ============================================================
# DATE YEAR
# ============================================================

def _extract_year(
    published_at
):
    """
    YYYY-MM-DD → YYYY
    """

    if not published_at:
        return None

    text = str(
        published_at
    ).strip()

    match = re.search(
        r"\b(20\d{2})\b",
        text,
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


# ============================================================
# URL YEAR
# ============================================================

def _extract_year_from_url(
    url
):
    """
    URL에서 연도 추출.

    지원 예:

    /2026/
    _20260521
    20260521
    260519-...
    """

    if not url:
        return None

    text = str(
        url
    )

    # ========================================================
    # 1. 4자리 year
    # ========================================================

    match = re.search(
        r"(?<!\d)"
        r"(20\d{2})"
        r"(?!\d)",
        text,
    )

    if match:

        return int(
            match.group(1)
        )

    # ========================================================
    # 2. YYYYMMDD
    # ========================================================

    match = re.search(
        r"(?<!\d)"
        r"(20\d{2})"
        r"\d{4}"
        r"(?!\d)",
        text,
    )

    if match:

        return int(
            match.group(1)
        )

    # ========================================================
    # 3. YYMMDD
    #
    # Philadelphia style:
    # 260519-...
    # ========================================================

    match = re.search(
        r"(?<!\d)"
        r"(\d{2})"
        r"(\d{2})"
        r"(\d{2})"
        r"(?!\d)",
        text,
    )

    if match:

        yy = int(
            match.group(1)
        )

        mm = int(
            match.group(2)
        )

        dd = int(
            match.group(3)
        )

        if (
            1 <= mm <= 12
            and
            1 <= dd <= 31
        ):

            return (
                2000
                + yy
            )

    return None


# ============================================================
# QUALITY SCORE
# ============================================================

def _quality_score(
    item
):
    """
    같은 URL이 중복으로 들어왔을 때
    정보가 더 많은 결과를 선택.
    """

    score = 0

    if item.get(
        "published_at"
    ):
        score += 2

    if item.get(
        "speaker_raw"
    ):
        score += 2

    if item.get(
        "title"
    ):
        score += 1

    text = (
        item.get(
            "text"
        )
        or ""
    )

    if text:
        score += 2

    if len(text) >= 500:
        score += 2

    return score


# ============================================================
# NORMALIZE ITEM
# ============================================================

def _normalize_item(
    item,
    member,
    fed,
):
    """
    adapter가 일부 필드를 비워서 반환해도
    최소 필드 보완.
    """

    result = dict(
        item
    )

    if not result.get(
        "source"
    ):

        result[
            "source"
        ] = fed

    if not result.get(
        "source_type"
    ):

        result[
            "source_type"
        ] = "OFFICIAL"

    if not result.get(
        "speaker_raw"
    ):

        result[
            "speaker_raw"
        ] = member.get(
            "name_en"
        )

    if result.get(
        "text"
    ) is None:

        result[
            "text"
        ] = ""

    return result


# ============================================================
# MAIN
# ============================================================

def crawl_regional_fed(
    fetch_body=False,
    year=None,
):
    """
    Regional Federal Reserve speeches 수집.

    처리 원칙
    ----------------------------------------------------------
    1. 각 지역 Fed adapter 독립 실행
    2. 특정 사이트 timeout/오류가 나도 전체 crawl 계속
    3. published_at이 있으면 year 기준 필터
    4. published_at이 없으면 URL에서 year 추출
    5. URL에서도 year를 판별 못 하면 버리지 않고 보존
    6. 동일 URL은 quality가 높은 결과 하나만 유지
    """

    members = load_members()

    results = []

    # ========================================================
    # MEMBER LOOP
    # ========================================================

    for _, row in members.iterrows():

        member = (
            row.to_dict()
        )

        name_en = (
            str(
                member.get(
                    "name_en"
                )
                or ""
            )
            .strip()
        )

        fed = (
            str(
                member.get(
                    "fed"
                )
                or ""
            )
            .strip()
        )

        if not name_en:
            continue

        if not fed:
            continue

        # ====================================================
        # Board는 fed_board.py에서 처리
        # ====================================================

        if fed == "Board of Governors":
            continue

        # ====================================================
        # ADAPTER
        # ====================================================

        adapter_class = (
            REGIONAL_ADAPTERS.get(
                fed
            )
        )

        if adapter_class is None:

            print(
                f"[SKIP] "
                f"{name_en} "
                f"({fed}) "
                f"- adapter 없음"
            )

            continue

        # ====================================================
        # CRAWL
        # ====================================================

        try:

            adapter = adapter_class(
                member=member,
                fetch_body=fetch_body,
            )

            items = (
                adapter.crawl()
                or []
            )

            print(
                f"[OK] "
                f"{name_en} "
                f"({fed}) "
                f"{len(items)}건"
            )

        except Exception as exc:

            print(
                f"[ERROR] "
                f"{name_en} "
                f"({fed}) : "
                f"{exc}"
            )

            continue

        # ====================================================
        # YEAR FILTER
        # ====================================================

        filtered_items = []

        for raw_item in items:

            if not isinstance(
                raw_item,
                dict
            ):
                continue

            item = _normalize_item(
                raw_item,
                member,
                fed,
            )

            # ------------------------------------------------
            # published_at
            # ------------------------------------------------

            published_at = (
                item.get(
                    "published_at"
                )
            )

            item_year = (
                _extract_year(
                    published_at
                )
            )

            # ------------------------------------------------
            # 날짜 없으면 URL에서 year 추출
            # ------------------------------------------------

            if item_year is None:

                item_year = (
                    _extract_year_from_url(
                        item.get(
                            "url"
                        )
                    )
                )

            # ------------------------------------------------
            # year 필터 없음
            # ------------------------------------------------

            if year is None:

                filtered_items.append(
                    item
                )

                continue

            target_year = int(
                year
            )

            # ------------------------------------------------
            # year를 판별할 수 있음
            # ------------------------------------------------

            if item_year is not None:

                if (
                    item_year
                    == target_year
                ):

                    filtered_items.append(
                        item
                    )

                continue

            # ------------------------------------------------
            # year 확인 불가
            #
            # Richmond처럼 날짜가 없는 잠재적 유효 데이터를
            # 함부로 삭제하지 않는다.
            # ------------------------------------------------

            filtered_items.append(
                item
            )

        # ====================================================
        # PHILADELPHIA DEBUG
        # ====================================================

        if fed == "Philadelphia Fed":

            print(
                f"[PHIL FILTER] "
                f"raw={len(items)} "
                f"kept={len(filtered_items)}"
            )

            for item in filtered_items[:5]:

                print(
                    "[PHIL SAMPLE]",
                    item.get(
                        "published_at"
                    ),
                    "|",
                    item.get(
                        "title"
                    ),
                    "|",
                    item.get(
                        "url"
                    ),
                )

        results.extend(
            filtered_items
        )

    # ========================================================
    # GLOBAL URL DEDUP
    # ========================================================

    by_url = {}

    no_url_items = []

    for item in results:

        if not isinstance(
            item,
            dict
        ):
            continue

        url = (
            item.get(
                "url"
            )
        )

        # ====================================================
        # URL 없음
        # ====================================================

        if not url:

            no_url_items.append(
                item
            )

            continue

        existing = (
            by_url.get(
                url
            )
        )

        if existing is None:

            by_url[
                url
            ] = item

            continue

        # ====================================================
        # 정보가 더 많은 결과 선택
        # ====================================================

        if (
            _quality_score(
                item
            )
            >
            _quality_score(
                existing
            )
        ):

            by_url[
                url
            ] = item

    results = (
        list(
            by_url.values()
        )
        + no_url_items
    )

    # ========================================================
    # SORT
    #
    # 날짜 있는 항목 최신순
    # 날짜 없는 항목은 뒤
    # ========================================================

    results.sort(
        key=lambda item: (
            item.get(
                "published_at"
            )
            or "0000-00-00"
        ),
        reverse=True,
    )

    return results