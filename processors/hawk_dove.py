# processors/hawk_dove.py

import re


# ============================================================
# CONFIG
# ============================================================

MAX_SENTENCE_SCORE = 6
MAX_ARTICLE_SCORE = 20


# ============================================================
# POLICY CONTEXT
#
# rate / rates 같은 단어가 등장해도
# 통화정책 맥락인지 확인하기 위한 키워드.
# ============================================================

POLICY_CONTEXT_TERMS = [
    "federal funds",
    "fed funds",
    "funds rate",
    "policy rate",
    "interest rate",
    "interest rates",
    "monetary policy",
    "policy stance",
    "policy restraint",
    "restrictive policy",
    "restrictive stance",
    "easing policy",
    "policy easing",
    "policy tightening",
    "tightening policy",
    "fomc",
    "federal reserve",
    "central bank",
    "rate cut",
    "rate cuts",
    "rate hike",
    "rate hikes",
    "cut rates",
    "raise rates",
    "lower rates",
    "higher rates",
]


# ============================================================
# NON-POLICY RATE CONTEXT
#
# lower rates / higher rates가
# 정책금리가 아닌 일반적인 비율을 의미하는 경우 제외.
# ============================================================

NON_POLICY_RATE_TERMS = [
    "delinquent",
    "delinquency",
    "default rate",
    "default rates",
    "mortality rate",
    "mortality rates",
    "participation rate",
    "participation rates",
    "unemployment rate",
    "unemployment rates",
    "vacancy rate",
    "vacancy rates",
    "turnover rate",
    "turnover rates",
    "response rate",
    "response rates",
    "adoption rate",
    "adoption rates",
    "growth rate",
    "growth rates",
    "tax rate",
    "tax rates",
    "crime rate",
    "crime rates",
    "loan rate",
    "loan rates",
    "mortgage rate",
    "mortgage rates",
    "borrowing rate",
    "borrowing rates",
    "failure rate",
    "failure rates",
    "recovery rate",
    "recovery rates",
]


# ============================================================
# HAWKISH PHRASES
# ============================================================

HAWKISH_PHRASES = {

    # Inflation
    "inflation remains elevated": 3,
    "inflation remains too high": 4,
    "inflation is too high": 4,
    "inflation is still too high": 3,
    "inflation has been too high": 4,
    "inflation above target": 3,
    "inflation remains above target": 3,
    "above-target inflation": 3,
    "persistent inflation": 3,
    "inflationary pressures": 2,
    "upside risks to inflation": 4,

    # Restrictive policy
    "restrictive policy": 3,
    "restrictive stance": 3,
    "policy remains restrictive": 3,
    "appropriately restrictive": 2,
    "maintain a restrictive stance": 3,
    "maintain restrictive policy": 3,

    # Hikes / tighter
    "raise rates": 5,
    "raise interest rates": 5,
    "raise the policy rate": 5,
    "higher policy rate": 4,
    "rate hike": 4,
    "rate hikes": 4,
    "further tightening": 4,
    "additional tightening": 4,
    "tighten monetary policy": 4,
    "additional policy restraint": 4,

    # No easing
    "higher for longer": 4,
    "no rush to cut": 4,
    "no urgency to cut": 4,
    "not ready to cut": 4,
    "not appropriate to cut": 4,
    "pause in rate cuts": 3,
    "hold rates steady": 2,

    # Economy/labor supports restrictive stance
    "economy remains strong": 2,
    "economy remains resilient": 2,
    "labor market remains strong": 2,
    "labor market remains solid": 2,
}


# ============================================================
# DOVISH PHRASES
# ============================================================

DOVISH_PHRASES = {

    # Cuts / easing
    "rate cut": -3,
    "rate cuts": -3,
    "cut rates": -4,
    "cut interest rates": -4,
    "lower the policy rate": -4,
    "reduce the policy rate": -4,
    "lower interest rates": -4,
    "policy easing": -3,
    "easing of policy": -3,
    "less restrictive policy": -3,
    "less restrictive stance": -3,
    "reduce policy restraint": -4,
    "reduce the degree of policy restraint": -4,

    # Inflation progress
    "inflation is declining": -2,
    "inflation has declined": -2,
    "inflation has eased": -2,
    "price pressures have eased": -2,
    "inflation moving toward target": -3,
    "inflation moving towards target": -3,

    # Labor downside
    "labor market weakening": -4,
    "labor market has weakened": -4,
    "labor market has cooled": -3,
    "labor market is cooling": -3,
    "employment growth has slowed": -3,
    "job growth has slowed": -3,
    "unemployment has risen": -3,
    "downside risks to employment": -4,
    "risks to employment have increased": -4,

    # Growth downside
    "economic activity has slowed": -2,
    "growth has slowed": -2,
    "downside risks to growth": -3,
}


# ============================================================
# REGEX - HAWKISH
# ============================================================

HAWKISH_PATTERNS = [

    (
        r"inflation.{0,70}"
        r"(above|over).{0,30}"
        r"(target|goal|objective)",
        3,
        "inflation_above_target",
    ),

    (
        r"inflation.{0,60}"
        r"(elevated|too high|persistent)",
        3,
        "inflation_elevated",
    ),

    (
        r"(upside|higher).{0,40}"
        r"risk.{0,40}"
        r"inflation",
        4,
        "inflation_upside_risk",
    ),

    (
        r"(more|further|additional).{0,40}"
        r"progress.{0,40}"
        r"inflation",
        3,
        "need_more_inflation_progress",
    ),

    (
        r"(remain|keep|maintain).{0,50}"
        r"restrictive",
        3,
        "maintain_restrictive_policy",
    ),

    (
        r"(no|not).{0,20}"
        r"(rush|urgency).{0,50}"
        r"(cut|ease)",
        4,
        "no_rush_to_ease",
    ),

    (
        r"(prepared|ready|willing).{0,30}"
        r"(to )?"
        r"(raise|increase).{0,30}"
        r"(rate|rates|policy rate)",
        5,
        "prepared_to_raise",
    ),

    (
        r"(further|additional).{0,40}"
        r"(tightening|restraint)",
        4,
        "additional_restraint",
    ),
]


# ============================================================
# REGEX - DOVISH
# ============================================================

DOVISH_PATTERNS = [

    (
        r"inflation.{0,60}"
        r"(moving|returning|converging).{0,40}"
        r"(toward|towards|closer to).{0,30}"
        r"(target|goal|objective)",
        -3,
        "inflation_moving_to_target",
    ),

    (
        r"(labor|labour).{0,30}"
        r"market.{0,50}"
        r"(cool|weaken|soften)",
        -3,
        "labor_market_softening",
    ),

    (
        r"(downside|greater).{0,40}"
        r"risk.{0,50}"
        r"(employment|labor|labour)",
        -4,
        "employment_downside_risk",
    ),

    (
        r"(appropriate|reasonable|warranted).{0,60}"
        r"(cut|lower|reduce).{0,30}"
        r"(rate|rates|policy restraint)",
        -4,
        "easing_appropriate",
    ),

    (
        r"(reduce|lower).{0,25}"
        r"(the )?"
        r"(federal funds|funds|policy).{0,15}"
        r"rate",
        -4,
        "policy_rate_reduction",
    ),
]


# ============================================================
# CONDITIONAL HAWKISH PATTERNS
#
# "If disinflation does not continue, I am prepared to act"
# 같은 문장 처리.
# ============================================================

CONDITIONAL_HAWKISH_PATTERNS = [

    (
        r"if.{0,100}"
        r"(inflation|disinflation).{0,80}"
        r"(does not|doesn't|fails to|do not|not).{0,60}"
        r"(improve|decline|ease|continue|resume|progress).{0,100}"
        r"(prepared|ready|willing).{0,40}"
        r"(act|raise|tighten)",
        5,
        "conditional_tightening",
    ),

    (
        r"if.{0,100}"
        r"inflation.{0,80}"
        r"(persist|remain|stay|rise).{0,100}"
        r"(raise|tighten|increase).{0,40}"
        r"(rate|rates|policy)",
        5,
        "inflation_persistence_hike",
    ),

    (
        r"cannot rule out.{0,40}"
        r"(rate hike|rate hikes|raising rates|higher rates)",
        4,
        "cannot_rule_out_hikes",
    ),

    (
        r"(prepared|ready).{0,40}"
        r"to act.{0,80}"
        r"inflation",
        4,
        "prepared_to_act_on_inflation",
    ),
]


# ============================================================
# CONDITIONAL DOVISH PATTERNS
# ============================================================

CONDITIONAL_DOVISH_PATTERNS = [

    (
        r"if.{0,100}"
        r"(employment|labor|labour|growth).{0,70}"
        r"(weaken|deteriorat|soften|slow).{0,100}"
        r"(cut|lower|reduce|ease).{0,40}"
        r"(rate|rates|policy)",
        -4,
        "conditional_easing",
    ),

    (
        r"if.{0,100}"
        r"inflation.{0,70}"
        r"(decline|ease|improve|progress).{0,100}"
        r"(cut|lower|reduce).{0,40}"
        r"(rate|rates|policy)",
        -3,
        "inflation_progress_easing",
    ),
]


# ============================================================
# DIRECT STANCE
# ============================================================

DIRECT_STANCE = [
    "i believe",
    "i think",
    "in my view",
    "i support",
    "i supported",
    "i would support",
    "i favor",
    "i favour",
    "i expect",
    "i see",
    "i am prepared",
    "i'm prepared",
    "i am ready",
    "we should",
    "we need to",
    "policy should",
    "it is appropriate",
    "would be appropriate",
]


# ============================================================
# REFERENCE / HISTORICAL CONTEXT
#
# 과거 사례, 남의 견해 등을
# 현재 stance로 과하게 해석하지 않도록 감점.
# ============================================================

REFERENCE_CONTEXT = [
    "some have argued",
    "some observers",
    "some view",
    "markets expect",
    "markets were pricing",
    "market participants expect",
    "respondents expect",
    "staff projected",
    "staff forecast",
    "historically",
    "in the past",
    "in 2022",
    "in 2023",
    "in 2024",
    "in 2025",
    "last year",
    "previously",
]


# ============================================================
# SENTENCE SPLIT
# ============================================================

def _split_sentences(
    text
):

    text = re.sub(
        r"\s+",
        " ",
        text or ""
    ).strip()

    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+(?=[A-Z“\"'])",
        text
    )

    return [
        sentence.strip()
        for sentence in parts
        if len(
            sentence.strip()
        ) >= 20
    ]


# ============================================================
# POLICY RATE CONTEXT
# ============================================================

def _has_policy_rate_context(
    sentence
):

    s = sentence.lower()

    # 명백한 비정책 rate 문맥이면 제외
    if any(
        term in s
        for term in NON_POLICY_RATE_TERMS
    ):

        # 단, 동시에 강한 monetary policy 표현이 있으면 인정
        strong_policy = any(
            term in s
            for term in [
                "federal funds",
                "funds rate",
                "policy rate",
                "monetary policy",
                "fomc",
                "rate cut",
                "rate cuts",
                "rate hike",
                "rate hikes",
            ]
        )

        if not strong_policy:
            return False

    return any(
        term in s
        for term in POLICY_CONTEXT_TERMS
    )


# ============================================================
# RATE PHRASE FILTER
# ============================================================

def _rate_phrase_allowed(
    phrase,
    sentence
):

    phrase_lower = (
        phrase.lower()
    )

    rate_related = any(
        token in phrase_lower
        for token in [
            "rate",
            "rates",
            "interest",
            "policy restraint",
        ]
    )

    if not rate_related:
        return True

    return _has_policy_rate_context(
        sentence
    )


# ============================================================
# DISINFLATION CONTEXT
#
# disinflation이라는 단어 자체는 dovish로 보지 않는다.
# ============================================================

def _disinflation_adjustment(
    sentence
):

    s = sentence.lower()

    # 조건부 긴축
    if (
        "disinflation" in s
        and
        any(
            x in s
            for x in [
                "if we do not",
                "if i do not",
                "does not",
                "doesn't",
                "fails to",
                "do not see",
                "not see signs",
            ]
        )
        and
        any(
            x in s
            for x in [
                "prepared to act",
                "prepared to raise",
                "raise rates",
                "tighten",
                "further tightening",
            ]
        )
    ):

        return {
            "hawk": 4,
            "dove": 0,
            "signal":
                "disinflation_failure_tightening",
        }

    # 명확하게 disinflation 진행 중이라는 표현일 때만
    # 약한 dovish
    if (
        "disinflation" in s
        and
        any(
            x in s
            for x in [
                "continuing",
                "continued",
                "resume",
                "resumed",
                "progress",
                "ongoing",
                "sustained",
            ]
        )
        and
        not any(
            x in s
            for x in [
                "not",
                "stall",
                "stalled",
                "fail",
            ]
        )
    ):

        return {
            "hawk": 0,
            "dove": -1,
            "signal":
                "disinflation_progress",
        }

    return {
        "hawk": 0,
        "dove": 0,
        "signal": None,
    }


# ============================================================
# CONTEXT MULTIPLIER
# ============================================================

def _context_multiplier(
    sentence
):

    s = sentence.lower()

    if any(
        x in s
        for x in DIRECT_STANCE
    ):
        return 1.35

    if any(
        x in s
        for x in REFERENCE_CONTEXT
    ):
        return 0.50

    return 1.0


# ============================================================
# SCORE ONE SENTENCE
# ============================================================

def _score_sentence(
    sentence
):

    text = (
        sentence.lower()
    )

    hawk_signals = {}
    dove_signals = {}

    # ========================================================
    # Conditional hawkish
    # ========================================================

    for (
        pattern,
        weight,
        name,
    ) in CONDITIONAL_HAWKISH_PATTERNS:

        if re.search(
            pattern,
            text,
            flags=re.I,
        ):

            hawk_signals[
                name
            ] = weight

    # ========================================================
    # Conditional dovish
    # ========================================================

    for (
        pattern,
        weight,
        name,
    ) in CONDITIONAL_DOVISH_PATTERNS:

        if re.search(
            pattern,
            text,
            flags=re.I,
        ):

            dove_signals[
                name
            ] = weight

    # ========================================================
    # HAWK PHRASES
    # ========================================================

    for (
        phrase,
        weight,
    ) in HAWKISH_PHRASES.items():

        if phrase not in text:
            continue

        if not _rate_phrase_allowed(
            phrase,
            sentence,
        ):
            continue

        hawk_signals[
            phrase
        ] = weight

    # ========================================================
    # DOVE PHRASES
    # ========================================================

    for (
        phrase,
        weight,
    ) in DOVISH_PHRASES.items():

        if phrase not in text:
            continue

        if not _rate_phrase_allowed(
            phrase,
            sentence,
        ):
            continue

        dove_signals[
            phrase
        ] = weight

    # ========================================================
    # HAWK REGEX
    # ========================================================

    for (
        pattern,
        weight,
        name,
    ) in HAWKISH_PATTERNS:

        if not re.search(
            pattern,
            text,
            flags=re.I,
        ):
            continue

        # rate 관련 regex면 policy context 필요
        if any(
            token in pattern
            for token in [
                "rate",
                "rates",
            ]
        ):

            if not _has_policy_rate_context(
                sentence
            ):
                continue

        hawk_signals.setdefault(
            name,
            weight,
        )

    # ========================================================
    # DOVE REGEX
    # ========================================================

    for (
        pattern,
        weight,
        name,
    ) in DOVISH_PATTERNS:

        if not re.search(
            pattern,
            text,
            flags=re.I,
        ):
            continue

        if any(
            token in pattern
            for token in [
                "rate",
                "rates",
            ]
        ):

            if not _has_policy_rate_context(
                sentence
            ):
                continue

        dove_signals.setdefault(
            name,
            weight,
        )

    # ========================================================
    # DISINFLATION SPECIAL CASE
    # ========================================================

    disinflation = (
        _disinflation_adjustment(
            sentence
        )
    )

    if (
        disinflation[
            "hawk"
        ]
        > 0
    ):

        hawk_signals[
            disinflation[
                "signal"
            ]
        ] = (
            disinflation[
                "hawk"
            ]
        )

    if (
        disinflation[
            "dove"
        ]
        < 0
    ):

        dove_signals[
            disinflation[
                "signal"
            ]
        ] = (
            disinflation[
                "dove"
            ]
        )

    # ========================================================
    # NEGATION / "WITHOUT HAVING TO ..."
    #
    # 예:
    # "without having to lower rates"
    # → dovish가 아님.
    #
    # "without having to raise rates"
    # → hawkish가 아님.
    # ========================================================

    if re.search(
        r"without having to.{0,20}"
        r"(lower|cut|reduce).{0,15}rates?",
        text,
    ):

        dove_signals = {
            key: value
            for key, value
            in dove_signals.items()
            if (
                "rate"
                not in key
                and
                "easing"
                not in key
            )
        }

    if re.search(
        r"without having to.{0,20}"
        r"(raise|increase).{0,15}rates?",
        text,
    ):

        hawk_signals = {
            key: value
            for key, value
            in hawk_signals.items()
            if (
                "rate"
                not in key
                and
                "prepared_to_raise"
                not in key
            )
        }

    # ========================================================
    # SCORE
    # ========================================================

    hawk_score = sum(
        hawk_signals.values()
    )

    dove_score = sum(
        dove_signals.values()
    )

    multiplier = (
        _context_multiplier(
            sentence
        )
    )

    hawk_score = round(
        hawk_score
        * multiplier
    )

    dove_score = round(
        dove_score
        * multiplier
    )

    # ========================================================
    # SENTENCE CAP
    # ========================================================

    hawk_score = min(
        hawk_score,
        MAX_SENTENCE_SCORE,
    )

    dove_score = max(
        dove_score,
        -MAX_SENTENCE_SCORE,
    )

    return {

        "sentence":
            sentence,

        "hawk_score":
            hawk_score,

        "dove_score":
            dove_score,

        "net_score":
            (
                hawk_score
                + dove_score
            ),

        "hawk_signals":
            list(
                hawk_signals.keys()
            ),

        "dove_signals":
            list(
                dove_signals.keys()
            ),
    }


# ============================================================
# LABEL
# ============================================================

def _label_from_score(
    score
):

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
# MAIN
# ============================================================

def score_hawk_dove(
    article
):

    title = str(
        article.get(
            "title"
        )
        or ""
    )

    text = str(
        article.get(
            "text"
        )
        or ""
    )

    sentences = []

    # title도 평가
    if title:

        sentences.append(
            title
        )

    sentences.extend(
        _split_sentences(
            text
        )
    )

    evidence = []

    total_hawk = 0
    total_dove = 0

    # ========================================================
    # SENTENCE LOOP
    # ========================================================

    for sentence in sentences:

        result = (
            _score_sentence(
                sentence
            )
        )

        if (
            result[
                "hawk_score"
            ]
            == 0
            and
            result[
                "dove_score"
            ]
            == 0
        ):

            continue

        total_hawk += (
            result[
                "hawk_score"
            ]
        )

        total_dove += (
            result[
                "dove_score"
            ]
        )

        evidence.append(
            result
        )

    # ========================================================
    # ARTICLE SCORE
    # ========================================================

    raw_score = (
        total_hawk
        + total_dove
    )

    score = max(
        -MAX_ARTICLE_SCORE,
        min(
            raw_score,
            MAX_ARTICLE_SCORE,
        )
    )

    label = (
        _label_from_score(
            score
        )
    )

    # ========================================================
    # SORT EVIDENCE
    # ========================================================

    evidence.sort(
        key=lambda x: abs(
            x[
                "net_score"
            ]
        ),
        reverse=True,
    )

    top_evidence = (
        evidence[
            :8
        ]
    )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    text_length = len(
        text.strip()
    )

    if (
        text_length
        < 100
    ):

        confidence = (
            "LOW"
        )

    elif (
        len(
            evidence
        )
        >= 4
    ):

        confidence = (
            "HIGH"
        )

    elif (
        len(
            evidence
        )
        >= 1
    ):

        confidence = (
            "MEDIUM"
        )

    else:

        confidence = (
            "LOW"
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "hawk_dove_score":
            score,

        "hawk_dove_raw_score":
            raw_score,

        "hawk_dove_label":
            label,

        "hawk_dove_confidence":
            confidence,

        "hawkish_score":
            total_hawk,

        "dovish_score":
            total_dove,

        "hawk_dove_match_count":
            len(
                evidence
            ),

        "hawk_dove_evidence":
            top_evidence,

        "hawk_evidence_sentences": [
            x[
                "sentence"
            ]
            for x
            in top_evidence
            if (
                x[
                    "net_score"
                ]
                > 0
            )
        ],

        "dove_evidence_sentences": [
            x[
                "sentence"
            ]
            for x
            in top_evidence
            if (
                x[
                    "net_score"
                ]
                < 0
            )
        ],
    }