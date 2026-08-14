# crawlers/news.py

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from email.utils import (
    parsedate_to_datetime,
)

from urllib.parse import (
    quote_plus,
)

import html
import re
import xml.etree.ElementTree as ET

import requests


GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search"
)

DEFAULT_LOOKBACK_DAYS = 90
DEFAULT_MAX_RESULTS = 10


# ============================================================
# PREFERRED SOURCES
# ============================================================

PREFERRED_SOURCES = {
    "Reuters",
    "Bloomberg",
    "Bloomberg.com",
    "CNBC",
    "Financial Times",
    "WSJ",
    "The Wall Street Journal",
    "The Washington Post",
    "Associated Press",
    "AP News",
    "American Banker",
    "MarketWatch",
    "Barron's",
}


# ============================================================
# POLICY TERMS
# ============================================================

POLICY_TERMS = [
    "rate",
    "rates",
    "interest rate",
    "interest rates",
    "inflation",
    "monetary policy",
    "policy stance",
    "tightening",
    "easing",
    "hike",
    "hiking",
    "cut",
    "cuts",
    "cutting",
    "hold",
    "restrictive",
    "employment",
    "labor market",
    "labour market",
    "price stability",
    "2%",
]


# ============================================================
# CLEARLY IRRELEVANT TOPICS
# ============================================================

IRRELEVANT_TERMS = [
    "private dinner",
    "bank of america dinner",
    "quiet period",
    "watchdog",
    "ethics",
    "investigate",
    "senate scrutiny",
    "spending practices",
    "wall street bankers",
]


# ============================================================
# TEXT CLEAN
# ============================================================

def _clean_html_text(
    value,
):

    if not value:
        return ""

    value = html.unescape(
        str(value)
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ============================================================
# DATE
# ============================================================

def _parse_rss_date(
    value,
):

    if not value:
        return None

    try:

        dt = parsedate_to_datetime(
            value
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt

    except Exception:

        return None


# ============================================================
# NORMALIZE TITLE FOR DEDUP
# ============================================================

def _normalize_title(
    title,
):

    title = (
        title
        or ""
    ).lower()

    title = re.sub(
        r"[^a-z0-9\s]",
        " ",
        title,
    )

    title = re.sub(
        r"\s+",
        " ",
        title,
    )

    return title.strip()


# ============================================================
# MEMBER TERMS
# ============================================================

def _member_terms(
    member_name,
):

    name = (
        member_name
        or ""
    ).strip()

    parts = (
        name.split()
    )

    terms = []

    if name:

        terms.append(
            name.lower()
        )

    if parts:

        surname = (
            parts[-1].lower()
        )

        if len(
            surname
        ) >= 4:

            terms.append(
                surname
            )

    return list(
        dict.fromkeys(
            terms
        )
    )


# ============================================================
# MEMBER RELEVANCE
# ============================================================

def _mentions_member(
    member_name,
    title,
    description,
):

    text = (
        (
            title
            or ""
        )
        + " "
        + (
            description
            or ""
        )
    ).lower()

    terms = (
        _member_terms(
            member_name
        )
    )

    return any(
        term in text
        for term in terms
    )


# ============================================================
# POLICY RELEVANCE
# ============================================================

def _is_policy_relevant(
    title,
    description,
):

    text = (
        (
            title
            or ""
        )
        + " "
        + (
            description
            or ""
        )
    ).lower()

    if any(
        token in text
        for token in IRRELEVANT_TERMS
    ):

        return False

    return any(
        token in text
        for token in POLICY_TERMS
    )


# ============================================================
# GOOGLE NEWS SEARCH
# ============================================================

def search_google_news(
    query,
    member_name=None,
    lookback_days=DEFAULT_LOOKBACK_DAYS,
    max_results=DEFAULT_MAX_RESULTS,
):

    encoded_query = quote_plus(
        query
    )

    url = (
        f"{GOOGLE_NEWS_RSS}"
        f"?q={encoded_query}"
        f"&hl=en-US"
        f"&gl=US"
        f"&ceid=US:en"
    )

    response = requests.get(
        url,
        timeout=(
            5,
            15,
        ),
        headers={
            "User-Agent":
                (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
                )
        },
    )

    response.raise_for_status()

    root = ET.fromstring(
        response.content
    )

    cutoff = (
        datetime.now(
            timezone.utc
        )
        -
        timedelta(
            days=lookback_days
        )
    )

    raw_results = []

    for item in root.findall(
        ".//item"
    ):

        title_node = (
            item.find(
                "title"
            )
        )

        link_node = (
            item.find(
                "link"
            )
        )

        date_node = (
            item.find(
                "pubDate"
            )
        )

        source_node = (
            item.find(
                "source"
            )
        )

        description_node = (
            item.find(
                "description"
            )
        )

        title = _clean_html_text(
            title_node.text
            if title_node is not None
            else ""
        )

        link = (
            link_node.text
            if link_node is not None
            else ""
        )

        source = _clean_html_text(
            source_node.text
            if source_node is not None
            else ""
        )

        description = _clean_html_text(
            description_node.text
            if description_node is not None
            else ""
        )

        published_dt = (
            _parse_rss_date(
                date_node.text
                if date_node is not None
                else ""
            )
        )

        if (
            published_dt
            and
            published_dt < cutoff
        ):

            continue

        # Google News 제목 뒤 "- Reuters" 제거
        if (
            source
            and
            title.endswith(
                f" - {source}"
            )
        ):

            title = title[
                : -len(
                    f" - {source}"
                )
            ].strip()

        if not title:
            continue

        # -----------------------------------------------
        # 인물 자체가 title/description에 있어야 함
        # -----------------------------------------------

        if (
            member_name
            and
            not _mentions_member(
                member_name,
                title,
                description,
            )
        ):

            continue

        # -----------------------------------------------
        # 실제 통화정책 기사인가
        # -----------------------------------------------

        if not _is_policy_relevant(
            title,
            description,
        ):

            continue

        raw_results.append({

            "title":
                title,

            "description":
                description,

            "url":
                link,

            "source":
                source,

            "published_at":
                (
                    published_dt
                    .date()
                    .isoformat()

                    if published_dt

                    else None
                ),

            "preferred_source":
                (
                    source
                    in PREFERRED_SOURCES
                ),
        })

    # ========================================================
    # DUPLICATE HEADLINES
    # ========================================================

    deduped = []

    seen_titles = set()

    for item in sorted(
        raw_results,
        key=lambda x: (
            x.get(
                "preferred_source",
                False
            ),
            x.get(
                "published_at"
            )
            or "",
        ),
        reverse=True,
    ):

        normalized = (
            _normalize_title(
                item.get(
                    "title"
                )
            )
        )

        # 완전히 같거나 상당히 비슷한 재전송 기사 방지
        duplicate = False

        for seen in seen_titles:

            if (
                normalized == seen
                or
                (
                    len(
                        normalized
                    ) >= 35
                    and
                    (
                        normalized in seen
                        or
                        seen in normalized
                    )
                )
            ):

                duplicate = True
                break

        if duplicate:
            continue

        seen_titles.add(
            normalized
        )

        deduped.append(
            item
        )

        if (
            len(
                deduped
            )
            >= max_results
        ):

            break

    return deduped


# ============================================================
# MEMBER SEARCH
# ============================================================

def search_member_news(
    member_name,
    lookback_days=90,
    max_results=10,
):

    query = (
        f'"{member_name}" '
        f'Federal Reserve '
        f'("interest rates" OR inflation OR '
        f'"monetary policy" OR '
        f'"rate hike" OR "rate cut")'
    )

    return search_google_news(
        query=query,
        member_name=member_name,
        lookback_days=lookback_days,
        max_results=max_results,
    )