# crawlers/base.py

import re
import time
from datetime import datetime
from urllib.parse import urljoin

import requests

from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# HTTP CONFIG
# ============================================================

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/130.0 Safari/537.36"
    ),

    "Accept": (
        "text/html,"
        "application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,"
        "image/webp,"
        "*/*;q=0.8"
    ),

    "Accept-Language": (
        "en-US,en;q=0.9"
    ),

    "Connection": "keep-alive",
}


# ============================================================
# TIMEOUT
#
# requests timeout tuple:
#
# (connect timeout, read timeout)
#
# connect = 서버 연결까지 기다리는 시간
# read    = 연결된 뒤 응답 데이터를 기다리는 시간
# ============================================================

DEFAULT_TIMEOUT = (
    5,
    12,
)


# ============================================================
# SESSION
# ============================================================

def _build_session():

    session = requests.Session()

    # ========================================================
    # RETRY
    #
    # 최초 요청 실패 후 추가 1회 재시도
    # ========================================================

    retry = Retry(
        total=1,

        connect=1,
        read=1,
        status=1,

        backoff_factor=0.5,

        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],

        allowed_methods=[
            "GET",
        ],

        # status code 에러가 retry 대상이면
        # 바로 예외를 던지지 않고 retry
        raise_on_status=False,

        # Retry-After header가 있으면 존중
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(
        max_retries=retry,

        # 병렬 body fetch 대응
        pool_connections=20,
        pool_maxsize=20,
    )

    session.mount(
        "https://",
        adapter
    )

    session.mount(
        "http://",
        adapter
    )

    session.headers.update(
        DEFAULT_HEADERS
    )

    return session


SESSION = _build_session()


# ============================================================
# GET HTML
# ============================================================

def get_html(
    url,
    timeout=DEFAULT_TIMEOUT,
    sleep_seconds=0,
):
    """
    URL의 HTML 문자열 반환.

    기본 timeout:
        connect 5초
        read    12초

    retry:
        추가 1회

    sleep_seconds:
        기본 0.
        필요할 때만 요청 전 delay 사용.
    """

    if sleep_seconds:

        time.sleep(
            sleep_seconds
        )

    response = SESSION.get(
        url,
        timeout=timeout,
    )

    response.raise_for_status()

    # ========================================================
    # ENCODING
    #
    # Fed 사이트에서
    # â€™
    # 같은 mojibake 발생 방지.
    # ========================================================

    content_type = (
        response.headers.get(
            "Content-Type",
            ""
        )
        .lower()
    )

    if "charset=utf-8" in content_type:

        response.encoding = (
            "utf-8"
        )

    else:

        encoding = (
            response.apparent_encoding
            or response.encoding
            or "utf-8"
        )

        encoding_lower = (
            str(
                encoding
            )
            .lower()
        )

        # requests가 latin 계열로 잘못 판단하는 경우
        if encoding_lower in [
            "iso-8859-1",
            "latin-1",
            "windows-1252",
        ]:

            encoding = (
                "utf-8"
            )

        response.encoding = (
            encoding
        )

    return response.text


# ============================================================
# GET SOUP
# ============================================================

def get_soup(
    url,
    timeout=DEFAULT_TIMEOUT,
):
    """
    URL → BeautifulSoup
    """

    html = get_html(
        url,
        timeout=timeout,
    )

    return BeautifulSoup(
        html,
        "html.parser",
    )


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(
    text
):

    if text is None:
        return ""

    text = str(
        text
    )

    # ========================================================
    # COMMON MOJIBAKE
    # ========================================================

    replacements = {
        "â€™": "’",
        "â€œ": "“",
        "â€\x9d": "”",
        "â€“": "–",
        "â€”": "—",
        "Â ": " ",
        "\xa0": " ",
    }

    for bad, good in (
        replacements.items()
    ):

        text = text.replace(
            bad,
            good
        )

    # ========================================================
    # WHITESPACE
    # ========================================================

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# ABSOLUTE URL
# ============================================================

def absolute_url(
    base_url,
    href
):

    if not href:
        return None

    return urljoin(
        base_url,
        href
    )


# ============================================================
# DATE PARSER
# ============================================================

def parse_english_date(
    text
):

    if not text:
        return None

    text = clean_text(
        text
    )

    # Apr. 10, 2026
    # → Apr 10, 2026
    text = re.sub(
        (
            r"\b"
            r"(Jan|Feb|Mar|Apr|Jun|Jul|Aug|"
            r"Sep|Sept|Oct|Nov|Dec)"
            r"\."
        ),
        r"\1",
        text,
        flags=re.IGNORECASE,
    )

    formats = [
        "%B %d, %Y",
        "%b %d, %Y",
        "%m/%d/%Y",
        "%m.%d.%Y",
        "%Y-%m-%d",
    ]

    for fmt in formats:

        try:

            dt = datetime.strptime(
                text,
                fmt
            )

            return dt.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            continue

    return None


# ============================================================
# ARTICLE TEXT
# ============================================================

def extract_article_text(
    soup,
    selectors=None,
):
    """
    여러 Fed 사이트에서 기사/연설 본문 추출.

    selector 우선 탐색 후,
    찾지 못하면 soup 전체의 p 태그 사용.
    """

    selectors = (
        selectors
        or [
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
    )

    target = None

    # ========================================================
    # SELECTOR
    # ========================================================

    for selector in selectors:

        try:

            target = (
                soup.select_one(
                    selector
                )
            )

        except Exception:

            continue

        if target:
            break

    if not target:

        target = soup

    # ========================================================
    # PARAGRAPHS
    # ========================================================

    paragraphs = []

    for p in target.find_all(
        "p"
    ):

        text = clean_text(
            p.get_text(
                " ",
                strip=True
            )
        )

        if not text:
            continue

        # navigation / 짧은 라벨 제거
        if len(text) < 20:
            continue

        paragraphs.append(
            text
        )

    # ========================================================
    # DEDUP PARAGRAPHS
    # ========================================================

    unique = []

    seen = set()

    for paragraph in paragraphs:

        key = (
            paragraph.lower()
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            paragraph
        )

    return "\n".join(
        unique
    )