# processors/final_stance.py

from __future__ import annotations

from typing import Any, Dict, Optional


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value: Any) -> Optional[float]:

    if value is None:
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def _norm(value: Any) -> str:

    return str(
        value or ""
    ).strip().upper()


# ============================================================
# FINAL SCORE -> STANCE
# ============================================================

def score_to_final_stance(
    score: Optional[float],
) -> str:
    """
    Model Stance와 동일한 보수적 threshold 사용.

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
# MODEL WEIGHT
# ============================================================

def get_model_weight(
    model_confidence: str,
) -> float:
    """
    Model이 Anchor.

    HIGH   -> 80%
    MEDIUM -> 70%
    LOW    -> 60%
    """

    confidence = _norm(
        model_confidence
    )

    if confidence == "HIGH":
        return 0.80

    if confidence == "MEDIUM":
        return 0.70

    if confidence == "LOW":
        return 0.60

    return 0.0


# ============================================================
# RECENT CONFIDENCE ADJUSTMENT
# ============================================================

def get_recent_confidence_multiplier(
    recent_confidence: str,
) -> float:
    """
    Recent Signal 신뢰도에 따라
    원래 Recent weight를 축소.

    HIGH   -> 100%
    MEDIUM -> 75%
    LOW    -> 50%
    """

    confidence = _norm(
        recent_confidence
    )

    if confidence == "HIGH":
        return 1.00

    if confidence == "MEDIUM":
        return 0.75

    if confidence == "LOW":
        return 0.50

    return 0.0


# ============================================================
# DIRECTION
# ============================================================

def _direction(score: Optional[float]) -> int:

    if score is None:
        return 0

    if score >= 2:
        return 1

    if score <= -2:
        return -1

    return 0


def signals_conflict(
    model_score: Optional[float],
    recent_score: Optional[float],
) -> bool:
    """
    명확한 매파/비둘기 방향이 서로 반대인지 확인.
    Neutral vs Hawkish는 conflict로 보지 않는다.
    """

    model_direction = _direction(
        model_score
    )

    recent_direction = _direction(
        recent_score
    )

    return (
        model_direction != 0
        and
        recent_direction != 0
        and
        model_direction != recent_direction
    )


# ============================================================
# FINAL CONFIDENCE
# ============================================================

def calculate_final_confidence(
    model_confidence: str,
    recent_confidence: str,
    model_score: Optional[float],
    recent_score: Optional[float],
) -> str:

    model_confidence = _norm(
        model_confidence
    )

    recent_confidence = _norm(
        recent_confidence
    )

    # --------------------------------------------------------
    # Model 없음
    # --------------------------------------------------------

    if model_score is None:

        if recent_score is None:
            return "INSUFFICIENT"

        # Recent만으로는 HIGH 확정 금지
        return "LOW"

    # --------------------------------------------------------
    # Recent 없음
    # --------------------------------------------------------

    if recent_score is None:

        if model_confidence in {
            "HIGH",
            "MEDIUM",
            "LOW",
        }:
            return model_confidence

        return "LOW"

    # --------------------------------------------------------
    # 명확하게 충돌
    # --------------------------------------------------------

    if signals_conflict(
        model_score,
        recent_score,
    ):

        if model_confidence == "HIGH":
            return "MEDIUM"

        return "LOW"

    # --------------------------------------------------------
    # 같은 방향 또는 Recent가 Neutral
    # --------------------------------------------------------

    if model_confidence == "HIGH":

        return "HIGH"

    if model_confidence == "MEDIUM":

        if recent_confidence in {
            "HIGH",
            "MEDIUM",
        }:
            return "MEDIUM"

        return "LOW"

    if model_confidence == "LOW":

        if (
            recent_confidence == "HIGH"
            and
            not signals_conflict(
                model_score,
                recent_score,
            )
        ):
            return "MEDIUM"

        return "LOW"

    return "LOW"


# ============================================================
# FINAL STANCE
# ============================================================

def calculate_final_stance(
    model_result: Dict[str, Any],
    recent_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    FINAL STANCE

    Model Stance = Anchor
    Recent Signal = 보정

    기본:
        Model HIGH   -> 80 / 20
        Model MEDIUM -> 70 / 30
        Model LOW    -> 60 / 40

    Recent Confidence가 낮으면 Recent 영향력 축소.

    Recent가 없으면 Model 그대로 사용.
    """

    model_score = _safe_float(
        model_result.get(
            "model_score"
        )
    )

    recent_score = _safe_float(
        recent_result.get(
            "recent_signal_score"
        )
    )

    model_confidence = _norm(
        model_result.get(
            "model_confidence"
        )
    )

    recent_confidence = _norm(
        recent_result.get(
            "recent_signal_confidence"
        )
    )

    # ========================================================
    # CASE 1
    # 둘 다 없음
    # ========================================================

    if (
        model_score is None
        and
        recent_score is None
    ):

        return {

            "final_stance":
                "INSUFFICIENT",

            "final_score":
                None,

            "final_confidence":
                "INSUFFICIENT",

            "final_model_weight":
                0.0,

            "final_recent_weight":
                0.0,

            "final_signal_conflict":
                False,

            "final_reason":
                "No usable model or recent evidence.",
        }

    # ========================================================
    # CASE 2
    # Model 없음 -> Recent 사용
    # ========================================================

    if model_score is None:

        final_score = round(
            recent_score,
            2,
        )

        return {

            "final_stance":
                score_to_final_stance(
                    final_score
                ),

            "final_score":
                final_score,

            # Recent만으로 판단하므로 LOW
            "final_confidence":
                "LOW",

            "final_model_weight":
                0.0,

            "final_recent_weight":
                1.0,

            "final_signal_conflict":
                False,

            "final_reason":
                "Model evidence insufficient; recent signal used as fallback.",
        }

    # ========================================================
    # CASE 3
    # Recent 없음 -> Model 그대로
    # ========================================================

    if recent_score is None:

        final_score = round(
            model_score,
            2,
        )

        final_confidence = (
            calculate_final_confidence(
                model_confidence=(
                    model_confidence
                ),
                recent_confidence=(
                    recent_confidence
                ),
                model_score=(
                    model_score
                ),
                recent_score=None,
            )
        )

        return {

            "final_stance":
                score_to_final_stance(
                    final_score
                ),

            "final_score":
                final_score,

            "final_confidence":
                final_confidence,

            "final_model_weight":
                1.0,

            "final_recent_weight":
                0.0,

            "final_signal_conflict":
                False,

            "final_reason":
                "No usable recent signal; model stance retained.",
        }

    # ========================================================
    # CASE 4
    # Model + Recent 둘 다 있음
    # ========================================================

    base_model_weight = (
        get_model_weight(
            model_confidence
        )
    )

    if base_model_weight <= 0:

        base_model_weight = 0.60

    base_recent_weight = (
        1.0
        -
        base_model_weight
    )

    recent_multiplier = (
        get_recent_confidence_multiplier(
            recent_confidence
        )
    )

    adjusted_recent_weight = (
        base_recent_weight
        *
        recent_multiplier
    )

    # Recent 영향이 줄어든 만큼 Model에 다시 배분
    adjusted_model_weight = (
        1.0
        -
        adjusted_recent_weight
    )

    final_score = (

        model_score
        *
        adjusted_model_weight

        +

        recent_score
        *
        adjusted_recent_weight
    )

    final_score = round(
        final_score,
        2,
    )

    conflict = (
        signals_conflict(
            model_score,
            recent_score,
        )
    )

    final_confidence = (
        calculate_final_confidence(
            model_confidence=(
                model_confidence
            ),
            recent_confidence=(
                recent_confidence
            ),
            model_score=(
                model_score
            ),
            recent_score=(
                recent_score
            ),
        )
    )

    # ========================================================
    # REASON
    # ========================================================

    if conflict:

        reason = (
            "Model and recent signals conflict; "
            "model retained as anchor and confidence reduced."
        )

    elif (
        _direction(model_score)
        ==
        _direction(recent_score)
        and
        _direction(model_score) != 0
    ):

        reason = (
            "Model and recent signals point in the same direction."
        )

    else:

        reason = (
            "Recent signal used as a limited adjustment to the model anchor."
        )

    return {

        "final_stance":
            score_to_final_stance(
                final_score
            ),

        "final_score":
            final_score,

        "final_confidence":
            final_confidence,

        "final_model_weight":
            round(
                adjusted_model_weight,
                3,
            ),

        "final_recent_weight":
            round(
                adjusted_recent_weight,
                3,
            ),

        "final_signal_conflict":
            conflict,

        "final_reason":
            reason,
    }