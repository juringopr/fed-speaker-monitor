# crawlers/fed_board.py

import re
from datetime import datetime

from .base import (
    get_soup,
    clean_text,
    absolute_url,
    parse_english_date,
    extract_article_text,
)


BASE_URL = "https://www.federalreserve.gov"


# ============================================================
# URL SPEAKER MAP
#
# 현재 우리가 추적하는 Board of Governors 인물만 등록.
# CSV에 없는 인물은 매칭하지 않고 UNMATCHED로 유지한다.
# ============================================================

URL_SPEAKER_MAP = {
    "powell": "Jerome Powell",
    "cook": "Lisa Cook",
    "jefferson": "Philip Jefferson",
    "barr": "Michael Barr",
    "bowman": "Michelle Bowman",
    "waller": "Christopher Waller",
    "warsh": "Kevin Warsh",
}


# ============================================================
# MAIN
# ============================================================

def crawl_fed_board(
    year=None,
    fetch_body=False,
):

    if year is None:
        year = datetime.now().year

    list_url = (
        f"{BASE_URL}/"
        f"newsevents/{year}-speeches.htm"
    )

    soup = get_soup(
        list_url
    )

    results = []
    seen_urls = set()

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = (
            link.get("href", "")
            or ""
        ).strip()

        if "/newsevents/speech/" not in href:
            continue

        if not href.lower().endswith(
            ".htm"
        ):
            continue

        url = absolute_url(
            BASE_URL,
            href
        )

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(
            url
        )

        link_title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        # ----------------------------------------------------
        # URL에서 날짜
        # ----------------------------------------------------

        url_date = (
            _extract_date_from_url(
                url
            )
        )

        # ----------------------------------------------------
        # URL에서 speaker
        # ----------------------------------------------------

        url_speaker = (
            _extract_speaker_from_url(
                url
            )
        )

        # ----------------------------------------------------
        # 상세 페이지
        # ----------------------------------------------------

        if fetch_body:

            try:

                article = (
                    _crawl_fed_board_article(
                        url
                    )
                )

            except Exception:

                article = {}

        else:

            article = {}

        # ----------------------------------------------------
        # 최종
        #
        # 상세 페이지 정보 우선,
        # 없으면 URL fallback
        # ----------------------------------------------------

        results.append({
            "published_at":
                article.get(
                    "published_at"
                )
                or url_date,

            "title":
                article.get(
                    "title"
                )
                or link_title,

            "speaker_raw":
                article.get(
                    "speaker_raw"
                )
                or url_speaker,

            "url":
                url,

            "source":
                "Federal Reserve Board",

            "source_type":
                "OFFICIAL",

            "text":
                article.get(
                    "text",
                    ""
                ),
        })

    # 날짜 최신순
    results.sort(
        key=lambda x: (
            x.get("published_at")
            or "0000-00-00"
        ),
        reverse=True
    )

    return results


# ============================================================
# URL → DATE
# ============================================================

def _extract_date_from_url(
    url
):
    """
    예:

    cook20260805a.htm
        → 2026-08-05

    jefferson20260716a.htm
        → 2026-07-16

    miran20260326a.htm
        → 2026-03-26
    """

    if not url:
        return None

    match = re.search(
        r"(20\d{2})"
        r"(\d{2})"
        r"(\d{2})"
        r"[a-z]?"
        r"\.htm",
        str(url),
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    year = int(
        match.group(1)
    )

    month = int(
        match.group(2)
    )

    day = int(
        match.group(3)
    )

    if not (
        1 <= month <= 12
    ):
        return None

    if not (
        1 <= day <= 31
    ):
        return None

    return (
        f"{year:04d}-"
        f"{month:02d}-"
        f"{day:02d}"
    )


# ============================================================
# URL → SPEAKER
# ============================================================

def _extract_speaker_from_url(
    url
):
    """
    현재 CSV에서 추적 중인 Board 인물만 speaker_raw에 넣는다.

    miran20260326a.htm 같은 경우
    URL_SPEAKER_MAP에 없으므로 None 반환.

    따라서 해당 기사는 삭제되지 않고
    member_matcher에서 UNMATCHED로 남는다.
    """

    if not url:
        return None

    filename = (
        str(url)
        .split("/")[-1]
        .lower()
    )

    match = re.match(
        r"([a-z]+)"
        r"20\d{6}",
        filename
    )

    if not match:
        return None

    slug = match.group(1)

    return URL_SPEAKER_MAP.get(
        slug
    )


# ============================================================
# DETAIL PAGE
# ============================================================

def _crawl_fed_board_article(
    url
):

    soup = get_soup(
        url
    )

    page_text = (
        soup.get_text(
            "\n",
            strip=True
        )
        or ""
    )

    # ========================================================
    # TITLE
    # ========================================================

    title = None

    h1 = soup.find(
        "h1"
    )

    if h1:

        title = clean_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

    # ========================================================
    # DATE
    # ========================================================

    published_at = (
        _extract_date_from_page(
            page_text
        )
    )

    if not published_at:

        published_at = (
            _extract_date_from_url(
                url
            )
        )

    # ========================================================
    # SPEAKER
    # ========================================================

    speaker_raw = (
        _extract_known_speaker_from_page(
            page_text
        )
    )

    if not speaker_raw:

        speaker_raw = (
            _extract_speaker_from_url(
                url
            )
        )

    # ========================================================
    # BODY
    # ========================================================

    text = extract_article_text(
        soup,
        selectors=[
            "#article",
            ".col-xs-12.col-sm-8.col-md-8",
            ".col-xs-12.col-sm-8",
            "article",
            "main",
        ]
    )

    return {
        "published_at":
            published_at,

        "title":
            title,

        "speaker_raw":
            speaker_raw,

        "text":
            text,
    }


# ============================================================
# PAGE DATE
# ============================================================

def _extract_date_from_page(
    text
):

    if not text:
        return None

    patterns = [
        (
            r"(January|February|March|April|May|June|"
            r"July|August|September|October|November|December)"
            r"\s+\d{1,2},\s+20\d{2}"
        ),
        (
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|"
            r"Oct|Nov|Dec)"
            r"\.?\s+\d{1,2},\s+20\d{2}"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        raw_date = (
            match.group(0)
            .replace(".", "")
        )

        parsed = (
            parse_english_date(
                raw_date
            )
        )

        if parsed:
            return parsed

    return None


# ============================================================
# PAGE SPEAKER
# ============================================================

def _extract_known_speaker_from_page(
    text
):

    if not text:
        return None

    lower_text = (
        text.lower()
    )

    for speaker in (
        URL_SPEAKER_MAP.values()
    ):

        if (
            speaker.lower()
            in lower_text
        ):
            return speaker

    return None