# crawlers/article_fetcher.py

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from datetime import datetime

import io
import re

import requests
from pypdf import PdfReader

from crawlers.base import (
    get_soup,
    extract_article_text,
    clean_text,
)


# ============================================================
# CONFIG
# ============================================================

DEFAULT_MAX_WORKERS = 6

MIN_TEXT_LENGTH = 100

READER_TIMEOUT = (
    5,
    25,
)

PDF_TIMEOUT = (
    5,
    20,
)


# ============================================================
# SOURCE-SPECIFIC SELECTORS
# ============================================================

SOURCE_SELECTORS = {

    "Federal Reserve Board": [
        "#article",
        ".col-xs-12.col-sm-8.col-md-8",
        ".col-xs-12.col-sm-8",
        "article",
        "main",
    ],

    "Dallas Fed": [
        "article",
        "main",
        ".article-content",
        ".content",
        "#content",
    ],

    "Cleveland Fed": [
        "article",
        "main",
        ".article-content",
        ".content",
        "#content",
    ],

    "Minneapolis Fed": [
        "article",
        "main",
        ".article-content",
        ".entry-content",
        ".content",
        "#content",
    ],

    "Chicago Fed": [
        "article",
        "main",
        ".article-content",
        ".content",
        "#content",
    ],

    "Boston Fed": [
        "article",
        "main",
        ".article-content",
        ".content",
        "#content",
    ],

    "Kansas City Fed": [
        "article",
        "main",
        ".article-content",
        ".content",
        "#content",
    ],

    "Richmond Fed": [
        "article",
        "main",
        ".article-content",
        ".content",
        "#content",
    ],

    "St. Louis Fed": [
        "article",
        "main",
        ".article-content",
        ".content",
        "#content",
    ],

    "New York Fed": [
        "article",
        "main",
        ".article-content",
        ".content",
        "#content",
    ],

    "Philadelphia Fed": [
        "article",
        "main",
        ".article-content",
        ".content",
        "#content",
    ],

    "San Francisco Fed": [
        "article",
        "main",
        ".article-content",
        ".entry-content",
        ".content",
        "#content",
    ],
}


DEFAULT_SELECTORS = [
    "article",
    "main",
    ".article-content",
    ".entry-content",
    ".page-content",
    ".body-content",
    ".content",
    "#article",
    "#content",
]


# ============================================================
# ST. LOUIS OFFICIAL PDF MAP
# ============================================================

STL_PDF_MAP = {

    "economic-outlook-monetary-policy-aei": {

        "url":
            (
                "https://www.stlouisfed.org/"
                "-/media/project/frbstl/stlouisfed/"
                "musalem/2026/"
                "musalem-aei-remarks-01-apr-2026-final.pdf"
            ),

        "date":
            "2026-04-01",
    },

    "productivity-growth-and-monetary-policy-iceland": {

        "url":
            (
                "https://www.stlouisfed.org/"
                "-/media/project/frbstl/stlouisfed/"
                "musalem/2026/"
                "musalem-iceland-remarks-28-may-2026_final.pdf"
            ),

        "date":
            "2026-05-28",
    },
}


# ============================================================
# DATE HELPERS
# ============================================================

MONTH_MAP = {

    "january": 1,
    "jan": 1,

    "february": 2,
    "feb": 2,

    "march": 3,
    "mar": 3,

    "april": 4,
    "apr": 4,

    "may": 5,

    "june": 6,
    "jun": 6,

    "july": 7,
    "jul": 7,

    "august": 8,
    "aug": 8,

    "september": 9,
    "sept": 9,
    "sep": 9,

    "october": 10,
    "oct": 10,

    "november": 11,
    "nov": 11,

    "december": 12,
    "dec": 12,
}


def _normalize_date(
    value,
):
    """
    날짜 문자열 -> YYYY-MM-DD
    """

    if not value:
        return None

    value = (
        str(
            value
        )
        .strip()
    )

    # --------------------------------------------------------
    # YYYY-MM-DD
    # --------------------------------------------------------

    iso_match = re.search(
        r"\b"
        r"(20\d{2})"
        r"-"
        r"(\d{1,2})"
        r"-"
        r"(\d{1,2})"
        r"\b",
        value,
    )

    if iso_match:

        try:

            year = int(
                iso_match.group(1)
            )

            month = int(
                iso_match.group(2)
            )

            day = int(
                iso_match.group(3)
            )

            return datetime(
                year,
                month,
                day,
            ).strftime(
                "%Y-%m-%d"
            )

        except ValueError:
            pass

    # --------------------------------------------------------
    # May 28, 2026
    # --------------------------------------------------------

    month_match = re.search(
        r"\b"
        r"(January|February|March|April|May|June|July|"
        r"August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
        r"\.?"
        r"\s+"
        r"(\d{1,2})"
        r",?"
        r"\s+"
        r"(20\d{2})"
        r"\b",
        value,
        flags=re.I,
    )

    if month_match:

        month_name = (
            month_match
            .group(1)
            .lower()
        )

        month = (
            MONTH_MAP.get(
                month_name
            )
        )

        day = int(
            month_match.group(2)
        )

        year = int(
            month_match.group(3)
        )

        if month:

            try:

                return datetime(
                    year,
                    month,
                    day,
                ).strftime(
                    "%Y-%m-%d"
                )

            except ValueError:
                pass

    return None


# ============================================================
# APPLY DATE
# ============================================================

def _apply_article_date(
    item,
    value,
):
    """
    article 내부의 date / published_at을 함께 동기화.

    하나라도 기존 날짜가 있으면 이를 기준으로
    다른 필드도 채운다.

    기존 정상 날짜를 새 값으로 덮어쓰지는 않는다.
    """

    normalized = (
        _normalize_date(
            value
        )
    )

    if not normalized:
        return

    if not item.get(
        "published_at"
    ):

        item[
            "published_at"
        ] = (
            normalized
        )

    if not item.get(
        "date"
    ):

        item[
            "date"
        ] = (
            normalized
        )


# ============================================================
# READER DATE
# ============================================================

def _extract_reader_date(
    reader_text,
):
    """
    Jina Reader metadata / 본문 앞부분에서 날짜 탐색.
    """

    if not reader_text:
        return None

    raw = str(
        reader_text
    )

    # --------------------------------------------------------
    # Published Time:
    # --------------------------------------------------------

    match = re.search(
        r"(?im)^"
        r"Published\s+Time\s*:"
        r"\s*(.+?)"
        r"\s*$",
        raw,
    )

    if match:

        normalized = (
            _normalize_date(
                match.group(1)
            )
        )

        if normalized:
            return normalized

    # --------------------------------------------------------
    # Published:
    # --------------------------------------------------------

    match = re.search(
        r"(?im)^"
        r"Published\s*:"
        r"\s*(.+?)"
        r"\s*$",
        raw,
    )

    if match:

        normalized = (
            _normalize_date(
                match.group(1)
            )
        )

        if normalized:
            return normalized

    # --------------------------------------------------------
    # Date:
    # --------------------------------------------------------

    match = re.search(
        r"(?im)^"
        r"Date\s*:"
        r"\s*(.+?)"
        r"\s*$",
        raw,
    )

    if match:

        normalized = (
            _normalize_date(
                match.group(1)
            )
        )

        if normalized:
            return normalized

    # --------------------------------------------------------
    # 본문 앞부분
    # --------------------------------------------------------

    head = (
        raw[
            :3000
        ]
    )

    return _normalize_date(
        head
    )


# ============================================================
# DIRECT HTML DATE
# ============================================================

def _extract_date_from_soup(
    soup,
):

    if soup is None:
        return None

    meta_candidates = [

        (
            "meta",
            {
                "property":
                    "article:published_time",
            },
        ),

        (
            "meta",
            {
                "name":
                    "date",
            },
        ),

        (
            "meta",
            {
                "name":
                    "publishdate",
            },
        ),

        (
            "meta",
            {
                "name":
                    "pubdate",
            },
        ),

        (
            "meta",
            {
                "itemprop":
                    "datePublished",
            },
        ),
    ]

    for (
        tag_name,
        attrs,
    ) in meta_candidates:

        tag = soup.find(
            tag_name,
            attrs=attrs,
        )

        if not tag:
            continue

        value = (
            tag.get(
                "content"
            )
            or
            tag.get_text(
                " ",
                strip=True,
            )
        )

        normalized = (
            _normalize_date(
                value
            )
        )

        if normalized:
            return normalized

    for time_tag in soup.find_all(
        "time"
    ):

        value = (
            time_tag.get(
                "datetime"
            )
            or
            time_tag.get_text(
                " ",
                strip=True,
            )
        )

        normalized = (
            _normalize_date(
                value
            )
        )

        if normalized:
            return normalized

    return None


# ============================================================
# PDF TEXT EXTRACT
# ============================================================

def _extract_pdf_text(
    pdf_bytes,
):

    reader = PdfReader(
        io.BytesIO(
            pdf_bytes
        )
    )

    pages = []

    for page in reader.pages:

        text = (
            page.extract_text()
            or ""
        )

        text = clean_text(
            text
        )

        if not text:
            continue

        pages.append(
            text
        )

    return "\n".join(
        pages
    )


# ============================================================
# ST. LOUIS PDF FALLBACK
# ============================================================

def _fetch_stl_pdf_fallback(
    url,
):
    """
    return:
        text, published_at
    """

    if not url:

        return (
            "",
            None,
        )

    slug = (
        str(
            url
        )
        .rstrip("/")
        .split("/")[-1]
        .lower()
    )

    pdf_info = (
        STL_PDF_MAP.get(
            slug
        )
    )

    if not pdf_info:

        return (
            "",
            None,
        )

    pdf_url = (
        pdf_info.get(
            "url"
        )
    )

    pdf_date = (
        pdf_info.get(
            "date"
        )
    )

    response = requests.get(
        pdf_url,
        timeout=PDF_TIMEOUT,
        headers={

            "User-Agent":
                (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
                ),

            "Accept":
                (
                    "application/pdf,"
                    "*/*;q=0.8"
                ),
        },
    )

    response.raise_for_status()

    content_type = (
        response.headers.get(
            "Content-Type",
            ""
        )
        .lower()
    )

    if (
        "pdf"
        not in content_type
        and
        not response.content.startswith(
            b"%PDF"
        )
    ):

        raise ValueError(
            "STL_PDF_INVALID_CONTENT_TYPE:"
            f"{content_type}"
        )

    text = (
        _extract_pdf_text(
            response.content
        )
    )

    return (
        clean_text(
            text
        ),
        pdf_date,
    )


# ============================================================
# JINA READER FALLBACK
# ============================================================

def _fetch_with_reader(
    url,
):

    reader_url = (
        "https://r.jina.ai/"
        + url
    )

    response = requests.get(
        reader_url,
        timeout=READER_TIMEOUT,
        headers={

            "User-Agent":
                (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
                ),

            "Accept":
                "text/plain",
        },
    )

    response.raise_for_status()

    return response.text


# ============================================================
# CLEAN READER TEXT
# ============================================================

def _clean_reader_text(
    text,
):

    if not text:
        return ""

    lines = []

    for raw_line in str(
        text
    ).splitlines():

        line = (
            raw_line
            .strip()
        )

        if not line:
            continue

        lower = (
            line.lower()
        )

        if lower.startswith(
            "title:"
        ):
            continue

        if lower.startswith(
            "url source:"
        ):
            continue

        if lower.startswith(
            "published time:"
        ):
            continue

        if lower.startswith(
            "published:"
        ):
            continue

        if lower.startswith(
            "markdown content:"
        ):
            continue

        lines.append(
            line
        )

    return clean_text(
        "\n".join(
            lines
        )
    )


# ============================================================
# SINGLE ARTICLE
# ============================================================

def fetch_article_body(
    article,
    min_text_length=MIN_TEXT_LENGTH,
):

    item = dict(
        article
    )

    # ========================================================
    # EXISTING DATE SYNC
    # ========================================================

    existing_date = (
        item.get(
            "date"
        )
        or
        item.get(
            "published_at"
        )
    )

    if existing_date:

        _apply_article_date(
            item,
            existing_date,
        )

    url = (
        item.get(
            "url"
        )
    )

    source = (
        item.get(
            "source"
        )
    )

    # ========================================================
    # URL MISSING
    # ========================================================

    if not url:

        item.update({

            "body_fetched":
                False,

            "body_fetch_error":
                "URL_MISSING",

            "body_text_length":
                0,

            "body_fetch_method":
                None,
        })

        return item

    # ========================================================
    # EXISTING TEXT
    # ========================================================

    existing_text = clean_text(
        item.get(
            "text"
        )
        or ""
    )

    if (
        len(
            existing_text
        )
        >= min_text_length
    ):

        item.update({

            "text":
                existing_text,

            "body_fetched":
                True,

            "body_fetch_error":
                None,

            "body_text_length":
                len(
                    existing_text
                ),

            "body_fetch_method":
                "EXISTING",
        })

        return item

    selectors = (
        SOURCE_SELECTORS.get(
            source
        )
        or
        DEFAULT_SELECTORS
    )

    direct_error = None

    # ========================================================
    # 1. DIRECT FETCH
    # ========================================================

    try:

        soup = get_soup(
            url
        )

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        direct_date = (
            _extract_date_from_soup(
                soup
            )
        )

        if direct_date:

            _apply_article_date(
                item,
                direct_date,
            )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        text = extract_article_text(
            soup,
            selectors=selectors,
        )

        text = clean_text(
            text
        )

        if (
            len(
                text
            )
            < min_text_length
        ):

            fallback_text = (
                _fallback_paragraph_text(
                    soup
                )
            )

            if (
                len(
                    fallback_text
                )
                >
                len(
                    text
                )
            ):

                text = (
                    fallback_text
                )

        if (
            len(
                text
            )
            >= min_text_length
        ):

            item.update({

                "text":
                    text,

                "body_fetched":
                    True,

                "body_fetch_error":
                    None,

                "body_text_length":
                    len(
                        text
                    ),

                "body_fetch_method":
                    "DIRECT",
            })

            return item

        direct_error = (
            "TEXT_TOO_SHORT:"
            f"{len(text)}"
        )

    except Exception as exc:

        direct_error = (
            str(
                exc
            )
        )

    # ========================================================
    # OTHER FED SOURCES
    # ========================================================

    if (
        source
        != "St. Louis Fed"
    ):

        item.update({

            "text":
                existing_text,

            "body_fetched":
                False,

            "body_fetch_error":
                direct_error,

            "body_text_length":
                len(
                    existing_text
                ),

            "body_fetch_method":
                "FAILED",
        })

        return item

    # ========================================================
    # 2. ST. LOUIS PDF
    # ========================================================

    pdf_error = (
        "PDF_NOT_AVAILABLE"
    )

    try:

        (
            pdf_text,
            pdf_date,
        ) = (
            _fetch_stl_pdf_fallback(
                url
            )
        )

        if pdf_date:

            _apply_article_date(
                item,
                pdf_date,
            )

        if (
            len(
                pdf_text
            )
            >= min_text_length
        ):

            item.update({

                "text":
                    pdf_text,

                "body_fetched":
                    True,

                "body_fetch_error":
                    None,

                "body_text_length":
                    len(
                        pdf_text
                    ),

                "body_fetch_method":
                    "STL_PDF",
            })

            print(
                "[STL PDF OK]",
                len(
                    pdf_text
                ),
                "chars",
                "|",
                item.get(
                    "date"
                ),
                "|",
                item.get(
                    "title"
                ),
            )

            return item

        if pdf_text:

            pdf_error = (
                "PDF_TEXT_TOO_SHORT:"
                f"{len(pdf_text)}"
            )

    except Exception as exc:

        pdf_error = (
            str(
                exc
            )
        )

    # ========================================================
    # 3. JINA READER
    # ========================================================

    reader_error = None

    try:

        raw_reader_text = (
            _fetch_with_reader(
                url
            )
        )

        # ----------------------------------------------------
        # DATE FIRST
        # ----------------------------------------------------

        reader_date = (
            _extract_reader_date(
                raw_reader_text
            )
        )

        if reader_date:

            _apply_article_date(
                item,
                reader_date,
            )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        reader_text = (
            _clean_reader_text(
                raw_reader_text
            )
        )

        if (
            len(
                reader_text
            )
            >= min_text_length
        ):

            item.update({

                "text":
                    reader_text,

                "body_fetched":
                    True,

                "body_fetch_error":
                    None,

                "body_text_length":
                    len(
                        reader_text
                    ),

                "body_fetch_method":
                    "JINA_READER",
            })

            print(
                "[STL READER OK]",
                len(
                    reader_text
                ),
                "chars",
                "| date=",
                item.get(
                    "date"
                ),
                "| published_at=",
                item.get(
                    "published_at"
                ),
                "|",
                item.get(
                    "title"
                ),
            )

            return item

        reader_error = (
            "READER_TEXT_TOO_SHORT:"
            f"{len(reader_text)}"
        )

    except Exception as exc:

        reader_error = (
            str(
                exc
            )
        )

    # ========================================================
    # ST. LOUIS ALL FAILED
    # ========================================================

    item.update({

        "text":
            existing_text,

        "body_fetched":
            False,

        "body_fetch_error":
            (
                "DIRECT="
                f"{direct_error}"
                " | "
                "PDF="
                f"{pdf_error}"
                " | "
                "READER="
                f"{reader_error}"
            ),

        "body_text_length":
            len(
                existing_text
            ),

        "body_fetch_method":
            "FAILED",
    })

    return item


# ============================================================
# WORKER
# ============================================================

def _fetch_worker(
    index,
    article,
):

    result = (
        fetch_article_body(
            article
        )
    )

    return (
        index,
        result,
    )


# ============================================================
# MULTIPLE ARTICLES - 6 THREAD
# ============================================================

def fetch_article_bodies(
    articles,
    relevance_levels=None,
    max_articles=None,
    max_workers=DEFAULT_MAX_WORKERS,
):

    if (
        relevance_levels
        is None
    ):

        relevance_levels = [
            "HIGH",
            "MEDIUM",
            "LOW",
        ]

    results = [
        dict(
            article
        )
        for article in articles
    ]

    targets = []

    for index, article in enumerate(
        results
    ):

        relevance = (
            article.get(
                "fomc_relevance"
            )
        )

        if (
            relevance
            not in relevance_levels
        ):
            continue

        targets.append(
            (
                index,
                article,
            )
        )

    if (
        max_articles
        is not None
    ):

        targets = (
            targets[
                :max_articles
            ]
        )

    total_targets = (
        len(
            targets
        )
    )

    print()

    print(
        "BODY FETCH TARGETS:",
        total_targets
    )

    print(
        "MAX WORKERS:",
        max_workers
    )

    if (
        total_targets
        == 0
    ):

        print(
            "BODY FETCH COMPLETE: 0건"
        )

        return results

    completed = 0
    success = 0
    failed = 0

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:

        future_map = {}

        for index, article in targets:

            future = (
                executor.submit(
                    _fetch_worker,
                    index,
                    article,
                )
            )

            future_map[
                future
            ] = (
                index,
                article,
            )

        for future in as_completed(
            future_map
        ):

            (
                original_index,
                original_article,
            ) = future_map[
                future
            ]

            try:

                (
                    result_index,
                    fetched,
                ) = (
                    future.result()
                )

            except Exception as exc:

                result_index = (
                    original_index
                )

                fetched = dict(
                    original_article
                )

                fetched.update({

                    "body_fetched":
                        False,

                    "body_fetch_error":
                        str(
                            exc
                        ),

                    "body_text_length":
                        len(
                            fetched.get(
                                "text"
                            )
                            or ""
                        ),

                    "body_fetch_method":
                        "FAILED",
                })

            results[
                result_index
            ] = (
                fetched
            )

            completed += 1

            if (
                fetched.get(
                    "body_fetched"
                )
            ):

                success += 1

                status = (
                    "OK "
                    f"{fetched.get('body_text_length', 0)} "
                    "chars "
                    f"[{fetched.get('body_fetch_method')}]"
                )

            else:

                failed += 1

                status = (
                    "FAIL "
                    f"{fetched.get('body_fetch_error')}"
                )

            speaker = (
                fetched.get(
                    "member_name_en"
                )
                or
                fetched.get(
                    "speaker_raw"
                )
                or
                "UNMATCHED"
            )

            title = (
                fetched.get(
                    "title"
                )
                or ""
            )

            article_date = (
                fetched.get(
                    "date"
                )
                or
                fetched.get(
                    "published_at"
                )
                or
                "-"
            )

            print(
                f"[BODY] "
                f"{completed}/{total_targets} "
                f"{speaker} "
                f"| {article_date} "
                f"| {status} "
                f"| {title[:70]}"
            )

    print()

    print(
        "=" * 70
    )

    print(
        "BODY FETCH COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        "TARGETS :",
        total_targets
    )

    print(
        "SUCCESS :",
        success
    )

    print(
        "FAILED  :",
        failed
    )

    print(
        "WORKERS :",
        max_workers
    )

    return results


# ============================================================
# PARAGRAPH FALLBACK
# ============================================================

def _fallback_paragraph_text(
    soup
):

    paragraphs = []

    seen = set()

    for p in soup.find_all(
        "p"
    ):

        text = clean_text(
            p.get_text(
                " ",
                strip=True,
            )
        )

        if (
            len(
                text
            )
            < 20
        ):
            continue

        key = (
            text.lower()
        )

        if (
            key
            in seen
        ):
            continue

        seen.add(
            key
        )

        paragraphs.append(
            text
        )

    return "\n".join(
        paragraphs
    )