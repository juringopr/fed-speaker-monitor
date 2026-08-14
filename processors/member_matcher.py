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


# ============================================================
# SPECIAL MEMBERS
# ============================================================

# Stephen Miran은 현재 일반 FOMC member master와 분리해서 관리.
# URL이 miranYYYYMMDD 형태이므로 안정적으로 식별 가능.
MIRAN_MEMBER = {
    "name_ko":
        "스티븐 미란",

    "name_en":
        "Stephen Miran",

    "role_ko":
        "전 연준 이사",

    "role_en":
        "Former Federal Reserve Governor",

    "fed":
        "Federal Reserve Board",

    # 현재 FOMC 집계에서는 별도 탭으로 분리
    "voter":
        0,

    "vote_year":
        None,

    "priority":
        0,

    "member_group":
        "MIRAN",
}


# ============================================================
# LOAD MEMBERS
# ============================================================

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
                None,
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


# ============================================================
# MEMBER SEARCH TERMS
# ============================================================

def _member_search_terms(
    member,
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
                str(
                    value
                ).strip()
            )

    aliases = member.get(
        "aliases"
    )

    if aliases:

        for alias in str(
            aliases
        ).split(
            "|"
        ):

            alias = (
                alias.strip()
            )

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

            surname = (
                parts[-1]
            )

            if len(
                surname
            ) >= 4:

                terms.append(
                    surname
                )

    return list(
        dict.fromkeys(
            terms
        )
    )


# ============================================================
# SPECIAL MATCH - STEPHEN MIRAN
# ============================================================

def _match_special_member(
    article,
):

    url = str(
        article.get(
            "url"
        )
        or ""
    ).lower()

    speaker_raw = str(
        article.get(
            "speaker_raw"
        )
        or ""
    ).lower()

    title = str(
        article.get(
            "title"
        )
        or ""
    ).lower()

    text = str(
        article.get(
            "text"
        )
        or ""
    )[:3000].lower()

    # --------------------------------------------------------
    # URL
    #
    # 예:
    # /speech/miran20260326a.htm
    # --------------------------------------------------------

    if (
        "miran20"
        in url
    ):

        result = dict(
            MIRAN_MEMBER
        )

        result[
            "match_score"
        ] = 100

        return result

    # --------------------------------------------------------
    # SPEAKER NAME
    # --------------------------------------------------------

    if any(
        token in speaker_raw
        for token in [
            "stephen miran",
            "stephen i. miran",
        ]
    ):

        result = dict(
            MIRAN_MEMBER
        )

        result[
            "match_score"
        ] = 100

        return result

    # --------------------------------------------------------
    # TITLE / BODY
    #
    # URL이 바뀌더라도 이름이 본문에 있으면 대응.
    # --------------------------------------------------------

    combined = (
        title
        + " "
        + text
    )

    if (
        "stephen miran"
        in combined
        or
        "stephen i. miran"
        in combined
    ):

        result = dict(
            MIRAN_MEMBER
        )

        result[
            "match_score"
        ] = 80

        return result

    return None


# ============================================================
# MATCH MEMBER
# ============================================================

def match_member(
    article,
):
    """
    article 예:

    {
        speaker_raw: "Lorie Logan",
        title: "...",
        text: "...",
        url: "..."
    }

    우선순위
    ----------------------------------------------------------
    1. Stephen Miran 특별 매칭
    2. fed_members.csv 일반 매칭
    """

    # ========================================================
    # 1. SPECIAL MEMBER
    # ========================================================

    special_member = (
        _match_special_member(
            article
        )
    )

    if special_member:

        return special_member

    # ========================================================
    # 2. NORMAL MEMBERS
    # ========================================================

    members = (
        load_members()
    )

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

            if (
                term_lower
                in search_text
            ):

                # ------------------------------------------------
                # full English name
                # ------------------------------------------------

                if (
                    term_lower
                    ==
                    str(
                        member.get(
                            "name_en"
                        )
                        or ""
                    ).lower()
                ):

                    score += 10

                # ------------------------------------------------
                # full Korean name
                # ------------------------------------------------

                elif (
                    term_lower
                    ==
                    str(
                        member.get(
                            "name_ko"
                        )
                        or ""
                    ).lower()
                ):

                    score += 10

                # ------------------------------------------------
                # alias / surname / role
                # ------------------------------------------------

                else:

                    score += 3

        # ====================================================
        # SPEAKER_RAW DIRECT MATCH
        # ====================================================

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
            in
            str(
                speaker_raw
            ).lower()
        ):

            score += 20

        # ====================================================
        # BEST MEMBER
        # ====================================================

        if (
            score
            >
            best_score
        ):

            best_score = (
                score
            )

            best_member = (
                member
            )

    # ========================================================
    # NO MATCH
    # ========================================================

    if (
        best_score
        <= 0
    ):

        return None

    result = dict(
        best_member
    )

    result[
        "match_score"
    ] = (
        best_score
    )

    # 일반 current FOMC member
    result[
        "member_group"
    ] = (
        "FOMC"
    )

    return result


# ============================================================
# ENRICH ARTICLE
# ============================================================

def enrich_with_member(
    article,
):

    result = dict(
        article
    )

    member = (
        match_member(
            article
        )
    )

    # ========================================================
    # UNMATCHED
    # ========================================================

    if not member:

        result.update({

            "member_name_ko":
                None,

            "member_name_en":
                None,

            "member_role_ko":
                None,

            "member_role_en":
                None,

            "member_fed":
                None,

            "member_voter":
                None,

            "member_vote_year":
                None,

            "member_priority":
                None,

            "member_match_score":
                0,

            "member_group":
                "UNMATCHED",
        })

        return result

    # ========================================================
    # MATCHED
    # ========================================================

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

        "member_group":
            member.get(
                "member_group"
            )
            or
            "FOMC",
    })

    return result