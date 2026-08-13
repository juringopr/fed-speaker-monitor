# processors/deduplicator.py

import re
from difflib import SequenceMatcher


def normalize_title(
    title
):

    if not title:
        return ""

    title = str(
        title
    ).lower()

    title = re.sub(
        r"[^a-z0-9\s]",
        " ",
        title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


def title_similarity(
    a,
    b
):

    a = normalize_title(
        a
    )

    b = normalize_title(
        b
    )

    if not a or not b:
        return 0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


def deduplicate_articles(
    articles,
    title_threshold=0.92,
):

    results = []

    seen_urls = set()

    for article in articles:

        url = article.get(
            "url"
        )

        if (
            url
            and url in seen_urls
        ):
            continue

        duplicate = False

        for existing in results:

            # 동일 인물 + 동일 날짜 + 제목 유사
            if (
                article.get(
                    "member_name_en"
                )
                ==
                existing.get(
                    "member_name_en"
                )

                and

                article.get(
                    "published_at"
                )
                ==
                existing.get(
                    "published_at"
                )
            ):

                similarity = (
                    title_similarity(
                        article.get(
                            "title"
                        ),

                        existing.get(
                            "title"
                        ),
                    )
                )

                if (
                    similarity
                    >= title_threshold
                ):

                    duplicate = True
                    break

        if duplicate:
            continue

        if url:
            seen_urls.add(
                url
            )

        results.append(
            article
        )

    return results