# processors/event_key.py

import re
import hashlib

import pandas as pd


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_event_text(
    value,
):

    if value is None:
        return ""

    value = str(
        value
    ).lower()

    value = re.sub(
        r"https?://\S+",
        " ",
        value,
    )

    value = re.sub(
        r"\s*-\s*연합인포맥스\s*$",
        "",
        value,
    )

    value = re.sub(
        r"\b(reuters|bloomberg|cnbc|wsj|yonhap infomax)\b",
        " ",
        value,
    )

    value = re.sub(
        r"[^0-9a-zA-Z가-힣\s]",
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

def _to_date_string(
    value,
):

    if value is None:
        return None

    try:

        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(
            parsed
        ):
            return None

        return parsed.strftime(
            "%Y-%m-%d"
        )

    except Exception:
        return None


def _to_timestamp(
    value,
):

    if value is None:
        return pd.NaT

    try:

        return pd.to_datetime(
            value,
            errors="coerce",
        )

    except Exception:

        return pd.NaT


# ============================================================
# EVENT DATE
# ============================================================

def infer_event_date(
    article,
):
    """
    실제 발언일 우선.

    Infomax:
        actual_speech_date -> 기사 속 실제 발언일
        published_at       -> 기사 게재일

    Official:
        speech_date / event_date / published_at
    """

    for key in [
        "actual_speech_date",
        "speech_date",
        "event_date",
        "published_at",
        "Date",
        "date",
    ]:

        value = article.get(
            key
        )

        date_string = (
            _to_date_string(
                value
            )
        )

        if date_string:
            return date_string

    return None


# ============================================================
# EVENT SIGNATURE TEXT
# ============================================================

def build_event_signature_text(
    article,
):

    title = normalize_event_text(
        article.get(
            "title"
        )
        or
        article.get(
            "Title"
        )
        or
        ""
    )

    topics = (
        article.get(
            "topics"
        )
        or
        article.get(
            "Topics"
        )
        or
        []
    )

    if isinstance(
        topics,
        list,
    ):

        topics_text = " ".join(
            normalize_event_text(
                topic
            )
            for topic
            in topics
        )

    else:

        topics_text = (
            normalize_event_text(
                topics
            )
        )

    body = normalize_event_text(
        article.get(
            "text"
        )
        or
        article.get(
            "body"
        )
        or
        ""
    )

    body = body[
        :1000
    ]

    return normalize_event_text(
        f"{title} "
        f"{topics_text} "
        f"{body}"
    )


# ============================================================
# POLICY FINGERPRINT
# ============================================================

POLICY_FINGERPRINTS = {

    "RATE_HIKE": [
        "rate hike",
        "rate hikes",
        "raise rates",
        "raise interest rates",
        "higher rates",
        "higher interest rates",
        "금리 인상",
        "금리인상",
        "금리를 인상",
        "금리를 올려",
        "더 높은 금리",
    ],

    "RATE_CUT": [
        "rate cut",
        "rate cuts",
        "cut rates",
        "lower rates",
        "lower interest rates",
        "금리 인하",
        "금리인하",
        "금리를 인하",
        "금리를 내려",
    ],

    "HOLD": [
        "hold rates",
        "hold rates steady",
        "keep rates unchanged",
        "rates unchanged",
        "금리 동결",
        "금리동결",
        "동결을 지지",
        "현 금리 수준",
    ],

    "TIGHTENING": [
        "tightening",
        "further tightening",
        "additional tightening",
        "restrictive policy",
        "restrictive stance",
        "more restrictive",
        "tighter monetary policy",
        "긴축",
        "긴축적",
        "긴축적인",
        "제약적",
        "더 제약적인",
        "더욱 긴축적인 정책",
    ],

    "EASING": [
        "easing",
        "policy easing",
        "less restrictive",
        "accommodative",
        "완화",
        "완화적",
        "정책 완화",
    ],

    "INFLATION_HIGH": [
        "inflation too high",
        "inflation remains too high",
        "inflation is too high",
        "inflation remains elevated",
        "persistent inflation",
        "인플레이션이 너무 높",
        "인플레가 너무 높",
        "인플레이션이 지나치게 높",
        "인플레가 지나치게 높",
        "인플레이션이 너무 뜨겁",
        "인플레가 너무 뜨겁",
    ],

    "INFLATION_RISK": [
        "inflation risk",
        "inflation risks",
        "upside risks to inflation",
        "inflationary pressures",
        "inflation pressure",
        "inflation expectations",
        "persistent inflation",
        "인플레이션 위험",
        "인플레 위험",
        "인플레이션 압력",
        "인플레 압력",
        "인플레이션 상방 위험",
        "인플레 상방 위험",
        "인플레이션 고착",
        "인플레 고착",
        "기대 인플레이션",
    ],

    "INFLATION_IMPROVING": [
        "disinflation",
        "inflation is declining",
        "inflation has declined",
        "inflation has eased",
        "inflation moving toward target",
        "inflation moving towards target",
        "인플레이션 둔화",
        "인플레 둔화",
        "인플레이션 하락",
        "인플레 하락",
        "2% 목표로 복귀",
        "2%로 복귀",
        "디스인플레이션",
    ],

    "LABOR_STRONG": [
        "labor market remains strong",
        "labor market remains solid",
        "labor market resilient",
        "employment remains strong",
        "고용 꽤 좋",
        "고용 견조",
        "노동시장 견조",
        "노동시장이 견조",
    ],

    "LABOR_WEAK": [
        "labor market weakening",
        "labor market has weakened",
        "labor market is cooling",
        "labor market has cooled",
        "downside risks to employment",
        "고용 하방 위험",
        "노동시장 하방 위험",
        "고용 악화",
        "노동시장 약화",
    ],

    "GROWTH_STRONG": [
        "economy remains strong",
        "economy remains resilient",
        "strong demand",
        "economic activity remains strong",
        "경제가 탄탄",
        "경제는 탄탄",
        "경제가 견조",
        "경제는 견조",
        "수요가 강",
    ],

    "GROWTH_WEAK": [
        "growth has slowed",
        "economic activity has slowed",
        "downside risks to growth",
        "growth weakening",
        "경기 둔화",
        "성장 둔화",
        "성장 약화",
    ],

    "BALANCE_SHEET": [
        "balance sheet",
        "reserves",
        "reserve balances",
        "대차대조표",
        "준비금",
        "지준",
    ],
}


def extract_policy_fingerprint(
    article,
):
    """
    Official / Infomax 동일 발언 매칭용.

    예:
        Official:
            "more restrictive policy may be needed"

        Infomax:
            "더 긴축적인 정책이 필요"

        둘 다:
            {"TIGHTENING", ...}
    """

    title = str(
        article.get(
            "title"
        )
        or
        article.get(
            "Title"
        )
        or
        ""
    )

    text = str(
        article.get(
            "text"
        )
        or
        article.get(
            "body"
        )
        or
        ""
    )

    combined = normalize_event_text(
        title
        +
        " "
        +
        text[:8000]
    )

    fingerprints = set()

    for (
        label,
        phrases,
    ) in POLICY_FINGERPRINTS.items():

        for phrase in phrases:

            normalized_phrase = (
                normalize_event_text(
                    phrase
                )
            )

            if (
                normalized_phrase
                and
                normalized_phrase
                in combined
            ):

                fingerprints.add(
                    label
                )

                break

    return fingerprints


# ============================================================
# SIMPLE EVENT KEY
# ============================================================

def build_event_key(
    article,
):
    """
    member + actual event date + policy fingerprint

    fingerprint가 없을 때만 text signature 사용.
    """

    member = normalize_event_text(
        article.get(
            "member_name_en"
        )
        or
        article.get(
            "Speaker"
        )
        or
        ""
    )

    event_date = (
        infer_event_date(
            article
        )
        or
        "unknown-date"
    )

    fingerprints = sorted(
        extract_policy_fingerprint(
            article
        )
    )

    if fingerprints:

        signature = "|".join(
            fingerprints
        )

    else:

        signature = (
            build_event_signature_text(
                article
            )
        )

    digest = (
        hashlib.sha1(
            signature.encode(
                "utf-8"
            )
        )
        .hexdigest()[
            :12
        ]
    )

    return (
        f"{member}|"
        f"{event_date}|"
        f"{digest}"
    )


# ============================================================
# TOKEN SET
# ============================================================

def _token_set(
    text,
):

    normalized = (
        normalize_event_text(
            text
        )
    )

    return {
        token
        for token
        in normalized.split()
        if len(token) >= 2
    }


# ============================================================
# TEXT SIMILARITY
# ============================================================

def event_similarity(
    article_a,
    article_b,
):

    text_a = (
        (
            article_a.get(
                "title"
            )
            or
            ""
        )
        +
        " "
        +
        (
            article_a.get(
                "text"
            )
            or
            ""
        )[:1000]
    )

    text_b = (
        (
            article_b.get(
                "title"
            )
            or
            ""
        )
        +
        " "
        +
        (
            article_b.get(
                "text"
            )
            or
            ""
        )[:1000]
    )

    tokens_a = (
        _token_set(
            text_a
        )
    )

    tokens_b = (
        _token_set(
            text_b
        )
    )

    if (
        not tokens_a
        or
        not tokens_b
    ):

        return 0.0

    intersection = len(
        tokens_a
        &
        tokens_b
    )

    union = len(
        tokens_a
        |
        tokens_b
    )

    if union == 0:
        return 0.0

    return (
        intersection
        /
        union
    )


# ============================================================
# STANCE DIRECTION
# ============================================================

def _stance_direction(
    article,
):

    value = article.get(
        "hawk_dove_score"
    )

    try:

        score = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0

    if score >= 1:
        return 1

    if score <= -1:
        return -1

    return 0


# ============================================================
# SAME EVENT
# ============================================================

def is_same_event(
    article_a,
    article_b,
    similarity_threshold=0.25,
    date_tolerance_days=1,
):
    """
    동일 event 조건:

    1. 같은 위원
    2. 실제 발언일 ±1일
    3. 아래 중 하나:
       - fingerprint 2개 이상 일치
       - text similarity 충분
       - 정확히 같은 날짜 + fingerprint 1개 이상 + stance 방향 동일
    """

    member_a = normalize_event_text(
        article_a.get(
            "member_name_en"
        )
        or
        article_a.get(
            "Speaker"
        )
        or
        ""
    )

    member_b = normalize_event_text(
        article_b.get(
            "member_name_en"
        )
        or
        article_b.get(
            "Speaker"
        )
        or
        ""
    )

    if (
        not member_a
        or
        not member_b
        or
        member_a
        != member_b
    ):

        return False

    date_a = _to_timestamp(
        infer_event_date(
            article_a
        )
    )

    date_b = _to_timestamp(
        infer_event_date(
            article_b
        )
    )

    if (
        pd.isna(
            date_a
        )
        or
        pd.isna(
            date_b
        )
    ):

        return False

    day_gap = abs(
        (
            date_a
            -
            date_b
        ).days
    )

    if (
        day_gap
        >
        date_tolerance_days
    ):

        return False

    # ========================================================
    # FINGERPRINT
    # ========================================================

    fp_a = (
        extract_policy_fingerprint(
            article_a
        )
    )

    fp_b = (
        extract_policy_fingerprint(
            article_b
        )
    )

    common_fp = (
        fp_a
        &
        fp_b
    )

    # 정책주제 2개 이상 일치하면
    # cross-language라도 같은 event 가능성이 높음
    if len(
        common_fp
    ) >= 2:

        return True

    # ========================================================
    # TEXT SIMILARITY
    # ========================================================

    similarity = (
        event_similarity(
            article_a,
            article_b,
        )
    )

    if (
        similarity
        >= similarity_threshold
    ):

        return True

    # ========================================================
    # SAME DATE + SAME DIRECTION
    # ========================================================

    if (
        day_gap == 0
        and
        len(
            common_fp
        ) >= 1
    ):

        direction_a = (
            _stance_direction(
                article_a
            )
        )

        direction_b = (
            _stance_direction(
                article_b
            )
        )

        if (
            direction_a != 0
            and
            direction_a
            ==
            direction_b
        ):

            return True

    return False


# ============================================================
# SOURCE PRIORITY
# ============================================================

SOURCE_PRIORITY = {

    "OFFICIAL":
        100,

    "FED_BOARD":
        100,

    "REGIONAL_FED":
        100,

    "INFOMAX":
        80,

    "NEWS":
        50,
}


def get_source_priority(
    article,
):

    source_type = (
        str(
            article.get(
                "source_type"
            )
            or
            ""
        )
        .upper()
        .strip()
    )

    return SOURCE_PRIORITY.get(
        source_type,
        0,
    )


# ============================================================
# MERGE EVENT
# ============================================================

def merge_event_group(
    articles,
):

    if not articles:
        return None

    sorted_articles = sorted(
        articles,
        key=get_source_priority,
        reverse=True,
    )

    # Official이 존재하면 Official을 대표 record로 사용
    base = dict(
        sorted_articles[0]
    )

    source_types = []
    sources = []
    urls = []
    titles = []

    all_fingerprints = set()

    for article in sorted_articles:

        source_type = (
            article.get(
                "source_type"
            )
        )

        source = (
            article.get(
                "source"
            )
        )

        url = (
            article.get(
                "url"
            )
            or
            article.get(
                "URL"
            )
        )

        title = (
            article.get(
                "title"
            )
            or
            article.get(
                "Title"
            )
        )

        if (
            source_type
            and
            source_type
            not in source_types
        ):

            source_types.append(
                source_type
            )

        if (
            source
            and
            source
            not in sources
        ):

            sources.append(
                source
            )

        if (
            url
            and
            url
            not in urls
        ):

            urls.append(
                url
            )

        if (
            title
            and
            title
            not in titles
        ):

            titles.append(
                title
            )

        # 실제 사용
        all_fingerprints.update(
            extract_policy_fingerprint(
                article
            )
        )

    upper_types = {
        str(
            value
        ).upper()
        for value
        in source_types
    }

    has_official = bool(
        upper_types
        &
        {
            "OFFICIAL",
            "FED_BOARD",
            "REGIONAL_FED",
        }
    )

    has_infomax = (
        "INFOMAX"
        in upper_types
    )

    if (
        has_official
        and
        has_infomax
    ):

        coverage = "BOTH"

    elif has_official:

        coverage = "OFFICIAL"

    elif has_infomax:

        coverage = "INFOMAX"

    else:

        coverage = "OTHER"

    base[
        "event_sources"
    ] = source_types

    base[
        "event_source_names"
    ] = sources

    base[
        "event_urls"
    ] = urls

    base[
        "event_titles"
    ] = titles

    base[
        "source_coverage"
    ] = coverage

    base[
        "event_source_count"
    ] = len(
        source_types
    )

    # fingerprint도 event metadata로 저장
    base[
        "policy_fingerprint"
    ] = sorted(
        all_fingerprints
    )

    base[
        "event_key"
    ] = (
        build_event_key(
            base
        )
    )

    return base


# ============================================================
# DEDUP EVENTS
# ============================================================

def deduplicate_events(
    articles,
    similarity_threshold=0.25,
    date_tolerance_days=1,
):

    articles = list(
        articles
        or []
    )

    articles = sorted(
        articles,
        key=lambda article: (
            normalize_event_text(
                article.get(
                    "member_name_en"
                )
                or
                article.get(
                    "Speaker"
                )
                or
                ""
            ),
            infer_event_date(
                article
            )
            or
            "",
        ),
    )

    groups = []

    for article in articles:

        matched_group = None

        for group in groups:

            # 기존처럼 representative 1개만 비교하지 않고
            # group 안의 모든 record와 비교
            if any(
                is_same_event(
                    article,
                    existing,
                    similarity_threshold=(
                        similarity_threshold
                    ),
                    date_tolerance_days=(
                        date_tolerance_days
                    ),
                )
                for existing
                in group
            ):

                matched_group = (
                    group
                )

                break

        if matched_group is None:

            groups.append(
                [
                    article
                ]
            )

        else:

            matched_group.append(
                article
            )

    merged = []

    for group in groups:

        event = (
            merge_event_group(
                group
            )
        )

        if event:

            merged.append(
                event
            )

    # 최신순
    merged.sort(
        key=lambda article: (
            infer_event_date(
                article
            )
            or
            ""
        ),
        reverse=True,
    )

    for index, event in enumerate(
        merged,
        start=1,
    ):

        event[
            "event_id"
        ] = (
            f"EVT{index:04d}"
        )

    return merged