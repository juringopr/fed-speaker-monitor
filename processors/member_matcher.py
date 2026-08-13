# processors/member_matcher.py

from pathlib import Path

import pandas as pd


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

MEMBERS_PATH = (
    PROJECT_ROOT
    / "data"
    / "fed_members.csv"
)


_MEMBER_CACHE = None


def load_members():
    global _MEMBER_CACHE

    if _MEMBER_CACHE is not None:
        return _MEMBER_CACHE

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp949",
        "euc-kr",
    ]

    last_error = None

    for encoding in encodings:

        try:

            df = pd.read_csv(
                MEMBERS_PATH,
                encoding=encoding,
            )

            df = df.where(
                pd.notnull(df),
                None
            )

            _MEMBER_CACHE = (
                df.to_dict(
                    orient="records"
                )
            )

            return _MEMBER_CACHE

        except UnicodeDecodeError as exc:
            last_error = exc

    raise last_error


def _member_search_terms(
    member
):

    terms = []

    for key in [
        "name_en",
        "name_ko",
        "role_en",
        "role_ko",
    ]:

        value = member.get(
            key
        )

        if value:

            terms.append(
                str(value).strip()
            )

    aliases = member.get(
        "aliases"
    )

    if aliases:

        for alias in str(
            aliases
        ).split("|"):

            alias = alias.strip()

            if alias:
                terms.append(
                    alias
                )

    name_en = member.get(
        "name_en"
    )

    if name_en:

        parts = str(
            name_en
        ).split()

        if parts:

            surname = parts[-1]

            if len(surname) >= 4:
                terms.append(
                    surname
                )

    return list(
        dict.fromkeys(
            terms
        )
    )


def match_member(
    article
):
    """
    article 예:
    {
        speaker_raw: "Lorie Logan",
        title: "...",
        text: "...",
        url: "..."
    }
    """

    members = load_members()

    search_text = " ".join([
        str(
            article.get(
                "speaker_raw"
            )
            or ""
        ),

        str(
            article.get(
                "title"
            )
            or ""
        ),

        str(
            article.get(
                "text"
            )
            or ""
        )[:3000],

        str(
            article.get(
                "url"
            )
            or ""
        ),
    ]).lower()

    best_member = None
    best_score = 0

    for member in members:

        score = 0

        terms = (
            _member_search_terms(
                member
            )
        )

        for term in terms:

            term_lower = (
                term.lower()
            )

            if not term_lower:
                continue

            if term_lower in search_text:

                # full name이면 강한 점수
                if (
                    term_lower
                    == str(
                        member.get(
                            "name_en"
                        )
                        or ""
                    ).lower()
                ):
                    score += 10

                elif (
                    term_lower
                    == str(
                        member.get(
                            "name_ko"
                        )
                        or ""
                    ).lower()
                ):
                    score += 10

                else:
                    score += 3

        # speaker_raw 직접 일치
        speaker_raw = (
            article.get(
                "speaker_raw"
            )
        )

        if (
            speaker_raw
            and
            member.get(
                "name_en"
            )
            and
            str(
                member[
                    "name_en"
                ]
            ).lower()
            in str(
                speaker_raw
            ).lower()
        ):
            score += 20

        if score > best_score:

            best_score = score
            best_member = member

    if best_score <= 0:
        return None

    result = dict(
        best_member
    )

    result[
        "match_score"
    ] = best_score

    return result


def enrich_with_member(
    article
):

    result = dict(
        article
    )

    member = (
        match_member(
            article
        )
    )

    if not member:

        result.update({
            "member_name_ko": None,
            "member_name_en": None,
            "member_role_ko": None,
            "member_role_en": None,
            "member_fed": None,
            "member_voter": None,
            "member_vote_year": None,
            "member_priority": None,
            "member_match_score": 0,
        })

        return result

    result.update({
        "member_name_ko":
            member.get(
                "name_ko"
            ),

        "member_name_en":
            member.get(
                "name_en"
            ),

        "member_role_ko":
            member.get(
                "role_ko"
            ),

        "member_role_en":
            member.get(
                "role_en"
            ),

        "member_fed":
            member.get(
                "fed"
            ),

        "member_voter":
            member.get(
                "voter"
            ),

        "member_vote_year":
            member.get(
                "vote_year"
            ),

        "member_priority":
            member.get(
                "priority"
            ),

        "member_match_score":
            member.get(
                "match_score"
            ),
    })

    return result