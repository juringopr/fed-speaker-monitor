# processors/hawk_dove.py

import re


# ============================================================
# CONFIG
# ============================================================

MAX_SENTENCE_SCORE = 6
MAX_ARTICLE_SCORE = 20


# ============================================================
# POLICY CONTEXT
# ============================================================

POLICY_CONTEXT_TERMS = [

    # English
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

    # Korean
    "연준",
    "연방준비제도",
    "연방공개시장위원회",
    "기준금리",
    "정책금리",
    "통화정책",
    "정책 기조",
    "정책기조",
    "금리 인하",
    "금리인하",
    "금리 인상",
    "금리인상",
    "금리 동결",
    "금리동결",
    "금리를 인하",
    "금리를 인상",
    "금리를 낮",
    "금리를 올",
    "긴축",
    "완화",
    "제약적",
    "중립금리",
]


# ============================================================
# NON-POLICY RATE CONTEXT
# ============================================================

NON_POLICY_RATE_TERMS = [

    # English
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

    # Korean
    "실업률",
    "참가율",
    "경제활동참가율",
    "성장률",
    "증가율",
    "감소율",
    "모기지 금리",
    "주택담보대출 금리",
    "대출금리",
    "연체율",
    "부도율",
]


# ============================================================
# ENGLISH HAWKISH PHRASES
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
# ENGLISH DOVISH PHRASES
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
# KOREAN HAWKISH PHRASES
# ============================================================

KOREAN_HAWKISH_PHRASES = {

    # --------------------------------------------------------
    # Direct rate hike
    # --------------------------------------------------------

    "금리 인상이 필요": 5,
    "금리인상이 필요": 5,

    "금리를 인상해야": 5,
    "금리를 올려야": 5,

    "기준금리를 인상": 5,
    "정책금리를 인상": 5,

    "추가 금리 인상": 5,
    "추가적인 금리 인상": 5,
    "추가 인상": 4,

    "더 높은 금리": 4,
    "다소 더 높은 금리": 4,

    # --------------------------------------------------------
    # Tightening
    # --------------------------------------------------------

    "더욱 긴축적인 정책": 6,
    "더 긴축적인 정책": 6,

    "긴축적인 정책이 필요": 6,
    "긴축적 정책이 필요": 6,

    "긴축적인 통화정책": 5,
    "긴축적 통화정책": 5,

    "추가 긴축": 5,
    "추가적인 긴축": 5,

    "제약적이지 않": 4,
    "충분히 제약적이지 않": 5,

    "더 제약적인": 4,
    "더욱 제약적인": 4,

    # --------------------------------------------------------
    # No cut / hold
    # --------------------------------------------------------

    "금리 인하할 이유가 거의 없어": 5,
    "금리인하할 이유가 거의 없어": 5,

    "금리 인하할 필요가 없어": 5,
    "금리인하할 필요가 없어": 5,

    "추가 완화할 이유가 거의 없어": 5,

    "금리 인하 기회 아냐": 5,
    "금리인하 기회 아냐": 5,

    "금리 인하를 서두를": 3,
    "금리인하를 서두를": 3,

    "금리 동결을 지지": 2,
    "금리동결을 지지": 2,

    "동결을 지지": 2,

    "현 정책기조 적절": 2,
    "현 정책 기조 적절": 2,

    "현 금리 수준 적절": 2,

    # --------------------------------------------------------
    # Inflation
    # --------------------------------------------------------

    "인플레이션이 너무 높": 4,
    "인플레가 너무 높": 4,

    "인플레이션은 너무 높": 4,
    "인플레는 너무 높": 4,

    "인플레이션이 지나치게 높": 4,
    "인플레가 지나치게 높": 4,

    "인플레가 너무 뜨겁": 5,
    "인플레이션이 너무 뜨겁": 5,

    "인플레이션 압력": 3,
    "인플레 압력": 3,

    "인플레이션 상방 위험": 4,
    "인플레 상방 위험": 4,

    "인플레이션 위험": 2,
    "인플레 위험": 2,

    "인플레이션 고착": 5,
    "인플레 고착": 5,

    "3%에 더 가깝게 고착": 6,
    "3% 수준에 더 가깝게 고착": 6,

    "인플레이션 기대": 2,
    "기대 인플레이션": 2,

    "인플레이션 측면에서 할 일이": 4,
    "인플레 측면에서 할 일이": 4,

    "물가안정을 중시": 3,
    "물가 안정을 중시": 3,

    "물가 안정 목표": 2,

    "경계를 늦출 때 아냐": 4,
    "경계를 늦출 때 아니다": 4,

    # --------------------------------------------------------
    # Strong economy/labor
    # --------------------------------------------------------

    "경제가 탄탄": 2,
    "경제는 탄탄": 2,

    "경제가 견조": 2,
    "경제는 견조": 2,

    "고용 꽤 좋": 2,

    "노동시장이 견조": 2,
    "노동시장은 견조": 2,
}


# ============================================================
# KOREAN DOVISH PHRASES
# ============================================================

KOREAN_DOVISH_PHRASES = {

    # --------------------------------------------------------
    # Cuts
    # --------------------------------------------------------

    "금리 인하가 필요": -5,
    "금리인하가 필요": -5,

    "금리를 인하해야": -5,
    "금리를 내려야": -5,

    "금리 인하를 지지": -5,
    "금리인하를 지지": -5,

    "추가 금리 인하": -4,
    "추가적인 금리 인하": -4,

    "금리 인하 가능": -3,
    "금리인하 가능": -3,

    "금리 인하 여력": -4,
    "금리인하 여력": -4,

    "몇 차례 금리 인하": -4,
    "몇차례 금리 인하": -4,

    # --------------------------------------------------------
    # Easing
    # --------------------------------------------------------

    "추가 완화가 필요": -4,
    "완화가 필요": -4,

    "완화적 정책": -3,
    "완화적인 정책": -3,

    "제약 수준을 낮": -4,
    "정책 제약을 줄": -4,

    # --------------------------------------------------------
    # Inflation improving
    # --------------------------------------------------------

    "인플레이션이 둔화": -2,
    "인플레가 둔화": -2,

    "인플레이션 둔화": -2,
    "인플레 둔화": -2,

    "물가 상승률이 둔화": -2,
    "물가 상승률 둔화": -2,

    "인플레이션이 하락": -2,
    "인플레가 하락": -2,

    "인플레이션 정점을 지났": -3,
    "인플레 정점을 지났": -3,

    "2% 목표로 복귀": -2,
    "2%로 복귀": -2,

    "디스인플레이션": -1,

    # --------------------------------------------------------
    # Employment / growth weakness
    # --------------------------------------------------------

    "노동시장 약화": -3,
    "노동시장이 약화": -3,

    "고용 하방 위험": -4,
    "고용의 하방 위험": -4,

    "노동시장 하방 위험": -4,

    "고용 악화": -3,

    "실업률 상승": -2,
    "실업률이 상승": -2,

    "경기 둔화": -2,
    "성장 둔화": -2,

    "하방 위험이 커": -3,

    # --------------------------------------------------------
    # No hike / look-through
    # --------------------------------------------------------

    "금리 인상에 반대": -5,
    "금리인상에 반대": -5,

    "금리 인상을 경계": -4,
    "금리인상을 경계": -4,

    "금리를 인상할 필요 없어": -5,
    "금리 인상할 필요 없어": -5,

    "일시적인 인플레이션": -2,
    "일시적 인플레이션": -2,

    "일시적인 물가 상승": -2,

    "일시적 충격으로 간주": -2,
    "일시적인 충격으로 간주": -2,
}


# ============================================================
# REGEX - ENGLISH HAWKISH
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
# REGEX - ENGLISH DOVISH
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
# REGEX - KOREAN HAWKISH
# ============================================================

KOREAN_HAWKISH_PATTERNS = [

    # 추가 금리 인하는 물가를 더 오래 높게 유지
    (
        r"(추가적인?\s*)?"
        r"금리\s*인하.{0,80}"
        r"(인플레|인플레이션|물가).{0,80}"
        r"(지속|높|위험)",
        5,
        "ko_rate_cut_inflation_risk",
    ),

    # 인플레를 잡기 위해 긴축 필요
    (
        r"(인플레|인플레이션|물가).{0,100}"
        r"(잡|낮추|억제).{0,100}"
        r"(긴축|제약).{0,50}"
        r"(필요|요구)",
        6,
        "ko_tightening_required",
    ),

    # 현 정책 충분히 제약적이지 않음
    (
        r"(현재|현).{0,80}"
        r"(정책|통화정책).{0,80}"
        r"(충분히\s*)?"
        r"제약적이지\s*않",
        5,
        "ko_policy_not_restrictive_enough",
    ),

    # 인플레 3% 고착
    (
        r"(인플레|인플레이션).{0,100}"
        r"3\s*%.{0,100}"
        r"(고착|머물|유지)",
        6,
        "ko_inflation_three_percent_risk",
    ),

    # 인플레 목표를 너무 오랫동안 상회
    (
        r"(인플레|인플레이션).{0,80}"
        r"(목표|2\s*%).{0,100}"
        r"(상회|웃돌).{0,60}"
        r"(오랫동안|지속)",
        4,
        "ko_inflation_above_target_persistent",
    ),

    # 금리 인상 준비/필요
    (
        r"(금리|기준금리).{0,40}"
        r"(인상|올려).{0,60}"
        r"(필요|준비|적절|고려)",
        5,
        "ko_rate_hike",
    ),

    # 물가 안정 우선
    (
        r"(완전고용|고용).{0,100}"
        r"(보다|보다는).{0,60}"
        r"(물가\s*안정|물가안정).{0,60}"
        r"(중시|우선)",
        4,
        "ko_price_stability_priority",
    ),

    # 금리 동결 지지
    (
        r"(금리\s*)?"
        r"동결.{0,50}"
        r"(지지|적절)",
        2,
        "ko_hold_rates",
    ),
]


# ============================================================
# REGEX - KOREAN DOVISH
# ============================================================

KOREAN_DOVISH_PATTERNS = [

    # 금리 인하 적절
    (
        r"(금리|기준금리).{0,40}"
        r"(인하|내려).{0,60}"
        r"(필요|적절|지지|고려)",
        -5,
        "ko_rate_cut",
    ),

    # 고용 약화하면 인하
    (
        r"(고용|노동시장).{0,100}"
        r"(약화|둔화|악화|하방).{0,100}"
        r"(금리\s*)?"
        r"(인하|완화)",
        -4,
        "ko_labor_weakness_easing",
    ),

    # 물가 둔화 -> 인하
    (
        r"(인플레|인플레이션|물가).{0,80}"
        r"(둔화|하락|개선).{0,100}"
        r"(금리\s*)?"
        r"(인하|완화)",
        -4,
        "ko_inflation_progress_easing",
    ),

    # 인상 필요 없음
    (
        r"(금리\s*)?"
        r"인상.{0,50}"
        r"(필요\s*없|불필요|반대)",
        -5,
        "ko_no_hike_needed",
    ),

    # 일시적 물가 충격 무시
    (
        r"(인플레|인플레이션|물가).{0,80}"
        r"(일시적|단기적).{0,100}"
        r"(간주|지켜보|넘어가|대응하지)",
        -3,
        "ko_look_through_inflation",
    ),
]


# ============================================================
# CONDITIONAL HAWKISH - ENGLISH
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
# CONDITIONAL DOVISH - ENGLISH
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

    # English
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

    # Korean — Infomax direct quote / attribution
    "말했다",
    "밝혔다",
    "강조했다",
    "지적했다",
    "평가했다",
    "설명했다",
    "전망했다",
    "경고했다",
    "주장했다",
    "시사했다",
    "언급했다",
    "덧붙였다",

    "필요하다고",
    "적절하다고",
    "생각한다고",
    "본다고",
    "판단한다고",
    "지지한다고",

    "필요하다는",
    "적절하다는",
    "생각한다",
    "본다",
    "판단한다",

    "지지했다",
    "반대했다",
]


# ============================================================
# REFERENCE / HISTORICAL CONTEXT
# ============================================================

REFERENCE_CONTEXT = [

    # English
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

    # Korean
    "시장에서는",
    "시장 참가자들은",
    "전문가들은",
    "이코노미스트들은",
    "월가에서는",
    "투자자들은",
    "시장은 예상",
    "시장이 예상",
    "지난해",
    "작년",
    "과거에는",
    "이전에는",
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

    # English punctuation + Korean article/quote context 모두 대응
    parts = re.split(
        r"(?<=[.!?。])\s+"
        r"|(?<=다\.)\s+"
        r"|(?<=요\.)\s+",
        text
    )

    return [
        sentence.strip()
        for sentence in parts
        if len(
            sentence.strip()
        ) >= 15
    ]


# ============================================================
# POLICY RATE CONTEXT
# ============================================================

def _has_policy_rate_context(
    sentence
):

    s = sentence.lower()

    if any(
        term in s
        for term in NON_POLICY_RATE_TERMS
    ):

        strong_policy = any(
            term in s
            for term in [
                # English
                "federal funds",
                "funds rate",
                "policy rate",
                "monetary policy",
                "fomc",
                "rate cut",
                "rate cuts",
                "rate hike",
                "rate hikes",

                # Korean
                "기준금리",
                "정책금리",
                "통화정책",
                "연준",
                "fomc",
                "금리 인하",
                "금리인하",
                "금리 인상",
                "금리인상",
                "금리 동결",
                "금리동결",
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

            "금리",
            "기준금리",
            "정책금리",
        ]
    )

    if not rate_related:
        return True

    return _has_policy_rate_context(
        sentence
    )


# ============================================================
# DISINFLATION CONTEXT
# ============================================================

def _disinflation_adjustment(
    sentence
):

    s = sentence.lower()

    # English conditional tightening
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

    # English progress
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

    # Korean stalled disinflation
    if (
        "디스인플레이션" in s
        and
        any(
            x in s
            for x in [
                "중단",
                "정체",
                "멈",
                "진전이 없",
                "진전 없",
            ]
        )
    ):

        return {
            "hawk": 3,
            "dove": 0,
            "signal":
                "ko_disinflation_stalled",
        }

    # Korean continued disinflation
    if (
        "디스인플레이션" in s
        and
        any(
            x in s
            for x in [
                "진전",
                "계속",
                "지속",
                "재개",
            ]
        )
        and
        not any(
            x in s
            for x in [
                "없",
                "중단",
                "정체",
                "멈",
            ]
        )
    ):

        return {
            "hawk": 0,
            "dove": -1,
            "signal":
                "ko_disinflation_progress",
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
    # CONDITIONAL ENGLISH HAWKISH
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
    # CONDITIONAL ENGLISH DOVISH
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
    # ENGLISH HAWK PHRASES
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
    # ENGLISH DOVE PHRASES
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
    # KOREAN HAWK PHRASES
    # ========================================================

    for (
        phrase,
        weight,
    ) in KOREAN_HAWKISH_PHRASES.items():

        if phrase not in text:
            continue

        if not _rate_phrase_allowed(
            phrase,
            sentence,
        ):
            continue

        hawk_signals[
            "ko:" + phrase
        ] = weight

    # ========================================================
    # KOREAN DOVE PHRASES
    # ========================================================

    for (
        phrase,
        weight,
    ) in KOREAN_DOVISH_PHRASES.items():

        if phrase not in text:
            continue

        if not _rate_phrase_allowed(
            phrase,
            sentence,
        ):
            continue

        dove_signals[
            "ko:" + phrase
        ] = weight

    # ========================================================
    # ENGLISH HAWK REGEX
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
    # ENGLISH DOVE REGEX
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
    # KOREAN HAWK REGEX
    # ========================================================

    for (
        pattern,
        weight,
        name,
    ) in KOREAN_HAWKISH_PATTERNS:

        if not re.search(
            pattern,
            text,
            flags=re.I,
        ):
            continue

        hawk_signals.setdefault(
            name,
            weight,
        )

    # ========================================================
    # KOREAN DOVE REGEX
    # ========================================================

    for (
        pattern,
        weight,
        name,
    ) in KOREAN_DOVISH_PATTERNS:

        if not re.search(
            pattern,
            text,
            flags=re.I,
        ):
            continue

        dove_signals.setdefault(
            name,
            weight,
        )

    # ========================================================
    # DISINFLATION
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
    # ENGLISH NEGATION
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
    # KOREAN NEGATION
    # ========================================================

    # "금리 인상이 필요하지 않다"
    if re.search(
        r"금리\s*인상.{0,30}"
        r"(필요하지\s*않|필요\s*없|불필요)",
        text,
    ):

        hawk_signals = {
            key: value
            for key, value
            in hawk_signals.items()
            if (
                "금리 인상"
                not in key
                and
                "rate_hike"
                not in key
            )
        }

        dove_signals[
            "ko_rate_hike_not_needed"
        ] = -5

    # "금리 인하가 필요하지 않다"
    if re.search(
        r"금리\s*인하.{0,30}"
        r"(필요하지\s*않|필요\s*없|불필요)",
        text,
    ):

        dove_signals = {
            key: value
            for key, value
            in dove_signals.items()
            if (
                "금리 인하"
                not in key
                and
                "rate_cut"
                not in key
            )
        }

        hawk_signals[
            "ko_rate_cut_not_needed"
        ] = 5

    # "추가 금리 인하는 높은 인플레이션을 더 오래 지속시킬 위험"
    if re.search(
        r"금리\s*인하.{0,100}"
        r"(인플레|인플레이션|물가).{0,100}"
        r"(더\s*오래|지속).{0,80}"
        r"(위험|높)",
        text,
    ):

        # 단순 '금리 인하' dovish hit 제거
        dove_signals = {
            key: value
            for key, value
            in dove_signals.items()
            if (
                "금리 인하"
                not in key
                and
                "rate_cut"
                not in key
            )
        }

        hawk_signals[
            "ko_cut_prolongs_inflation"
        ] = 6

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
                +
                dove_score
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

def score_to_hawk_dove_label(
    score
):
    """
    외부 processor에서도 사용할 수 있는
    public label function.

    processors/__init__.py 호환용.
    """

    try:

        score = float(
            score
        )

    except (
        TypeError,
        ValueError,
    ):

        return "NEUTRAL"

    if score >= 4:
        return "HAWKISH"

    if score >= 1:
        return "NEUTRAL_HAWKISH"

    if score <= -4:
        return "DOVISH"

    if score <= -1:
        return "NEUTRAL_DOVISH"

    return "NEUTRAL"


# 기존 코드 호환
def _label_from_score(
    score
):

    return (
        score_to_hawk_dove_label(
            score
        )
    )


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

    sentences = []

    # ========================================================
    # TITLE
    # ========================================================

    if title:

        sentences.append(
            title
        )

    # ========================================================
    # BODY
    # ========================================================

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
        +
        total_dove
    )

    score = max(
        -MAX_ARTICLE_SCORE,
        min(
            raw_score,
            MAX_ARTICLE_SCORE,
        )
    )

    label = (
        score_to_hawk_dove_label(
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