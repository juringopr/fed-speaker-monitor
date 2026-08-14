# processors/recent_signal.py

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# ============================================================
# CONFIG
# ============================================================

RECENT_LOOKBACK_DAYS = 90

MAX_AUX_SPEECH_ITEMS = 5
MAX_NEWS_ITEMS = 10


# ============================================================
# SCORE -> LABEL
# ============================================================

def score_to_recent_signal(
    score: Optional[float],
) -> str:

    if score is None:
        return "INSUFFICIENT"

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


def _parse_date(
    value: Any,
):

    if not value:
        return None

    try:

        parsed = datetime.fromisoformat(
            str(value)
            .replace(
                "Z",
                "+00:00",
            )
        )

        return parsed.replace(
            tzinfo=None
        )

    except Exception:

        try:

            return datetime.strptime(
                str(value)[:10],
                "%Y-%m-%d",
            )

        except Exception:

            return None


def _event_date(
    item: Dict[str, Any],
):

    return (
        _parse_date(
            item.get(
                "actual_speech_date"
            )
        )
        or
        _parse_date(
            item.get(
                "speech_date"
            )
        )
        or
        _parse_date(
            item.get(
                "event_date"
            )
        )
        or
        _parse_date(
            item.get(
                "published_at"
            )
        )
    )


def _event_identity(
    item: Dict[str, Any],
) -> str:
    """
    Model evidence와의 중복 제거용.
    event_id가 있으면 최우선.
    """

    event_id = (
        item.get(
            "event_id"
        )
    )

    if event_id:

        return str(
            event_id
        )

    return (
        str(
            item.get(
                "actual_speech_date"
            )
            or
            item.get(
                "published_at"
            )
            or
            ""
        )
        +
        "|"
        +
        str(
            item.get(
                "title"
            )
            or
            ""
        )
    )


# ============================================================
# RECENT WINDOW
# ============================================================

def _inside_recent_window(
    item: Dict[str, Any],
    lookback_days: int,
) -> bool:

    date_value = (
        _event_date(
            item
        )
    )

    if date_value is None:
        return False

    cutoff = (
        datetime.now()
        -
        timedelta(
            days=lookback_days
        )
    )

    return (
        date_value
        >= cutoff
    )


# ============================================================
# AUX SPEECH
# ============================================================

def select_auxiliary_speech(
    events: List[Dict[str, Any]],
    model_evidence: Optional[List[Dict[str, Any]]] = None,
    lookback_days: int = RECENT_LOOKBACK_DAYS,
    max_items: int = MAX_AUX_SPEECH_ITEMS,
) -> List[Dict[str, Any]]:
    """
    Recent Signal에 사용할 보조발언.

    조건:
    - 최근 N일
    - Hawk/Dove score 존재
    - Model Evidence에 이미 사용된 event 제외
    - MEDIUM / LOW 중심
    """

    model_ids = {
        _event_identity(
            item
        )
        for item
        in (
            model_evidence
            or []
        )
    }

    selected = []

    for item in (
        events
        or []
    ):

        if not _inside_recent_window(
            item,
            lookback_days,
        ):
            continue

        if (
            _event_identity(
                item
            )
            in model_ids
        ):
            continue

        score = (
            _safe_float(
                item.get(
                    "hawk_dove_score"
                )
            )
        )

        if score is None:
            continue

        relevance = str(
            item.get(
                "fomc_relevance"
            )
            or
            ""
        ).upper()

        # Model에 쓰지 않은 보조자료 중심
        if relevance not in [
            "MEDIUM",
            "LOW",
        ]:

            continue

        selected.append(
            item
        )

    selected.sort(
        key=lambda item:
            _event_date(
                item
            )
            or
            datetime.min,
        reverse=True,
    )

    return selected[
        :max_items
    ]


# ============================================================
# SPEECH SIGNAL
# ============================================================

def calculate_auxiliary_speech_signal(
    events: List[Dict[str, Any]],
    model_evidence: Optional[List[Dict[str, Any]]] = None,
    lookback_days: int = RECENT_LOOKBACK_DAYS,
) -> Dict[str, Any]:

    evidence = (
        select_auxiliary_speech(
            events=events,
            model_evidence=model_evidence,
            lookback_days=lookback_days,
        )
    )

    scores = []

    for item in evidence:

        score = (
            _safe_float(
                item.get(
                    "hawk_dove_score"
                )
            )
        )

        if score is not None:

            scores.append(
                score
            )

    if not scores:

        return {

            "aux_speech_score":
                None,

            "aux_speech_label":
                "INSUFFICIENT",

            "aux_speech_count":
                0,

            "aux_speech_evidence":
                [],
        }

    score = round(
        sum(
            scores
        )
        /
        len(
            scores
        ),
        2,
    )

    return {

        "aux_speech_score":
            score,

        "aux_speech_label":
            score_to_recent_signal(
                score
            ),

        "aux_speech_count":
            len(
                evidence
            ),

        "aux_speech_evidence":
            evidence,
    }


# ============================================================
# NEWS SIGNAL NORMALIZE
# ============================================================

def normalize_news_signal(
    news_analysis: Dict[str, Any],
) -> Dict[str, Any]:

    score = (
        _safe_float(
            news_analysis.get(
                "news_score"
            )
        )
    )

    label = (
        news_analysis.get(
            "news_label"
        )
        or
        "INSUFFICIENT"
    )

    confidence = (
        news_analysis.get(
            "news_confidence"
        )
        or
        "LOW"
    )

    usable_count = int(
        news_analysis.get(
            "news_usable_count"
        )
        or
        0
    )

    return {

        "news_score":
            score,

        "news_label":
            label,

        "news_confidence":
            confidence,

        "news_usable_count":
            usable_count,

        "news_articles":
            news_analysis.get(
                "news_articles"
            )
            or [],
    }


# ============================================================
# WEIGHTS
# ============================================================

def _news_weight(
    confidence: str,
    usable_count: int,
) -> float:

    confidence = str(
        confidence
        or ""
    ).upper()

    if usable_count <= 0:
        return 0.0

    if confidence == "HIGH":
        return 0.60

    if confidence == "MEDIUM":
        return 0.45

    if confidence == "LOW":
        return 0.25

    return 0.0


def _speech_weight(
    count: int,
) -> float:

    if count <= 0:
        return 0.0

    if count == 1:
        return 0.35

    if count == 2:
        return 0.45

    return 0.55


# ============================================================
# RECENT SIGNAL CONFIDENCE
# ============================================================

def calculate_recent_signal_confidence(
    aux_count: int,
    news_usable_count: int,
    news_confidence: str,
) -> str:

    total_sources = (
        aux_count
        +
        news_usable_count
    )

    if total_sources == 0:
        return "INSUFFICIENT"

    if (
        aux_count >= 2
        and
        news_usable_count >= 2
    ):
        return "HIGH"

    if (
        total_sources >= 3
    ):
        return "MEDIUM"

    if (
        str(
            news_confidence
        ).upper()
        == "HIGH"
        and
        news_usable_count >= 2
    ):
        return "MEDIUM"

    return "LOW"


# ============================================================
# MAIN
# ============================================================

def calculate_recent_signal(
    events: List[Dict[str, Any]],
    news_analysis: Dict[str, Any],
    model_evidence: Optional[List[Dict[str, Any]]] = None,
    lookback_days: int = RECENT_LOOKBACK_DAYS,
) -> Dict[str, Any]:
    """
    Recent Signal
    =
    최근 90일 MEDIUM/LOW 보조발언
    +
    최근 90일 Google News

    Model Evidence는 중복 사용하지 않는다.
    """

    aux = (
        calculate_auxiliary_speech_signal(
            events=events,
            model_evidence=model_evidence,
            lookback_days=lookback_days,
        )
    )

    news = (
        normalize_news_signal(
            news_analysis
        )
    )

    aux_score = (
        aux.get(
            "aux_speech_score"
        )
    )

    news_score = (
        news.get(
            "news_score"
        )
    )

    aux_weight = (
        _speech_weight(
            aux.get(
                "aux_speech_count",
                0,
            )
        )
    )

    news_weight = (
        _news_weight(
            news.get(
                "news_confidence",
                "LOW",
            ),
            news.get(
                "news_usable_count",
                0,
            ),
        )
    )

    weighted_sum = 0.0
    total_weight = 0.0

    if (
        aux_score
        is not None
        and
        aux_weight > 0
    ):

        weighted_sum += (
            aux_score
            *
            aux_weight
        )

        total_weight += (
            aux_weight
        )

    if (
        news_score
        is not None
        and
        news_weight > 0
    ):

        weighted_sum += (
            news_score
            *
            news_weight
        )

        total_weight += (
            news_weight
        )

    if total_weight == 0:

        recent_score = None

        recent_label = (
            "INSUFFICIENT"
        )

    else:

        recent_score = round(
            weighted_sum
            /
            total_weight,
            2,
        )

        recent_label = (
            score_to_recent_signal(
                recent_score
            )
        )

    recent_confidence = (
        calculate_recent_signal_confidence(

            aux_count=(
                aux.get(
                    "aux_speech_count",
                    0,
                )
            ),

            news_usable_count=(
                news.get(
                    "news_usable_count",
                    0,
                )
            ),

            news_confidence=(
                news.get(
                    "news_confidence",
                    "LOW",
                )
            ),
        )
    )

    return {

        "recent_signal":
            recent_label,

        "recent_signal_score":
            recent_score,

        "recent_signal_confidence":
            recent_confidence,

        "recent_lookback_days":
            lookback_days,

        # ---------------------------------------------
        # Auxiliary speech
        # ---------------------------------------------

        "aux_speech_score":
            aux.get(
                "aux_speech_score"
            ),

        "aux_speech_label":
            aux.get(
                "aux_speech_label"
            ),

        "aux_speech_count":
            aux.get(
                "aux_speech_count",
                0,
            ),

        "aux_speech_evidence":
            aux.get(
                "aux_speech_evidence"
            )
            or [],

        # ---------------------------------------------
        # News
        # ---------------------------------------------

        "recent_news_score":
            news.get(
                "news_score"
            ),

        "recent_news_label":
            news.get(
                "news_label"
            ),

        "recent_news_confidence":
            news.get(
                "news_confidence"
            ),

        "recent_news_usable_count":
            news.get(
                "news_usable_count",
                0,
            ),

        "recent_news_articles":
            news.get(
                "news_articles"
            )
            or [],
    }