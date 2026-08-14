# crawlers/infomax.py

from datetime import datetime
from urllib.parse import quote
import email.utils
import re
import time
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from googlenewsdecoder import new_decoderv1


# ============================================================
# CONFIG
# ============================================================

INFOMAX_DOMAIN = "news.einfomax.co.kr"

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search"
)

TIMEOUT = 15
REQUEST_SLEEP = 0.25


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    ),
    "Accept-Language":
        "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ============================================================
# ARTICLE TYPE FILTER
# ============================================================

# 이런 기사들은 위원 이름이 있어도
# 해당 위원의 직접 정책발언으로 쓰지 않는다.
EXCLUDED_TITLE_TERMS = [
    "뉴욕 마켓 브리핑",
    "뉴욕마켓워치",
    "뉴욕채권",
    "뉴욕환시",
    "뉴욕 금가격",
    "채권-주간",
    "증시-주간전망",
    "주간전망",
    "오늘 글로벌 경제지표",
    "딜링룸 24시",
    "전문] 연준",
    "[전문]",
    "전문가 시각",
    "월가의",
    "월가 ",
    "해외ib",
    "bofa ",
    "ing ",
    "맥쿼리 ",
    "골드만",
    "jp모건",
    "씨티 ",
    "크루그먼",
    "뷰포인트",
    "icyMI",
    "icymi",
]


# 위원에게 실제 발언을 귀속시킬 때 사용하는 표현
SPEECH_VERBS_KO = [
    "말했다",
    "밝혔다",
    "강조했다",
    "지적했다",
    "평가했다",
    "설명했다",
    "전망했다",
    "언급했다",
    "주장했다",
    "경고했다",
    "시사했다",
    "덧붙였다",
    "선호한다",
    "선호한다고",
    "생각한다",
    "생각한다고",
    "본다",
    "본다고",
    "판단한다",
    "판단한다고",
    "필요하다",
    "필요하다고",
    "적절하다",
    "적절하다고",
    "준비돼",
    "준비되어",
    "지지했다",
    "지지한다",
    "반대했다",
    "반대한다",
]


DIRECT_QUOTE_MARKERS = [
    '"',
    "'",
    "“",
    "”",
    "‘",
    "’",
]


POLICY_TERMS = [
    "금리",
    "기준금리",
    "금리인하",
    "금리 인하",
    "금리인상",
    "금리 인상",
    "동결",
    "인플레이션",
    "인플레",
    "물가",
    "연준",
    "fomc",
    "통화정책",
    "긴축",
    "완화",
    "제약적",
    "중립금리",
    "노동시장",
    "고용",
    "실업률",
    "interest rate",
    "rate cut",
    "rate hike",
    "inflation",
    "monetary policy",
]


# ============================================================
# HELPERS
# ============================================================

def _clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def _normalize_date(value):

    if not value:
        return None

    text = str(value).strip()

    # RSS RFC date
    try:

        parsed = (
            email.utils
            .parsedate_to_datetime(
                text
            )
        )

        if parsed:

            return parsed.strftime(
                "%Y-%m-%d"
            )

    except Exception:
        pass

    patterns = [
        r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})",
        r"(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
        )

        if not match:
            continue

        try:

            return datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            ).strftime("%Y-%m-%d")

        except Exception:
            continue

    return None


# ============================================================
# ACTUAL SPEECH DATE
# ============================================================

def extract_actual_speech_date(
    text,
    published_at,
):
    """
    인포맥스 기사:
        5일 발행
        "4일(현지시간) ... 연설에서"

    -> actual_speech_date = 4일

    발언일과 기사일을 분리하여
    Official ↔ Infomax event matching에 사용.
    """

    if not text or not published_at:
        return None

    try:

        pub = datetime.strptime(
            str(published_at)[:10],
            "%Y-%m-%d",
        )

    except Exception:
        return None

    # 너무 넓게 찾지 않고 기사 초반부 위주
    head = text[:5000]

    patterns = [
        r"(\d{1,2})일\s*\(현지\s*시간\)",
        r"(\d{1,2})일\s*\(현지시간\)",
        r"(\d{1,2})일\s+현지시간",
    ]

    candidate_day = None

    for pattern in patterns:

        match = re.search(
            pattern,
            head,
        )

        if match:

            candidate_day = int(
                match.group(1)
            )

            break

    if candidate_day is None:
        return None

    # 보통 기사일과 같은 달.
    # 기사일이 월초인데 발언일 숫자가 더 크다면
    # 전월일 가능성이 높음.
    year = pub.year
    month = pub.month

    if (
        pub.day <= 5
        and
        candidate_day >= 25
    ):

        month -= 1

        if month == 0:
            month = 12
            year -= 1

    try:

        actual = datetime(
            year,
            month,
            candidate_day,
        )

    except ValueError:
        return None

    # 기사일보다 너무 멀면 잘못 잡은 날짜로 간주
    gap = (
        pub.date()
        -
        actual.date()
    ).days

    if gap < 0 or gap > 7:
        return None

    return actual.strftime(
        "%Y-%m-%d"
    )


# ============================================================
# GOOGLE NEWS
# ============================================================

def build_google_news_url(
    query,
):

    return (
        f"{GOOGLE_NEWS_RSS}"
        f"?q={quote(query)}"
        f"&hl=ko"
        f"&gl=KR"
        f"&ceid=KR:ko"
    )


def search_google_news(
    query,
    max_results=50,
):

    url = build_google_news_url(
        query
    )

    print(
        f"[GOOGLE NEWS] {query}"
    )

    response = SESSION.get(
        url,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    root = ET.fromstring(
        response.content
    )

    results = []

    for item in root.findall(
        ".//item"
    ):

        source_node = item.find(
            "source"
        )

        source = (
            source_node.text
            if source_node is not None
            else ""
        )

        results.append({
            "title":
                _clean_text(
                    item.findtext("title")
                    or ""
                ),

            "google_news_url":
                item.findtext("link")
                or "",

            "published_at":
                _normalize_date(
                    item.findtext(
                        "pubDate"
                    )
                ),

            "source":
                _clean_text(
                    source
                ),
        })

        if len(results) >= max_results:
            break

    return results


# ============================================================
# GOOGLE URL DECODER
# ============================================================

def resolve_google_news_url(
    url,
):

    if not url:
        return None

    # 1. decoder
    try:

        result = new_decoderv1(
            url,
            interval=0.5,
        )

        decoded_url = None

        if isinstance(
            result,
            dict,
        ):

            decoded_url = (
                result.get(
                    "decoded_url"
                )
                or
                result.get(
                    "url"
                )
            )

        elif result:

            decoded_url = str(
                result
            )

        if (
            decoded_url
            and
            INFOMAX_DOMAIN
            in decoded_url
        ):

            return decoded_url.strip()

    except Exception as exc:

        print(
            "[GOOGLE DECODE FAIL]",
            exc,
        )

    # 2. redirect fallback
    try:

        response = SESSION.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
        )

        if (
            response.url
            and
            INFOMAX_DOMAIN
            in response.url
        ):

            return response.url

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        canonical = soup.select_one(
            'link[rel="canonical"]'
        )

        if canonical:

            href = canonical.get(
                "href"
            )

            if (
                href
                and
                INFOMAX_DOMAIN
                in href
            ):

                return href

    except Exception as exc:

        print(
            "[GOOGLE REDIRECT FAIL]",
            exc,
        )

    return None


# ============================================================
# FETCH ARTICLE
# ============================================================

def fetch_infomax_article(
    url,
):

    response = SESSION.get(
        url,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    title_node = (
        soup.select_one(
            "h3.heading"
        )
        or
        soup.select_one(
            ".article-head-title"
        )
        or
        soup.select_one(
            "h1"
        )
        or
        soup.select_one(
            "title"
        )
    )

    title = (
        _clean_text(
            title_node.get_text(
                " ",
                strip=True,
            )
        )
        if title_node
        else ""
    )

    body_node = (
        soup.select_one(
            "#article-view-content-div"
        )
        or
        soup.select_one(
            ".article-view-content"
        )
        or
        soup.select_one(
            ".article-body"
        )
        or
        soup.select_one(
            "#articleBody"
        )
    )

    text = ""

    if body_node:

        for garbage in body_node.select(
            "script, style, iframe"
        ):

            garbage.decompose()

        text = body_node.get_text(
            "\n",
            strip=True,
        )

    published_at = None

    meta_candidates = [
        soup.select_one(
            'meta[property="article:published_time"]'
        ),
        soup.select_one(
            'meta[name="article:published_time"]'
        ),
        soup.select_one(
            'meta[name="pubdate"]'
        ),
    ]

    for node in meta_candidates:

        if not node:
            continue

        published_at = (
            _normalize_date(
                node.get(
                    "content"
                )
            )
        )

        if published_at:
            break

    if not published_at:

        for node in soup.select(
            "time, "
            ".article-info, "
            ".article-head-info, "
            ".info-text, "
            "span, li"
        ):

            published_at = (
                _normalize_date(
                    node.get_text(
                        " ",
                        strip=True,
                    )
                )
            )

            if published_at:
                break

    actual_speech_date = (
        extract_actual_speech_date(
            text,
            published_at,
        )
    )

    return {
        "source":
            "Yonhap Infomax",

        "source_type":
            "INFOMAX",

        "title":
            title,

        "url":
            url,

        "published_at":
            published_at,

        "actual_speech_date":
            actual_speech_date,

        "text":
            text,

        "body_fetched":
            bool(text),
    }


# ============================================================
# MEMBER TERMS
# ============================================================

def build_member_terms(
    member_name_en,
    member_name_ko=None,
    aliases=None,
):

    terms = []

    if member_name_en:

        terms.append(
            member_name_en
        )

        parts = (
            member_name_en
            .split()
        )

        if parts:

            surname = (
                parts[-1]
                .strip()
            )

            if len(surname) >= 4:

                terms.append(
                    surname
                )

    if member_name_ko:

        terms.append(
            member_name_ko
        )

    for alias in (
        aliases
        or []
    ):

        alias = _clean_text(
            alias
        )

        if alias:
            terms.append(alias)

    return list(
        dict.fromkeys(
            terms
        )
    )


# ============================================================
# BASIC MEMBER CHECK
# ============================================================

def article_mentions_member(
    article,
    terms,
):

    combined = (
        (
            article.get("title")
            or ""
        )
        +
        "\n"
        +
        (
            article.get("text")
            or ""
        )
    ).lower()

    return any(
        term.lower()
        in combined
        for term
        in terms
        if term
    )


# ============================================================
# DIRECT SPEECH CHECK
# ============================================================

def article_has_direct_member_signal(
    article,
    member_terms,
):
    """
    핵심 필터.

    단순히 기사에 이름이 등장한 것이 아니라,
    해당 위원이 실제 말하거나 정책 입장을
    밝힌 기사인지 확인한다.
    """

    title = (
        article.get("title")
        or ""
    )

    text = (
        article.get("text")
        or ""
    )

    title_lower = title.lower()
    text_lower = text.lower()

    # --------------------------------------------------------
    # 시장기사/전망기사 제외
    # --------------------------------------------------------

    for term in EXCLUDED_TITLE_TERMS:

        if term.lower() in title_lower:
            return False

    # --------------------------------------------------------
    # 제목에 위원 이름/직책 + 인용문이 있는 경우
    # --------------------------------------------------------

    title_member = any(
        term.lower()
        in title_lower
        for term
        in member_terms
        if term
    )

    title_quote = any(
        marker in title
        for marker
        in DIRECT_QUOTE_MARKERS
    )

    if title_member and title_quote:
        return True

    # --------------------------------------------------------
    # 본문 내 실제 발언 문맥
    # --------------------------------------------------------

    # 이름 주변 ±250자만 확인
    for term in member_terms:

        if not term:
            continue

        term_lower = term.lower()

        start = 0

        while True:

            idx = text_lower.find(
                term_lower,
                start,
            )

            if idx < 0:
                break

            left = max(
                0,
                idx - 250,
            )

            right = min(
                len(text),
                idx + len(term) + 450,
            )

            window = text[
                left:right
            ]

            has_speech_verb = any(
                verb in window
                for verb
                in SPEECH_VERBS_KO
            )

            has_policy = any(
                policy.lower()
                in window.lower()
                for policy
                in POLICY_TERMS
            )

            if (
                has_speech_verb
                and
                has_policy
            ):

                return True

            start = (
                idx
                +
                len(term)
            )

    return False


# ============================================================
# POLICY FILTER
# ============================================================

def article_is_policy_relevant(
    article,
):

    combined = (
        (
            article.get("title")
            or ""
        )
        +
        "\n"
        +
        (
            article.get("text")
            or ""
        )
    ).lower()

    return any(
        term.lower()
        in combined
        for term
        in POLICY_TERMS
    )


# ============================================================
# SEARCH QUERIES
# ============================================================

def build_google_queries(
    member_name_en,
    member_name_ko=None,
    aliases=None,
):

    queries = []

    base_terms = []

    if member_name_ko:
        base_terms.append(
            member_name_ko
        )

    if member_name_en:
        base_terms.append(
            member_name_en
        )

    for alias in (
        aliases
        or []
    ):

        alias = _clean_text(
            alias
        )

        if alias:
            base_terms.append(
                alias
            )

    base_terms = list(
        dict.fromkeys(
            base_terms
        )
    )

    # 이름 단독 검색
    for term in base_terms:

        queries.append(
            f'"{term}" 연합인포맥스'
        )

    # recall 보강:
    # 한글 이름에는 정책 키워드 조합도 추가
    if member_name_ko:

        for policy_word in [
            "금리",
            "인플레",
            "FOMC",
        ]:

            queries.append(
                f'"{member_name_ko}" '
                f'{policy_word} '
                f'연합인포맥스'
            )

    return list(
        dict.fromkeys(
            queries
        )
    )


# ============================================================
# MAIN
# ============================================================

def crawl_infomax_member_news(
    member_name_en,
    member_name_ko=None,
    aliases=None,
    max_results=20,
    year=None,
):

    queries = (
        build_google_queries(
            member_name_en,
            member_name_ko,
            aliases,
        )
    )

    member_terms = (
        build_member_terms(
            member_name_en,
            member_name_ko,
            aliases,
        )
    )

    candidates = []
    seen_google_urls = set()

    # ========================================================
    # SEARCH
    # ========================================================

    for query in queries:

        try:

            results = search_google_news(
                query,
                max_results=50,
            )

        except Exception as exc:

            print(
                "[GOOGLE SEARCH FAIL]",
                query,
                "|",
                exc,
            )

            continue

        print(
            f"[GOOGLE RESULT] "
            f"{query} = {len(results)}"
        )

        for item in results:

            source = (
                item.get("source")
                or ""
            )

            if (
                "인포맥스"
                not in source
                and
                "Infomax"
                not in source
            ):
                continue

            google_url = (
                item.get(
                    "google_news_url"
                )
            )

            if (
                not google_url
                or
                google_url
                in seen_google_urls
            ):
                continue

            seen_google_urls.add(
                google_url
            )

            candidates.append(
                item
            )

    print()

    print(
        f"[INFOMAX GOOGLE CANDIDATES] "
        f"{member_name_en}: "
        f"{len(candidates)}"
    )

    # ========================================================
    # FETCH + FILTER
    # ========================================================

    final = []
    seen_article_urls = set()

    for candidate in candidates:

        infomax_url = (
            resolve_google_news_url(
                candidate.get(
                    "google_news_url"
                )
            )
        )

        if not infomax_url:

            print(
                "[INFOMAX RESOLVE FAIL]",
                candidate.get("title"),
            )

            continue

        if infomax_url in seen_article_urls:
            continue

        seen_article_urls.add(
            infomax_url
        )

        try:

            article = (
                fetch_infomax_article(
                    infomax_url
                )
            )

        except Exception as exc:

            print(
                "[INFOMAX FETCH FAIL]",
                infomax_url,
                "|",
                exc,
            )

            continue

        if not article.get(
            "title"
        ):

            article["title"] = (
                (
                    candidate.get("title")
                    or ""
                )
                .replace(
                    " - 연합인포맥스",
                    "",
                )
                .strip()
            )

        if not article.get(
            "published_at"
        ):

            article[
                "published_at"
            ] = candidate.get(
                "published_at"
            )

        # 실제 발언일 재추출
        if not article.get(
            "actual_speech_date"
        ):

            article[
                "actual_speech_date"
            ] = (
                extract_actual_speech_date(
                    article.get("text"),
                    article.get(
                        "published_at"
                    ),
                )
            )

        # ====================================================
        # YEAR
        # ====================================================

        if year:

            date_for_year = (
                article.get(
                    "actual_speech_date"
                )
                or
                article.get(
                    "published_at"
                )
            )

            if (
                date_for_year
                and
                not str(
                    date_for_year
                ).startswith(
                    str(year)
                )
            ):

                continue

        # ====================================================
        # MEMBER
        # ====================================================

        if not article_mentions_member(
            article,
            member_terms,
        ):

            print(
                "[INFOMAX SKIP MEMBER]",
                article.get("title"),
            )

            continue

        # ====================================================
        # POLICY
        # ====================================================

        if not article_is_policy_relevant(
            article
        ):

            print(
                "[INFOMAX SKIP POLICY]",
                article.get("title"),
            )

            continue

        # ====================================================
        # DIRECT SPEECH
        # ====================================================

        if not article_has_direct_member_signal(
            article,
            member_terms,
        ):

            print(
                "[INFOMAX SKIP NONSPEECH]",
                article.get("title"),
            )

            continue

        # ====================================================
        # META
        # ====================================================

        article.update({
            "member_name_en":
                member_name_en,

            "member_name_ko":
                member_name_ko,

            "speaker_raw":
                member_name_en,

            "source":
                "Yonhap Infomax",

            "source_type":
                "INFOMAX",

            "matched":
                True,
        })

        final.append(
            article
        )

        print(
            "[INFOMAX OK]",
            article.get(
                "published_at"
            ),
            "| speech=",
            article.get(
                "actual_speech_date"
            ),
            "|",
            article.get(
                "title"
            ),
        )

        if len(final) >= max_results:
            break

        time.sleep(
            REQUEST_SLEEP
        )

    final.sort(
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

    return final


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    from pprint import pprint

    print()
    print(
        "=" * 90
    )
    print(
        "INFOMAX TEST - JEFFREY SCHMID"
    )
    print(
        "=" * 90
    )

    results = (
        crawl_infomax_member_news(

            member_name_en=(
                "Jeffrey Schmid"
            ),

            member_name_ko=(
                "제프리 슈미드"
            ),

            aliases=[
                "슈미드",
                "제프 슈미드",
                "캔자스시티 연은 총재",
                "캔자스시티 연방준비은행 총재",
            ],

            max_results=20,
            year=2026,
        )
    )

    print()
    print(
        "FINAL COUNT:",
        len(results)
    )

    for item in results:

        pprint({
            "published":
                item.get(
                    "published_at"
                ),

            "speech_date":
                item.get(
                    "actual_speech_date"
                ),

            "title":
                item.get(
                    "title"
                ),

            "url":
                item.get(
                    "url"
                ),

            "preview":
                (
                    item.get(
                        "text"
                    )
                    or ""
                )[:500],
        })