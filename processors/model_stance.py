# processors/model_stance.py

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ============================================================
# CONFIG
# ============================================================

MAX_MODEL_EVIDENCE = 5


# ============================================================
# SCORE -> MODEL STANCE
# ============================================================

def score_to_model_stance(
    score: Optional[float],
) -> str:
    """
    Model Stance는 일반 개별 발언 label보다 조금 보수적으로 판단.

    >= +5 : HAWKISH
    >= +2 : NEUTRAL_HAWKISH
    -2 ~ +2 : NEUTRAL
    <= -2 : NEUTRAL_DOVISH
    <= -5 : DOVISH
    """

    if score is None:
        return "INSUFFICIENT"

    if score >= 5:
        return "HAWKISH"

    if score >= 2:
        return "NEUTRAL_HAWKISH"

    if score <= -5:
        return "DOVISH"

    if score <= -2:
        return "NEUTRAL_DOVISH"

    return "NEUTRAL"


# ============================================================
# HELPERS
# ============================================================

def _safe_float(
    value: Any,
) -> Optional[float]:

    if value is None:
        return None

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def _norm(
    value: Any,
) -> str:

    return str(
        value or ""
    ).strip().upper()


def _get_event_date(
    item: Dict[str, Any],
) -> str:
    """
    실제 발언일 우선.
    """

    return str(
        item.get("actual_speech_date")
        or item.get("speech_date")
        or item.get("event_date")
        or item.get("published_at")
        or item.get("date")
        or ""
    )


def _combined_text(
    item: Dict[str, Any],
) -> str:

    title = str(
        item.get("title")
        or ""
    )

    text = str(
        item.get("text")
        or item.get("body")
        or item.get("content")
        or ""
    )

    return (
        title
        + " "
        + text
    ).lower()


# ============================================================
# SOURCE DETECTION
# ============================================================

def _get_source_coverage(
    item: Dict[str, Any],
) -> str:

    return _norm(
        item.get("source_coverage")
        or item.get("source")
        or item.get("source_type")
    )


def _is_official(
    item: Dict[str, Any],
) -> bool:

    source = _get_source_coverage(
        item
    )

    return (
        source == "OFFICIAL"
        or source == "BOTH"
        or "FEDERAL RESERVE" in source
        or "FED OFFICIAL" in source
    )


def _is_infomax(
    item: Dict[str, Any],
) -> bool:

    source = _get_source_coverage(
        item
    )

    return (
        source == "INFOMAX"
        or source == "BOTH"
        or "INFOMAX" in source
        or "연합인포맥스" in source
    )


# ============================================================
# POLICY CONTEXT
# ============================================================

POLICY_KEYWORDS = [

    # --------------------------------------------------------
    # Interest rates
    # --------------------------------------------------------

    "interest rate",
    "interest rates",
    "rate cut",
    "rate cuts",
    "rate hike",
    "rate hikes",
    "policy rate",
    "federal funds",
    "fed funds",

    "금리",
    "금리인하",
    "금리 인하",
    "금리인상",
    "금리 인상",
    "기준금리",

    # --------------------------------------------------------
    # Monetary policy
    # --------------------------------------------------------

    "monetary policy",
    "policy stance",
    "restrictive",
    "restriction",
    "tightening",
    "tighten",
    "easing",
    "ease",

    "통화정책",
    "정책기조",
    "정책 기조",
    "긴축",
    "긴축적",
    "완화",
    "완화적",
    "제약적",

    # --------------------------------------------------------
    # Inflation
    # --------------------------------------------------------

    "inflation",
    "price stability",
    "price pressures",
    "inflation expectations",
    "2 percent",
    "2% target",

    "인플레이션",
    "물가",
    "물가안정",
    "물가 안정",
    "물가압력",
    "물가 압력",
    "기대인플레이션",
    "기대 인플레이션",

    # --------------------------------------------------------
    # Labor market
    # --------------------------------------------------------

    "labor market",
    "labour market",
    "employment",
    "unemployment",
    "job market",

    "노동시장",
    "노동 시장",
    "고용",
    "실업",

    # --------------------------------------------------------
    # FOMC
    # --------------------------------------------------------

    "fomc",
    "federal open market committee",
    "open market committee",

    "연방공개시장위원회",

    # --------------------------------------------------------
    # Balance sheet
    # --------------------------------------------------------

    "balance sheet",
    "quantitative tightening",
    "quantitative easing",
    "qt",
    "qe",

    "대차대조표",
    "양적긴축",
    "양적완화",

    # --------------------------------------------------------
    # Neutral rate
    # --------------------------------------------------------

    "neutral rate",
    "neutral interest rate",
    "r-star",
    "r star",

    "중립금리",
    "중립 금리",
]


def _has_policy_context(
    item: Dict[str, Any],
) -> bool:

    combined = _combined_text(
        item
    )

    topics = (
        item.get("topics")
        or []
    )

    if isinstance(
        topics,
        list,
    ):

        combined += " " + " ".join(
            str(x).lower()
            for x in topics
        )

    else:

        combined += " " + str(
            topics
        ).lower()

    return any(
        keyword in combined
        for keyword in POLICY_KEYWORDS
    )


# ============================================================
# DIRECT SPEECH DETECTION
# ============================================================

DIRECT_SPEECH_PATTERNS = [

    # --------------------------------------------------------
    # Korean direct speech
    # --------------------------------------------------------

    "말했다",
    "밝혔다",
    "강조했다",
    "언급했다",
    "설명했다",
    "평가했다",
    "진단했다",
    "경계했다",
    "지적했다",
    "주장했다",
    "전망했다",
    "시사했다",
    "덧붙였다",
    "전했다",
    "견해를 밝혔다",
    "입장을 밝혔다",
    "생각한다",
    "본다",
    "판단한다",

    # --------------------------------------------------------
    # Speech / prepared remarks
    # --------------------------------------------------------

    "연설에서",
    "준비한 연설",
    "준비된 연설",
    "경제 포럼에서",
    "경제포럼에서",
    "인터뷰에서",
    "기자들에게",
    "기자회견에서",
    "토론에서",
    "패널에서",

    # --------------------------------------------------------
    # English
    # --------------------------------------------------------

    " said ",
    " says ",
    " stated ",
    " noted ",
    " told ",
    " remarked ",
    " argued ",
    " emphasized ",
    " stressed ",
    " warned ",
    " believes ",
    " thinks ",
    " speaking at ",
    " in a speech ",
    " in prepared remarks ",
    " in an interview ",
]


def _has_direct_speech_signal(
    item: Dict[str, Any],
) -> bool:
    """
    기사 안에 실제 위원 발언임을 나타내는 패턴이 있는지 확인.
    """

    combined = (
        " "
        + _combined_text(
            item
        )
        + " "
    )

    return any(
        pattern in combined
        for pattern in DIRECT_SPEECH_PATTERNS
    )


# ============================================================
# MEMBER PRESENCE
# ============================================================

def _member_is_present(
    item: Dict[str, Any],
) -> bool:
    """
    Infomax 기사가 해당 위원 본인의 기사인지 추가 확인.

    member_name_en / member_name_ko가 기사에 등장하거나,
    upstream member matcher가 이미 member를 확정했다면 허용.
    """

    member_en = str(
        item.get("member_name_en")
        or ""
    ).strip().lower()

    member_ko = str(
        item.get("member_name_ko")
        or ""
    ).strip().lower()

    combined = _combined_text(
        item
    )

    if member_en and member_en in combined:
        return True

    if member_ko and member_ko in combined:
        return True

    # 이미 member matcher를 통과해 정확한 member_name_en이
    # 존재하는 경우에는 보조적으로 인정.
    if member_en:
        return True

    return False


# ============================================================
# INFOMAX DIRECT POLICY SPEECH
# ============================================================

def is_verified_infomax_policy_speech(
    item: Dict[str, Any],
) -> bool:
    """
    Infomax 기사 중 Model Evidence로 승격할 수 있는 기사.

    조건:
        1. Infomax
        2. 위원 매칭
        3. 정책 관련
        4. 직접 발언 signal
        5. Hawk/Dove score 존재

    relevance가 MEDIUM이어도 위 조건을 충족하면 허용.
    """

    if not _is_infomax(
        item
    ):
        return False

    if not _member_is_present(
        item
    ):
        return False

    if not _has_policy_context(
        item
    ):
        return False

    if not _has_direct_speech_signal(
        item
    ):
        return False

    score = _safe_float(
        item.get(
            "hawk_dove_score"
        )
    )

    if score is None:
        return False

    return True


# ============================================================
# MODEL EVIDENCE FILTER
# ============================================================

def is_high_confidence_policy_event(
    item: Dict[str, Any],
) -> bool:
    """
    Model Stance Evidence 기준.

    A. Official
       -> HIGH relevance + 정책관련 + score

    B. Infomax
       -> 위원 본인의 검증된 직접 정책발언이면
          HIGH가 아니어도 허용.

    BOTH는 Official 또는 Infomax 조건 중 하나를
    충족하면 사용 가능.
    """

    if not isinstance(
        item,
        dict,
    ):
        return False

    score = _safe_float(
        item.get(
            "hawk_dove_score"
        )
    )

    if score is None:
        return False

    if not _has_policy_context(
        item
    ):
        return False

    relevance = _norm(
        item.get("fomc_relevance")
        or item.get("relevance")
        or item.get("relevance_label")
        or item.get("importance")
    )

    # ========================================================
    # A. OFFICIAL
    # ========================================================

    if _is_official(
        item
    ):

        if relevance == "HIGH":
            return True

    # ========================================================
    # B. INFOMAX VERIFIED DIRECT SPEECH
    # ========================================================

    if is_verified_infomax_policy_speech(
        item
    ):
        return True

    return False


# ============================================================
# EVIDENCE SELECTION
# ============================================================

def select_model_evidence(
    items: List[Dict[str, Any]],
    max_items: int = MAX_MODEL_EVIDENCE,
) -> List[Dict[str, Any]]:
    """
    Model Evidence:
    - 검증된 event만
    - 최신 실제 발언일 순
    - 최대 5개
    """

    if not items:
        return []

    eligible = [
        item
        for item in items
        if is_high_confidence_policy_event(
            item
        )
    ]

    eligible.sort(
        key=_get_event_date,
        reverse=True,
    )

    return eligible[
        :max_items
    ]


# ============================================================
# WEIGHTS
# ============================================================

def _evidence_weight(
    rank: int,
) -> float:
    """
    최근 발언에 약간 더 높은 가중치.

    지나치게 최근 발언 하나가 전체 성향을
    지배하지 않도록 완만한 decay 사용.
    """

    weights = [
        1.00,
        0.90,
        0.80,
        0.70,
        0.60,
    ]

    if rank < len(
        weights
    ):
        return weights[
            rank
        ]

    return 0.50


# ============================================================
# MODEL SCORE
# ============================================================

def calculate_model_score(
    evidence: List[Dict[str, Any]],
) -> Optional[float]:

    if not evidence:
        return None

    weighted_sum = 0.0

    total_weight = 0.0

    for rank, item in enumerate(
        evidence
    ):

        score = _safe_float(
            item.get(
                "hawk_dove_score"
            )
        )

        if score is None:
            continue

        weight = (
            _evidence_weight(
                rank
            )
        )

        weighted_sum += (
            score
            *
            weight
        )

        total_weight += (
            weight
        )

    if total_weight == 0:
        return None

    return round(
        weighted_sum
        /
        total_weight,
        2,
    )


# ============================================================
# MODEL CONFIDENCE
# ============================================================

def calculate_model_confidence(
    evidence: List[Dict[str, Any]],
) -> str:
    """
    Model Evidence 자체는 이미 품질 검증을 통과했으므로
    근거 event 개수로 confidence 결정.

    0 -> INSUFFICIENT
    1 -> LOW
    2 -> MEDIUM
    >=3 -> HIGH
    """

    count = len(
        evidence
    )

    if count == 0:
        return "INSUFFICIENT"

    if count == 1:
        return "LOW"

    if count == 2:
        return "MEDIUM"

    return "HIGH"


# ============================================================
# EVIDENCE SUMMARY
# ============================================================

def _build_evidence_summary(
    evidence: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    디버깅 및 향후 App 상세보기용.

    원문 전체를 반복 저장하지 않고
    필요한 핵심 필드만 반환.
    """

    output = []

    for item in evidence:

        output.append({

            "event_id":
                item.get(
                    "event_id"
                ),

            "date":
                _get_event_date(
                    item
                ),

            "title":
                item.get(
                    "title"
                ),

            "source_coverage":
                item.get(
                    "source_coverage"
                ),

            "fomc_relevance":
                item.get(
                    "fomc_relevance"
                ),

            "hawk_dove_score":
                item.get(
                    "hawk_dove_score"
                ),

            "hawk_dove_label":
                item.get(
                    "hawk_dove_label"
                ),
        })

    return output


# ============================================================
# MAIN
# ============================================================

def calculate_model_stance(
    items: List[Dict[str, Any]],
    max_items: int = MAX_MODEL_EVIDENCE,
) -> Dict[str, Any]:
    """
    위원 1명의 Model Stance.

    MODEL STANCE
        =
        Official HIGH 직접 정책발언
        +
        검증된 Infomax 직접 정책발언

    일반 뉴스/시장전망/제3자 평가는 사용하지 않는다.
    """

    evidence = (
        select_model_evidence(
            items=items,
            max_items=max_items,
        )
    )

    model_score = (
        calculate_model_score(
            evidence
        )
    )

    model_stance = (
        score_to_model_stance(
            model_score
        )
    )

    model_confidence = (
        calculate_model_confidence(
            evidence
        )
    )

    return {

        "model_stance":
            model_stance,

        "model_score":
            model_score,

        "model_confidence":
            model_confidence,

        "model_evidence_count":
            len(
                evidence
            ),

        "model_evidence":
            evidence,

        "model_evidence_summary":
            _build_evidence_summary(
                evidence
            ),
    }