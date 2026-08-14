# processors/news_stance.py

import re


# ============================================================
# SCORE -> LABEL
# ============================================================

def score_to_label(score):

    if score >= 4:
        return "HAWKISH"

    if score >= 1:
        return "NEUTRAL_HAWKISH"

    if score <= -4:
        return "DOVISH"

    if score <= -1:
        return "NEUTRAL_DOVISH"

    return "NEUTRAL"


# ============================================================
# STRONG DOVISH CONTEXT
#
# 금리 인상 관련 단어가 있더라도
# "인상 반대", "인상 경계" 등의 문맥이면
# 비둘기파로 판정
# ============================================================

STRONG_DOVISH_RULES = [

    (
        r"\b"
        r"(warn|warns|warned)"
        r".{0,25}"
        r"against"
        r".{0,25}"
        r"(hike|hiking|raise|raising)"
        r"\b",
        -5,
        "warns against hikes",
    ),

    (
        r"\b"
        r"(push|pushes|pushed)"
        r".{0,15}"
        r"back"
        r".{0,15}"
        r"against"
        r".{0,25}"
        r"(hike|hiking|raise|raising)"
        r"\b",
        -5,
        "pushes back against hikes",
    ),

    (
        r"\b"
        r"(reject|rejects|rejected)"
        r".{0,30}"
        r"(hike|hiking|higher rate|higher rates)"
        r"\b",
        -5,
        "rejects rate hikes",
    ),

    (
        r"\b"
        r"against"
        r".{0,25}"
        r"(rate hike|rate hikes|hiking interest rates)"
        r"\b",
        -5,
        "against rate hikes",
    ),

    (
        r"\b"
        r"(look through|looks through|looking through)"
        r".{0,35}"
        r"(inflation|price|prices|shock|bump)"
        r"\b",
        -4,
        "looks through inflation shock",
    ),

    (
        r"\b"
        r"(wary|cautious)"
        r".{0,30}"
        r"(reacting|responding)"
        r".{0,30}"
        r"(inflation|price|energy)"
        r"\b",
        -3,
        "cautious on inflation response",
    ),
]


# ============================================================
# NORMAL DOVISH RULES
# ============================================================

DOVISH_RULES = [

    (
        r"\b"
        r"(support|supports|supported|"
        r"favor|favors|favours|"
        r"open to|prepared to|ready to)"
        r".{0,30}"
        r"(cut|cuts|cutting|lower|lowering)"
        r".{0,20}"
        r"(rate|rates|interest rate|interest rates)"
        r"\b",
        -5,
        "supports cuts",
    ),

    (
        r"\b"
        r"(rate cut|rate cuts|lower interest rates)"
        r"\b",
        -3,
        "rate cuts",
    ),

    (
        r"\b"
        r"inflation"
        r".{0,30}"
        r"(falling|cooling|easing|declining|temporary|transitory)"
        r"\b",
        -2,
        "disinflation",
    ),

    (
        r"\b"
        r"(inflation|price pressures)"
        r".{0,30}"
        r"(moderating|softening|subsiding)"
        r"\b",
        -2,
        "inflation moderating",
    ),

    (
        r"\b"
        r"(labor market|labour market|job market|employment)"
        r".{0,30}"
        r"(weak|weakening|slowing|softening|downside)"
        r"\b",
        -3,
        "labor downside",
    ),

    (
        r"\b"
        r"(economic growth|economy|growth)"
        r".{0,30}"
        r"(weak|weakening|slowing|softening|downside)"
        r"\b",
        -2,
        "growth downside",
    ),
]


# ============================================================
# HAWKISH RULES
# ============================================================

HAWKISH_RULES = [

    (
        r"\b"
        r"(support|supports|supported|"
        r"favor|favors|favours|"
        r"open to|prepared to|ready to|"
        r"consider|considers|considering)"
        r".{0,30}"
        r"(raise|raising|hike|hiking)"
        r".{0,20}"
        r"(rate|rates|interest rate|interest rates)"
        r"\b",
        5,
        "supports hikes",
    ),

    (
        r"\b"
        r"(possible|potential|further|additional)"
        r".{0,20}"
        r"(rate hike|rate hikes|tightening)"
        r"\b",
        3,
        "possible tightening",
    ),

    (
        r"\b"
        r"(no rush|not in a hurry|not ready|premature)"
        r".{0,30}"
        r"(cut|cuts|cutting|lower|lowering)"
        r"\b",
        5,
        "resists cuts",
    ),

    (
        r"\b"
        r"(hold|holds|holding|keep|keeps|maintain|maintains)"
        r".{0,20}"
        r"(rate|rates|policy rate)"
        r"\b",
        2,
        "hold rates",
    ),

    (
        r"\b"
        r"inflation"
        r".{0,30}"
        r"(too high|elevated|persistent|sticky|above target)"
        r"\b",
        3,
        "inflation concern",
    ),

    (
        r"\b"
        r"(inflation risk|inflation risks|"
        r"upside risk to inflation|upside risks to inflation)"
        r"\b",
        3,
        "inflation upside risks",
    ),

    (
        r"\b"
        r"(progress|disinflation)"
        r".{0,30}"
        r"(stalled|stalling|stopped)"
        r"\b",
        3,
        "disinflation stalled",
    ),

    (
        r"\b"
        r"(restrictive|restrictive policy)"
        r".{0,30}"
        r"(remain|maintain|needed|necessary)"
        r"\b",
        3,
        "restrictive policy needed",
    ),
]


# ============================================================
# SCORE SINGLE NEWS ARTICLE
# ============================================================

def score_news_text(text):

    text = (
        str(text or "")
        .lower()
        .strip()
    )

    hawk_matches = []
    dove_matches = []

    # --------------------------------------------------------
    # 1. Strong dovish context
    # --------------------------------------------------------

    for (
        pattern,
        weight,
        reason,
    ) in STRONG_DOVISH_RULES:

        if re.search(
            pattern,
            text,
            flags=re.I,
        ):

            dove_matches.append(
                (
                    weight,
                    reason,
                )
            )

    # --------------------------------------------------------
    # 2. Normal dovish
    # --------------------------------------------------------

    for (
        pattern,
        weight,
        reason,
    ) in DOVISH_RULES:

        if re.search(
            pattern,
            text,
            flags=re.I,
        ):

            dove_matches.append(
                (
                    weight,
                    reason,
                )
            )

    # --------------------------------------------------------
    # 3. Hawkish
    # --------------------------------------------------------

    for (
        pattern,
        weight,
        reason,
    ) in HAWKISH_RULES:

        if re.search(
            pattern,
            text,
            flags=re.I,
        ):

            hawk_matches.append(
                (
                    weight,
                    reason,
                )
            )

    # ========================================================
    # NEGATION PROTECTION
    #
    # 예:
    #
    # warns against hiking rates
    # rejects rate hikes
    # pushes back against rate hikes
    #
    # → "hike"라는 단어가 있어도
    #   hawkish 신호로 다시 잡지 않는다.
    # ========================================================

    strong_dove = any(
        weight <= -4
        for weight, _
        in dove_matches
    )

    if strong_dove:

        hawk_matches = [
            (
                weight,
                reason,
            )
            for (
                weight,
                reason,
            )
            in hawk_matches
            if reason not in [
                "supports hikes",
                "possible tightening",
            ]
        ]

    # ========================================================
    # SAME-DIRECTION DUPLICATE PROTECTION
    #
    # 같은 기사에서
    #
    # warns against hikes      -5
    # against rate hikes       -5
    #
    # 둘 다 잡혀도 -10으로 만들지 않는다.
    #
    # 가장 강한 신호 하나만 사용.
    # ========================================================

    if hawk_matches:

        strongest_hawk = max(
            hawk_matches,
            key=lambda x: x[0],
        )

        hawk_score = (
            strongest_hawk[0]
        )

        hawk_hits = [
            strongest_hawk[1]
        ]

    else:

        hawk_score = 0
        hawk_hits = []

    if dove_matches:

        strongest_dove = min(
            dove_matches,
            key=lambda x: x[0],
        )

        dove_score = (
            strongest_dove[0]
        )

        dove_hits = [
            strongest_dove[1]
        ]

    else:

        dove_score = 0
        dove_hits = []

    # ========================================================
    # FINAL ARTICLE SCORE
    # ========================================================

    score = (
        hawk_score
        +
        dove_score
    )

    # 한 기사 최대 ±5
    score = max(
        -5,
        min(
            5,
            score,
        ),
    )

    return {

        "score":
            score,

        "label":
            score_to_label(
                score
            ),

        "hawkish_score":
            max(
                score,
                0,
            ),

        "dovish_score":
            abs(
                min(
                    score,
                    0,
                )
            ),

        "hawk_hits":
            hawk_hits,

        "dove_hits":
            dove_hits,
    }


# ============================================================
# ANALYZE MEMBER NEWS
# ============================================================

def analyze_member_news(
    news_items,
):

    # --------------------------------------------------------
    # No news
    # --------------------------------------------------------

    if not news_items:

        return {

            "news_score":
                None,

            "news_label":
                "INSUFFICIENT",

            "news_count":
                0,

            "news_usable_count":
                0,

            "news_confidence":
                "LOW",

            "news_articles":
                [],
        }

    analyzed = []

    weighted_scores = []

    # ========================================================
    # Analyze each article
    # ========================================================

    for article in news_items:

        item = dict(
            article
        )

        # title + RSS description 같이 분석
        analysis_text = (
            (
                item.get(
                    "title"
                )
                or ""
            )
            + ". "
            +
            (
                item.get(
                    "description"
                )
                or ""
            )
        )

        analysis = (
            score_news_text(
                analysis_text
            )
        )

        item.update(
            analysis
        )

        analyzed.append(
            item
        )

        score = (
            analysis[
                "score"
            ]
        )

        # Neutral headline은
        # consensus 계산에 사용하지 않음
        if score == 0:
            continue

        # ----------------------------------------------------
        # Source weighting
        # ----------------------------------------------------

        if item.get(
            "preferred_source"
        ):

            weight = 1.5

        else:

            weight = 1.0

        weighted_scores.append(
            (
                score,
                weight,
            )
        )

    # ========================================================
    # No usable stance articles
    # ========================================================

    if not weighted_scores:

        return {

            "news_score":
                None,

            "news_label":
                "INSUFFICIENT",

            "news_count":
                len(
                    analyzed
                ),

            "news_usable_count":
                0,

            "news_confidence":
                "LOW",

            "news_articles":
                analyzed,
        }

    # ========================================================
    # Weighted average
    # ========================================================

    numerator = sum(
        score * weight
        for score, weight
        in weighted_scores
    )

    denominator = sum(
        weight
        for _, weight
        in weighted_scores
    )

    news_score = round(
        numerator
        /
        denominator,
        2,
    )

    usable_count = (
        len(
            weighted_scores
        )
    )

    # ========================================================
    # Preferred source count
    # ========================================================

    preferred_usable = sum(
        1
        for article in analyzed
        if (
            article.get(
                "preferred_source"
            )
            and
            article.get(
                "score"
            )
            != 0
        )
    )

    # ========================================================
    # Confidence
    # ========================================================

    if (
        usable_count >= 4
        and
        preferred_usable >= 2
    ):

        confidence = (
            "HIGH"
        )

    elif (
        usable_count >= 2
        and
        preferred_usable >= 1
    ):

        confidence = (
            "MEDIUM"
        )

    elif (
        usable_count >= 2
    ):

        confidence = (
            "MEDIUM"
        )

    else:

        confidence = (
            "LOW"
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "news_score":
            news_score,

        "news_label":
            score_to_label(
                news_score
            ),

        "news_count":
            len(
                analyzed
            ),

        "news_usable_count":
            usable_count,

        "news_confidence":
            confidence,

        "news_articles":
            analyzed,
    }