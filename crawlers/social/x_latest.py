# crawlers/social/x_latest.py

from pathlib import Path
from datetime import datetime, timezone
import os
import time

import pandas as pd
import requests


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

DATA_DIR = (
    PROJECT_ROOT
    / "data"
)

MEMBERS_PATH = (
    DATA_DIR
    / "fed_members.csv"
)

CACHE_PATH = (
    DATA_DIR
    / "x_latest.csv"
)


# ============================================================
# X API
# ============================================================

X_API_BASE = "https://api.x.com/2"

REQUEST_TIMEOUT = 15

DEFAULT_SLEEP = 0.25


# ============================================================
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent":
        "FedSpeakerMonitor/1.0"
})


# ============================================================
# HELPERS
# ============================================================

def _clean_value(
    value,
):

    if value is None:
        return None

    try:

        if pd.isna(value):
            return None

    except Exception:
        pass

    value = (
        str(value)
        .strip()
    )

    if not value:
        return None

    return value


def clean_x_handle(
    handle,
):

    handle = (
        _clean_value(
            handle
        )
    )

    if not handle:
        return None

    if handle.startswith("@"):

        handle = (
            handle[1:]
        )

    return (
        handle.strip()
    )


# ============================================================
# TOKEN
# ============================================================

def get_bearer_token():

    token = (
        os.getenv(
            "X_BEARER_TOKEN"
        )
    )

    if not token:

        raise RuntimeError(
            "X_BEARER_TOKEN 환경변수가 없습니다."
        )

    return (
        token.strip()
    )


# ============================================================
# X REQUEST
# ============================================================

def _x_get(
    endpoint,
    params=None,
):

    token = (
        get_bearer_token()
    )

    url = (
        f"{X_API_BASE}"
        f"{endpoint}"
    )

    response = (
        SESSION.get(
            url,
            headers={
                "Authorization":
                    f"Bearer {token}"
            },
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    )

    if response.status_code == 401:

        raise RuntimeError(
            "X API 인증 실패(401). "
            "Bearer Token을 확인해주세요."
        )

    if response.status_code == 402:

        raise RuntimeError(
            "X API 크레딧/결제 오류(402)."
        )

    if response.status_code == 403:

        raise RuntimeError(
            "X API 접근 거부(403). "
            "현재 API 권한을 확인해주세요."
        )

    if response.status_code == 429:

        raise RuntimeError(
            "X API Rate Limit(429)에 도달했습니다."
        )

    response.raise_for_status()

    return (
        response.json()
    )


# ============================================================
# USER
# ============================================================

def get_x_user(
    handle,
):

    handle = (
        clean_x_handle(
            handle
        )
    )

    if not handle:
        return None

    payload = (
        _x_get(
            f"/users/by/username/{handle}",
            params={
                "user.fields":
                    (
                        "id,name,username,"
                        "verified,description"
                    )
            },
        )
    )

    return (
        payload.get(
            "data"
        )
    )


# ============================================================
# POSTS
# ============================================================

def get_user_posts(
    user_id,
    max_results=10,
):

    payload = (
        _x_get(
            f"/users/{user_id}/tweets",
            params={
                "max_results":
                    max(
                        5,
                        int(max_results),
                    ),

                "tweet.fields":
                    (
                        "id,text,created_at,"
                        "author_id,"
                        "conversation_id,"
                        "referenced_tweets"
                    ),

                "exclude":
                    "retweets,replies",
            },
        )
    )

    return (
        payload.get(
            "data"
        )
        or []
    )


# ============================================================
# LATEST POST
# ============================================================

def get_latest_x_post(
    handle,
):
    """
    날짜 제한 없이
    가장 최근 original post 1개 반환.

    reply / retweet 제외.
    """

    handle = (
        clean_x_handle(
            handle
        )
    )

    if not handle:
        return None

    user = (
        get_x_user(
            handle
        )
    )

    if not user:
        return None

    user_id = (
        user.get(
            "id"
        )
    )

    if not user_id:
        return None

    posts = (
        get_user_posts(
            user_id,
            max_results=10,
        )
    )

    if not posts:
        return None

    posts = sorted(
        posts,
        key=lambda x: (
            x.get(
                "created_at"
            )
            or
            ""
        ),
        reverse=True,
    )

    latest = (
        posts[0]
    )

    post_id = (
        latest.get(
            "id"
        )
    )

    post_url = None

    if post_id:

        post_url = (
            f"https://x.com/"
            f"{handle}/status/"
            f"{post_id}"
        )

    return {

        "platform":
            "X",

        "x_handle":
            handle,

        "x_name":
            user.get(
                "name"
            ),

        "x_username":
            user.get(
                "username"
            ),

        "x_verified":
            user.get(
                "verified"
            ),

        "x_description":
            user.get(
                "description"
            ),

        "x_user_id":
            user_id,

        "x_post_id":
            post_id,

        "x_published_at":
            latest.get(
                "created_at"
            ),

        "x_text":
            latest.get(
                "text"
            ),

        "x_url":
            post_url,
    }


# ============================================================
# LOAD MEMBERS
# ============================================================

def load_members():

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp949",
        "euc-kr",
    ]

    last_error = None

    for encoding in encodings:

        try:

            return (
                pd.read_csv(
                    MEMBERS_PATH,
                    encoding=encoding,
                )
            )

        except UnicodeDecodeError as exc:

            last_error = exc

    raise last_error


def load_members_with_x():

    df = (
        load_members()
    )

    if (
        "x_handle"
        not in df.columns
    ):

        raise ValueError(
            "fed_members.csv에 "
            "x_handle 컬럼이 없습니다."
        )

    df[
        "x_handle"
    ] = (
        df[
            "x_handle"
        ]
        .apply(
            clean_x_handle
        )
    )

    return (
        df[
            df[
                "x_handle"
            ]
            .notna()
        ]
        .copy()
    )


# ============================================================
# CRAWL ALL
# ============================================================

def crawl_latest_x_posts(
    sleep_seconds=DEFAULT_SLEEP,
):

    members = (
        load_members_with_x()
    )

    results = []

    total = len(
        members
    )

    for position, (
        _,
        row,
    ) in enumerate(
        members.iterrows(),
        start=1,
    ):

        name_en = (
            _clean_value(
                row.get(
                    "name_en"
                )
            )
        )

        name_ko = (
            _clean_value(
                row.get(
                    "name_ko"
                )
            )
        )

        fed = (
            _clean_value(
                row.get(
                    "fed"
                )
            )
        )

        handle = (
            clean_x_handle(
                row.get(
                    "x_handle"
                )
            )
        )

        print(
            f"[X {position}/{total}] "
            f"{name_en} "
            f"@{handle}"
        )

        try:

            latest = (
                get_latest_x_post(
                    handle
                )
            )

            if latest:

                result = {

                    "member_name_en":
                        name_en,

                    "member_name_ko":
                        name_ko,

                    "fed":
                        fed,

                    **latest,

                    "x_error":
                        None,
                }

                print(
                    "    OK:",
                    result.get(
                        "x_published_at"
                    )
                )

            else:

                result = {

                    "member_name_en":
                        name_en,

                    "member_name_ko":
                        name_ko,

                    "fed":
                        fed,

                    "platform":
                        "X",

                    "x_handle":
                        handle,

                    "x_name":
                        None,

                    "x_username":
                        handle,

                    "x_verified":
                        None,

                    "x_description":
                        None,

                    "x_user_id":
                        None,

                    "x_post_id":
                        None,

                    "x_published_at":
                        None,

                    "x_text":
                        None,

                    "x_url":
                        None,

                    "x_error":
                        "NO_POST",
                }

                print(
                    "    NO POST"
                )

        except Exception as exc:

            result = {

                "member_name_en":
                    name_en,

                "member_name_ko":
                    name_ko,

                "fed":
                    fed,

                "platform":
                    "X",

                "x_handle":
                    handle,

                "x_name":
                    None,

                "x_username":
                    handle,

                "x_verified":
                    None,

                "x_description":
                    None,

                "x_user_id":
                    None,

                "x_post_id":
                    None,

                "x_published_at":
                    None,

                "x_text":
                    None,

                "x_url":
                    None,

                "x_error":
                    str(exc),
            }

            print(
                "    FAIL:",
                exc
            )

        results.append(
            result
        )

        if sleep_seconds:

            time.sleep(
                sleep_seconds
            )

    return results


# ============================================================
# DATAFRAME
# ============================================================

def latest_x_posts_to_dataframe(
    results,
):

    columns = [
        "member_name_ko",
        "member_name_en",
        "fed",

        "x_handle",

        "x_published_at",
        "x_text",
        "x_url",

        "x_name",
        "x_verified",

        "x_post_id",
        "x_user_id",

        "x_error",

        "cache_updated_at",
    ]

    df = (
        pd.DataFrame(
            results
            or []
        )
    )

    for column in columns:

        if column not in df.columns:

            df[
                column
            ] = None

    df = (
        df[
            columns
        ]
        .copy()
    )

    df[
        "x_published_at"
    ] = pd.to_datetime(
        df[
            "x_published_at"
        ],
        errors="coerce",
        utc=True,
    )

    return (
        df.sort_values(
            [
                "x_published_at",
                "member_name_en",
            ],
            ascending=[
                False,
                True,
            ],
            na_position="last",
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# SAVE CACHE
# ============================================================

def save_x_cache(
    results,
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = (
        latest_x_posts_to_dataframe(
            results
        )
    )

    updated_at = (
        datetime.now(
            timezone.utc
        )
        .strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )

    df[
        "cache_updated_at"
    ] = (
        updated_at
    )

    # pandas timezone 포함 timestamp를
    # csv 문자열로 저장
    df[
        "x_published_at"
    ] = (
        df[
            "x_published_at"
        ]
        .dt.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )

    df.to_csv(
        CACHE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"[X CACHE SAVED] "
        f"{CACHE_PATH}"
    )

    return (
        CACHE_PATH
    )


# ============================================================
# LOAD CACHE
# ============================================================

def load_x_cache():

    if not CACHE_PATH.exists():

        return (
            pd.DataFrame()
        )

    try:

        df = (
            pd.read_csv(
                CACHE_PATH,
                encoding="utf-8-sig",
            )
        )

    except Exception:

        return (
            pd.DataFrame()
        )

    if (
        "x_published_at"
        in df.columns
    ):

        df[
            "x_published_at"
        ] = pd.to_datetime(
            df[
                "x_published_at"
            ],
            errors="coerce",
            utc=True,
        )

    return df


# ============================================================
# UPDATE CACHE
# ============================================================

def update_x_cache():
    """
    실제 X API 호출.

    이 함수는 앱 새로고침 때 자동 호출하지 않고
    사용자가 업데이트 버튼을 눌렀을 때만 호출한다.
    """

    print()
    print(
        "=" * 80
    )
    print(
        "UPDATE X CACHE"
    )
    print(
        "=" * 80
    )

    results = (
        crawl_latest_x_posts()
    )

    save_x_cache(
        results
    )

    return (
        load_x_cache()
    )


# ============================================================
# CACHE INFO
# ============================================================

def get_x_cache_updated_at():

    df = (
        load_x_cache()
    )

    if df.empty:

        return None

    if (
        "cache_updated_at"
        not in df.columns
    ):

        return None

    values = (
        df[
            "cache_updated_at"
        ]
        .dropna()
    )

    if values.empty:

        return None

    return (
        values.iloc[0]
    )


# ============================================================
# TEST SINGLE
# ============================================================

def test_single_handle(
    handle="@neelkashkari",
):

    from pprint import pprint

    result = (
        get_latest_x_post(
            handle
        )
    )

    pprint(
        result
    )

    return result


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    df = (
        update_x_cache()
    )

    print()
    print(
        df[
            [
                "member_name_en",
                "x_handle",
                "x_published_at",
                "x_text",
            ]
        ]
    )