# processors/momentum.py

import pandas as pd


# ============================================================
# CONFIG
# ============================================================

IMPORTANT_LEVELS = [
    "HIGH",
    "MEDIUM",
]


# ============================================================
# MOMENTUM LABEL
# ============================================================

def momentum_to_label(
    momentum,
):

    if momentum is None:
        return "INSUFFICIENT"

    try:
        if pd.isna(momentum):
            return "INSUFFICIENT"
    except Exception:
        pass

    momentum = float(
        momentum
    )

    if momentum >= 3:
        return "STRONG_HAWKISH_SHIFT"

    if momentum >= 1:
        return "HAWKISH_SHIFT"

    if momentum <= -3:
        return "STRONG_DOVISH_SHIFT"

    if momentum <= -1:
        return "DOVISH_SHIFT"

    return "STABLE"


# ============================================================
# DISPLAY
# ============================================================

def momentum_display(
    label,
):

    mapping = {
        "STRONG_HAWKISH_SHIFT":
            "▲▲ Strong Hawkish Shift",

        "HAWKISH_SHIFT":
            "▲ Hawkish Shift",

        "STABLE":
            "→ Stable",

        "DOVISH_SHIFT":
            "▼ Dovish Shift",

        "STRONG_DOVISH_SHIFT":
            "▼▼ Strong Dovish Shift",

        "INSUFFICIENT":
            "– Insufficient",
    }

    return mapping.get(
        label,
        str(
            label
            or ""
        ),
    )


# ============================================================
# SCORE CLEAN
# ============================================================

def _to_numeric_score(
    value,
):

    try:

        value = float(
            value
        )

        if pd.isna(
            value
        ):
            return None

        return value

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# DATE
# ============================================================

def _article_date(
    article,
):

    value = (
        article.get(
            "published_at"
        )
        or
        article.get(
            "date"
        )
        or
        article.get(
            "Date"
        )
    )

    if value is None:
        return pd.Timestamp.min

    try:

        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(
            parsed
        ):
            return pd.Timestamp.min

        return parsed

    except Exception:

        return pd.Timestamp.min


# ============================================================
# PREPARE ARTICLES
# ============================================================

def prepare_momentum_articles(
    articles,
):

    prepared = []

    for article in (
        articles
        or []
    ):

        relevance = (
            article.get(
                "fomc_relevance"
            )
            or
            article.get(
                "Relevance"
            )
        )

        if relevance not in IMPORTANT_LEVELS:
            continue

        raw_score = (
            article.get(
                "hawk_dove_score"
            )
        )

        if raw_score is None:

            raw_score = (
                article.get(
                    "Hawk_Dove_Score"
                )
            )

        score = (
            _to_numeric_score(
                raw_score
            )
        )

        if score is None:
            continue

        item = dict(
            article
        )

        item[
            "_momentum_score"
        ] = score

        item[
            "_momentum_date"
        ] = _article_date(
            article
        )

        prepared.append(
            item
        )

    prepared.sort(
        key=lambda item: (
            item[
                "_momentum_date"
            ]
        ),
        reverse=True,
    )

    return prepared


# ============================================================
# EMPTY RESULT
# ============================================================

def _insufficient_result(
    total_count=0,
):

    return {

        "momentum_score":
            None,

        "momentum_label":
            "INSUFFICIENT",

        "momentum_display":
            momentum_display(
                "INSUFFICIENT"
            ),

        "momentum_confidence":
            "INSUFFICIENT",

        "recent_avg":
            None,

        "previous_avg":
            None,

        "recent_count":
            0,

        "previous_count":
            0,

        "total_important_count":
            total_count,

        "recent_articles":
            [],

        "previous_articles":
            [],
    }


# ============================================================
# CALCULATE MOMENTUM
# ============================================================

def calculate_momentum(
    articles,
):

    prepared = (
        prepare_momentum_articles(
            articles
        )
    )

    total_count = len(
        prepared
    )

    # ========================================================
    # SAMPLE RULE
    # ========================================================

    if total_count >= 6:

        recent_n = 3
        previous_n = 3

        confidence = (
            "HIGH"
        )

    elif total_count >= 4:

        recent_n = 2
        previous_n = 2

        confidence = (
            "LOW"
        )

    else:

        return (
            _insufficient_result(
                total_count
            )
        )

    # ========================================================
    # SPLIT
    # ========================================================

    recent_articles = (
        prepared[
            :recent_n
        ]
    )

    previous_articles = (
        prepared[
            recent_n:
            recent_n + previous_n
        ]
    )

    if (
        len(
            recent_articles
        )
        < recent_n
        or
        len(
            previous_articles
        )
        < previous_n
    ):

        return (
            _insufficient_result(
                total_count
            )
        )

    # ========================================================
    # SCORES
    # ========================================================

    recent_scores = [
        item[
            "_momentum_score"
        ]
        for item
        in recent_articles
    ]

    previous_scores = [
        item[
            "_momentum_score"
        ]
        for item
        in previous_articles
    ]

    recent_avg = round(
        sum(
            recent_scores
        )
        /
        len(
            recent_scores
        ),
        2,
    )

    previous_avg = round(
        sum(
            previous_scores
        )
        /
        len(
            previous_scores
        ),
        2,
    )

    momentum_score = round(
        recent_avg
        -
        previous_avg,
        2,
    )

    label = (
        momentum_to_label(
            momentum_score
        )
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    return {

        "momentum_score":
            momentum_score,

        "momentum_label":
            label,

        "momentum_display":
            momentum_display(
                label
            ),

        "momentum_confidence":
            confidence,

        "recent_avg":
            recent_avg,

        "previous_avg":
            previous_avg,

        "recent_count":
            len(
                recent_scores
            ),

        "previous_count":
            len(
                previous_scores
            ),

        "total_important_count":
            total_count,

        "recent_articles":
            recent_articles,

        "previous_articles":
            previous_articles,
    }


# ============================================================
# ATTACH MOMENTUM
# ============================================================

def attach_member_momentum(
    articles,
):

    result = (
        calculate_momentum(
            articles
        )
    )

    output = []

    for article in (
        articles
        or []
    ):

        item = dict(
            article
        )

        item.update({

            "momentum_score":
                result[
                    "momentum_score"
                ],

            "momentum_label":
                result[
                    "momentum_label"
                ],

            "momentum_confidence":
                result[
                    "momentum_confidence"
                ],

            "momentum_recent_avg":
                result[
                    "recent_avg"
                ],

            "momentum_previous_avg":
                result[
                    "previous_avg"
                ],

            "momentum_recent_count":
                result[
                    "recent_count"
                ],

            "momentum_previous_count":
                result[
                    "previous_count"
                ],

            "momentum_total_important_count":
                result[
                    "total_important_count"
                ],
        })

        output.append(
            item
        )

    return output