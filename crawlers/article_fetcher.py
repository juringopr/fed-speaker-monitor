# crawlers/article_fetcher.py

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

import io

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
#
# 공식 prepared remarks PDF가 확인된 speech만 등록한다.
#
# 인터뷰 / 현장방문 / webcast 등은
# 전문이 없을 수 있으므로 억지로 mapping하지 않는다.
# ============================================================

STL_PDF_MAP = {

    "economic-outlook-monetary-policy-aei":
        (
            "https://www.stlouisfed.org/"
            "-/media/project/frbstl/stlouisfed/"
            "musalem/2026/"
            "musalem-aei-remarks-01-apr-2026-final.pdf"
        ),

    "productivity-growth-and-monetary-policy-iceland":
        (
            "https://www.stlouisfed.org/"
            "-/media/project/frbstl/stlouisfed/"
            "musalem/2026/"
            "musalem-iceland-remarks-28-may-2026_final.pdf"
        ),
}


# ============================================================
# PDF TEXT EXTRACT
# ============================================================

def _extract_pdf_text(
    pdf_bytes,
):
    """
    PDF bytes -> text
    """

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
    St. Louis URL slug가 STL_PDF_MAP에 있으면
    공식 PDF를 다운로드해서 본문 추출.

    PDF가 등록되어 있지 않으면 빈 문자열 반환.
    """

    if not url:
        return ""

    slug = (
        str(url)
        .rstrip("/")
        .split("/")[-1]
        .lower()
    )

    pdf_url = (
        STL_PDF_MAP.get(
            slug
        )
    )

    if not pdf_url:
        return ""

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

    # HTML error page를 PDF로 오인하는 것 방지
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

    text = _extract_pdf_text(
        response.content
    )

    return clean_text(
        text
    )


# ============================================================
# JINA READER FALLBACK
# ============================================================

def _fetch_with_reader(
    url,
):
    """
    URL -> Jina Reader
    """

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
    """
    본문 수집 순서

    일반:
        1. DIRECT

    St. Louis:
        1. DIRECT
        2. OFFICIAL PDF
        3. JINA READER

    반환:
        text
        body_fetched
        body_fetch_error
        body_text_length
        body_fetch_method
    """

    item = dict(
        article
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

        text = extract_article_text(
            soup,
            selectors=selectors,
        )

        text = clean_text(
            text
        )

        # ----------------------------------------------------
        # paragraph fallback
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # direct success
        # ----------------------------------------------------

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
    # 2. ST. LOUIS OFFICIAL PDF
    # ========================================================

    pdf_error = (
        "PDF_NOT_AVAILABLE"
    )

    try:

        pdf_text = (
            _fetch_stl_pdf_fallback(
                url
            )
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

        reader_text = (
            _fetch_with_reader(
                url
            )
        )

        reader_text = (
            _clean_reader_text(
                reader_text
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

    # ========================================================
    # TARGETS
    # ========================================================

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

    # ========================================================
    # THREAD POOL
    # ========================================================

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

        # ====================================================
        # RESULTS
        # ====================================================

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
                ) = future.result()

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

            # ------------------------------------------------
            # 원래 위치 유지
            # ------------------------------------------------

            results[
                result_index
            ] = fetched

            completed += 1

            # ------------------------------------------------
            # status
            # ------------------------------------------------

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

            print(
                f"[BODY] "
                f"{completed}/{total_targets} "
                f"{speaker} "
                f"| {status} "
                f"| {title[:70]}"
            )

    # ========================================================
    # SUMMARY
    # ========================================================

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