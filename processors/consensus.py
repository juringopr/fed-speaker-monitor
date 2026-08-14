# processors/consensus.py

from collections import defaultdict


# ============================================================
# CONFIG
# ============================================================

SPEECH_WEIGHT = 0.70
NEWS_WEIGHT = 0.30


# ============================================================
# LABEL
# ============================================================

def score_to_label(score):

    if score is None:
        return "UNKNOWN"

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
# DIRECTION
# ============================================================

def label_direction(label):

    if label in [
        "HAWKISH",
        "NEUTRAL_HAWKISH",
    ]:
        return 1

    if label in [
        "DOVISH",
        "NEUTRAL_DOVISH",
    ]:
        return -1

    if label == "NEUTRAL":
        return 0

    return None


# ============================================================
# CLUSTER NEWS
#
# 같은 날짜의 여러 언론 보도는 같은 발언/이벤트일
# 가능성이 높으므로 독립된 기사 여러 개로 세지 않는다.
# ============================================================

def cluster_news_articles(
    news_articles,
):

    clusters = defaultdict(
        list
    )

    for article in (
        news_articles
        or []
    ):

        score = article.get(
            "score"
        )

        if (
            score is None
            or score == 0
        ):
            continue

        date = (
            article.get(
                "published_at"
            )
            or
            "UNKNOWN_DATE"
        )

        clusters[
            date
        ].append(
            article
        )

    results = []

    for date, articles in clusters.items():

        weighted_scores = []

        for article in articles:

            score = article.get(
                "score"
            )

            if article.get(
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

        denominator = sum(
            weight
            for _, weight
            in weighted_scores
        )

        if denominator == 0:
            continue

        cluster_score = (
            sum(
                score * weight
                for score, weight
                in weighted_scores
            )
            /
            denominator
        )

        cluster_score = round(
            cluster_score,
            2,
        )

        preferred_count = sum(
            1
            for article in articles
            if article.get(
                "preferred_source"
            )
        )

        results.append({

            "date":
                date,

            "score":
                cluster_score,

            "label":
                score_to_label(
                    cluster_score
                ),

            "article_count":
                len(
                    articles
                ),

            "preferred_count":
                preferred_count,

            "articles":
                articles,
        })

    results.sort(
        key=lambda item: (
            item.get(
                "date"
            )
            or ""
        ),
        reverse=True,
    )

    return results


# ============================================================
# CLUSTERED NEWS SUMMARY
# ============================================================

def summarize_news_clusters(
    news_analysis,
):

    news_articles = (
        news_analysis.get(
            "news_articles"
        )
        or []
    )

    clusters = (
        cluster_news_articles(
            news_articles
        )
    )

    if not clusters:

        return {

            "cluster_score":
                None,

            "cluster_label":
                "INSUFFICIENT",

            "cluster_count":
                0,

            "cluster_confidence":
                "LOW",

            "clusters":
                [],
        }

    # --------------------------------------------------------
    # 최근 이벤트를 조금 더 중요하게
    # --------------------------------------------------------

    weighted = []

    for index, cluster in enumerate(
        clusters
    ):

        if index == 0:
            recency_weight = 1.5

        elif index == 1:
            recency_weight = 1.25

        else:
            recency_weight = 1.0

        # 신뢰매체가 하나라도 있으면 추가 가중
        if (
            cluster.get(
                "preferred_count",
                0
            )
            > 0
        ):
            quality_weight = 1.2

        else:
            quality_weight = 1.0

        total_weight = (
            recency_weight
            *
            quality_weight
        )

        weighted.append(
            (
                cluster[
                    "score"
                ],
                total_weight,
            )
        )

    denominator = sum(
        weight
        for _, weight
        in weighted
    )

    cluster_score = (
        sum(
            score * weight
            for score, weight
            in weighted
        )
        /
        denominator
    )

    cluster_score = round(
        cluster_score,
        2,
    )

    cluster_count = len(
        clusters
    )

    # --------------------------------------------------------
    # Confidence는 "기사 수"가 아니라
    # 독립 뉴스 이벤트 수 기준
    # --------------------------------------------------------

    if cluster_count >= 3:

        confidence = (
            "HIGH"
        )

    elif cluster_count >= 2:

        confidence = (
            "MEDIUM"
        )

    else:

        confidence = (
            "LOW"
        )

    return {

        "cluster_score":
            cluster_score,

        "cluster_label":
            score_to_label(
                cluster_score
            ),

        "cluster_count":
            cluster_count,

        "cluster_confidence":
            confidence,

        "clusters":
            clusters,
    }


# ============================================================
# CONSENSUS
# ============================================================

def calculate_consensus(
    speech_score,
    speech_label,
    news_analysis,
):

    clustered = (
        summarize_news_clusters(
            news_analysis
        )
    )

    news_score = (
        clustered[
            "cluster_score"
        ]
    )

    news_label = (
        clustered[
            "cluster_label"
        ]
    )

    # ========================================================
    # NEWS INSUFFICIENT
    #
    # 뉴스가 없으면 공식 발언을 그대로 최종값으로 사용.
    # ========================================================

    if news_score is None:

        return {

            "speech_score":
                speech_score,

            "speech_label":
                speech_label,

            "news_score":
                None,

            "news_label":
                "INSUFFICIENT",

            "news_cluster_count":
                0,

            "news_confidence":
                "LOW",

            "consensus_score":
                speech_score,

            "consensus_label":
                speech_label,

            "cross_check":
                "NEWS_INSUFFICIENT",

            "news_clusters":
                [],
        }

    # ========================================================
    # CONSENSUS SCORE
    # ========================================================

    final_score = (
        float(
            speech_score
            or 0
        )
        *
        SPEECH_WEIGHT
        +
        float(
            news_score
        )
        *
        NEWS_WEIGHT
    )

    final_score = round(
        final_score,
        2,
    )

    final_label = (
        score_to_label(
            final_score
        )
    )

    # ========================================================
    # CROSS CHECK
    # ========================================================

    speech_direction = (
        label_direction(
            speech_label
        )
    )

    news_direction = (
        label_direction(
            news_label
        )
    )

    if (
        speech_direction is None
        or
        news_direction is None
    ):

        cross_check = (
            "UNKNOWN"
        )

    elif (
        speech_direction
        *
        news_direction
        == -1
    ):

        # 완전 반대
        cross_check = (
            "DIVERGENCE"
        )

    elif (
        speech_direction
        ==
        news_direction
    ):

        cross_check = (
            "CONFIRMED"
        )

    elif (
        speech_direction == 0
        or
        news_direction == 0
    ):

        cross_check = (
            "PARTIAL"
        )

    else:

        cross_check = (
            "PARTIAL"
        )

    return {

        "speech_score":
            speech_score,

        "speech_label":
            speech_label,

        "news_score":
            news_score,

        "news_label":
            news_label,

        "news_cluster_count":
            clustered[
                "cluster_count"
            ],

        "news_confidence":
            clustered[
                "cluster_confidence"
            ],

        "consensus_score":
            final_score,

        "consensus_label":
            final_label,

        "cross_check":
            cross_check,

        "news_clusters":
            clustered[
                "clusters"
            ],
    }