# processors/topic_classifier.py

TOPICS = {

    "INFLATION": [
        "inflation",
        "prices",
        "price stability",
        "pce",
        "cpi",
        "disinflation",
    ],

    "LABOR": [
        "labor market",
        "labour market",
        "employment",
        "unemployment",
        "jobs",
        "wages",
        "payroll",
    ],

    "RATES": [
        "monetary policy",
        "interest rate",
        "interest rates",
        "federal funds rate",
        "rate cut",
        "rate cuts",
        "rate hike",
        "rate hikes",
    ],

    "GROWTH": [
        "economic growth",
        "growth",
        "gdp",
        "economy",
        "economic outlook",
        "recession",
    ],

    "BALANCE_SHEET": [
        "balance sheet",
        "reserves",
        "quantitative tightening",
        "quantitative easing",
        "qt",
        "qe",
    ],

    "FINANCIAL_CONDITIONS": [
        "financial conditions",
        "credit conditions",
        "banking system",
        "liquidity",
    ],

    "TARIFFS": [
        "tariff",
        "tariffs",
        "trade policy",
    ],

    "FX": [
        "dollar",
        "exchange rate",
        "currency",
        "foreign exchange",
    ],
}


def classify_topics(
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

    combined = (
        title
        + " "
        + text
    ).lower()

    found = []

    for topic, keywords in (
        TOPICS.items()
    ):

        if any(
            keyword
            in combined

            for keyword
            in keywords
        ):

            found.append(
                topic
            )

    return found