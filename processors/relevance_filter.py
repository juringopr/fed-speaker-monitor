# processors/relevance_filter.py


# ============================================================
# 1. DIRECT MONETARY POLICY
# ============================================================

POLICY_SIGNALS = {

    "monetary policy": 6,
    "fomc": 6,

    "federal funds rate": 6,
    "fed funds rate": 6,

    "policy rate": 5,

    "rate cut": 5,
    "rate cuts": 5,

    "cut rates": 5,
    "cut interest rates": 5,

    "rate hike": 5,
    "rate hikes": 5,

    "raise rates": 5,
    "raise interest rates": 5,

    "interest rate": 3,
    "interest rates": 3,

    "policy stance": 4,

    "restrictive": 4,

    "tightening": 4,
    "easing": 4,

    "neutral rate": 4,

    "balance sheet": 4,

    "quantitative tightening": 5,
    "quantitative easing": 5,
}


# ============================================================
# 2. DUAL MANDATE
# ============================================================

DUAL_MANDATE_SIGNALS = {

    "inflation": 3,

    "price stability": 4,

    "pce": 3,
    "core pce": 4,

    "consumer price": 2,

    "employment": 3,

    "labor market": 3,
    "labour market": 3,

    "unemployment": 3,

    "payroll": 2,
    "payrolls": 2,

    "job market": 2,

    "jobs": 1,

    "wage": 2,
    "wages": 2,
}


# ============================================================
# 3. MACRO / ECONOMIC OUTLOOK
# ============================================================

MACRO_SIGNALS = {

    "economic outlook": 4,

    "economic activity": 2,

    "economic growth": 2,

    "economy": 1,

    "growth": 1,

    "gdp": 2,

    "recession": 3,

    "consumer spending": 2,

    "consumption": 1,

    "business investment": 2,

    "productivity": 1,

    "tariff": 2,
    "tariffs": 2,

    "trade policy": 2,

    "financial conditions": 3,

    "credit conditions": 2,

    "financial stability": 2,

    "supply shock": 2,
    "supply shocks": 2,
}


# ============================================================
# 4. LOWER POLICY RELEVANCE
#
# 단, 여기 단어가 있다고 무조건 LOW 처리하지 않는다.
# 통화정책 키워드가 같이 있으면 정책 점수가 이김.
# ============================================================

LOW_RELEVANCE_SIGNALS = {

    "commencement": -3,

    "financial inclusion": -2,

    "community development": -2,

    "cybersecurity": -2,

    "responsible innovation": -2,

    "payments conference": -2,

    "bank supervision": -1,

    "bank regulation": -1,
}


# ============================================================
# CATEGORY SCORE
# ============================================================

def _score_signal_group(
    text,
    signal_map,
    category,
):

    score = 0

    matches = []

    for phrase, weight in (
        signal_map.items()
    ):

        if phrase in text:

            score += weight

            matches.append({
                "phrase": phrase,
                "weight": weight,
                "category": category,
            })

    return score, matches


# ============================================================
# MAIN
# ============================================================

def calculate_fomc_relevance(
    article
):
    """
    FOMC / 경제 / 통화정책 관련성을 점수화.

    fetch_body=False:
        제목 기반 1차 평가

    fetch_body=True 이후:
        title + 실제 연설본문 기반 평가

    데이터를 삭제하지 않는다.
    HIGH / MEDIUM / LOW label만 부여한다.
    """

    title = str(
        article.get(
            "title"
        )
        or ""
    ).lower()

    text = str(
        article.get(
            "text"
        )
        or ""
    ).lower()

    combined = (
        title
        + "\n"
        + text
    )

    # ========================================================
    # POLICY
    # ========================================================

    policy_score, policy_matches = (
        _score_signal_group(
            combined,
            POLICY_SIGNALS,
            "POLICY",
        )
    )

    # ========================================================
    # DUAL MANDATE
    # ========================================================

    dual_score, dual_matches = (
        _score_signal_group(
            combined,
            DUAL_MANDATE_SIGNALS,
            "DUAL_MANDATE",
        )
    )

    # ========================================================
    # MACRO
    # ========================================================

    macro_score, macro_matches = (
        _score_signal_group(
            combined,
            MACRO_SIGNALS,
            "MACRO",
        )
    )

    # ========================================================
    # LOW RELEVANCE
    # ========================================================

    penalty_score, penalty_matches = (
        _score_signal_group(
            combined,
            LOW_RELEVANCE_SIGNALS,
            "LOW_RELEVANCE",
        )
    )

    total_score = (
        policy_score
        + dual_score
        + macro_score
        + penalty_score
    )

    total_score = max(
        total_score,
        0
    )

    # ========================================================
    # IMPORTANT OVERRIDES
    #
    # 통화정책을 직접 언급한다면
    # commencement/opening remarks 같은 표현 때문에
    # LOW가 되는 것을 막는다.
    # ========================================================

    if policy_score >= 6:

        label = "HIGH"

    elif (
        policy_score >= 3
        and dual_score >= 3
    ):

        label = "HIGH"

    elif total_score >= 8:

        label = "HIGH"

    elif total_score >= 4:

        label = "MEDIUM"

    else:

        label = "LOW"

    # ========================================================
    # BODY STATUS
    # ========================================================

    has_body = (
        len(text.strip())
        >= 100
    )

    return {

        "fomc_relevance_score":
            total_score,

        "fomc_relevance":
            label,

        "policy_score":
            policy_score,

        "dual_mandate_score":
            dual_score,

        "macro_score":
            macro_score,

        "relevance_has_body":
            has_body,

        "relevance_matches":
            (
                policy_matches
                + dual_matches
                + macro_matches
                + penalty_matches
            ),
    }


# ============================================================
# OPTIONAL FILTER
# ============================================================

def filter_by_relevance(
    articles,
    minimum="MEDIUM",
):

    ranks = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
    }

    minimum_rank = ranks.get(
        minimum,
        2
    )

    results = []

    for article in articles:

        item = dict(
            article
        )

        relevance = (
            calculate_fomc_relevance(
                item
            )
        )

        item.update(
            relevance
        )

        label = item.get(
            "fomc_relevance"
        )

        rank = ranks.get(
            label,
            1
        )

        if rank >= minimum_rank:

            results.append(
                item
            )

    return results