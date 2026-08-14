# app.py

from pathlib import Path
from datetime import datetime
import json
import os
import subprocess
import sys

import pandas as pd
import streamlit as st

from crawlers.social.x_latest import (
    load_x_cache,
    update_x_cache,
    get_x_cache_updated_at,
)


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "output"
)

DATA_DIR = (
    PROJECT_ROOT
    / "data"
)

FINAL_EVENTS_PATH = (
    DATA_DIR
    / "final_events.json"
)

PIPELINE_FILE = (
    PROJECT_ROOT
    / "merge_pipeline.py"
)

NEWS_UPDATED_LOOKBACK_DAYS = 14


# App에서만 숨김
HIDDEN_APP_MEMBERS = {
    "Stephen Miran",
}


# ============================================================
# PERSONAL X ACCOUNTS
# ============================================================

PERSONAL_X_HANDLES = {
    "Austan_Goolsbee",
    "MaryDalyEcon",
    "neelkashkari",
}


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Fed Speaker Monitor",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STREAMLIT SECRET -> ENV
# ============================================================

try:

    if (
        not os.getenv(
            "X_BEARER_TOKEN"
        )
        and
        "X_BEARER_TOKEN"
        in st.secrets
    ):

        os.environ[
            "X_BEARER_TOKEN"
        ] = str(
            st.secrets[
                "X_BEARER_TOKEN"
            ]
        )

except Exception:
    pass



# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

.block-container {
    padding-top: 2.2rem;
    padding-bottom: 3rem;
}

.main-title {
    font-size: 2.1rem;
    font-weight: 750;
    line-height: 1.25;
    margin: 0 0 0.15rem 0;
    padding-top: 0.15rem;
}

.header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 30px;
    margin-top: 0;
    margin-bottom: 0.9rem;
}

.sub-title {
    color: #666666;
    font-size: 0.94rem;
}

.top-stats {
    text-align: right;
    color: #6b7280;
    font-size: 0.76rem;
    line-height: 1.65;
    white-space: nowrap;
}

.method-note {
    color: #6b7280;
    font-size: 0.82rem;
    margin-top: -0.20rem;
    margin-bottom: 0.85rem;
    line-height: 1.65;
}

.model-box {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 13px 16px;
    margin-top: 0.2rem;
    margin-bottom: 1rem;
    background-color: rgba(250,250,250,0.55);
    font-size: 0.82rem;
    line-height: 1.7;
    color: #4b5563;
}

.model-box b {
    color: #252525;
}

.sns-note {
    color: #6b7280;
    font-size: 0.82rem;
    margin-top: -0.1rem;
    margin-bottom: 0.8rem;
}

.news-note {
    color: #6b7280;
    font-size: 0.82rem;
    margin-top: -0.1rem;
    margin-bottom: 0.8rem;
}

.news-card {
    padding: 0.8rem 0.2rem 1rem 0.2rem;
}

.news-date {
    color: #8a8a8a;
    font-size: 0.76rem;
    margin-bottom: 0.22rem;
}

.news-member {
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 0.15rem;
}

.news-meta {
    color: #6b7280;
    font-size: 0.79rem;
    margin-bottom: 0.45rem;
}

.news-title {
    font-size: 0.94rem;
    font-weight: 650;
    line-height: 1.45;
    margin-bottom: 0.35rem;
}

.news-summary {
    font-size: 0.86rem;
    line-height: 1.6;
    color: #444444;
    margin-bottom: 0.35rem;
}

div[data-testid="stMetric"] {
    border: 1px solid #eeeeee;
    padding: 10px;
    border-radius: 10px;
    background: white;
}
/* 위원별 상세 metric 제목 */
div[data-testid="stMetric"] label {
    font-size: 13px !important;
}

/* 위원별 상세 metric 값 */
div[data-testid="stMetricValue"] {
    font-size: 18px !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# LATEST EXCEL
# ============================================================

def get_latest_excel():

    if not OUTPUT_DIR.exists():
        return None

    files = list(
        OUTPUT_DIR.glob(
            "fed_speaker_monitor_*.xlsx"
        )
    )

    if not files:
        return None

    return max(
        files,
        key=lambda path:
            path.stat().st_mtime,
    )


# ============================================================
# LOAD EXCEL
# ============================================================

@st.cache_data(
    show_spinner=False
)
def load_excel(
    path_str,
    modified_time,
):

    path = Path(
        path_str
    )

    excel = pd.ExcelFile(
        path
    )

    if (
        "Articles"
        in excel.sheet_names
    ):

        df = pd.read_excel(
            path,
            sheet_name="Articles",
        )

    elif (
        "ALL"
        in excel.sheet_names
    ):

        df = pd.read_excel(
            path,
            sheet_name="ALL",
        )

    else:

        raise ValueError(
            "Articles 또는 ALL 시트를 찾을 수 없습니다."
        )

    rename_map = {

        "Member_EN":
            "Speaker",

        "Member_KO":
            "Speaker_KO",

        "FOMC_Relevance":
            "Relevance",

        "Current_Stance":
            "Speech_Current_Stance",

        "Current_Stance_Score":
            "Speech_Current_Score",

        "Current_Stance_Samples":
            "Speech_Sample_Count",

        "Consensus":
            "Consensus_Stance",

        "Term":
            "Vote_Year",

        "Momentum":
            "Momentum_Label",
    }

    df = df.rename(
        columns={
            key: value
            for key, value
            in rename_map.items()
            if key in df.columns
        }
    )

    if (
        "Date"
        in df.columns
    ):

        df[
            "Date"
        ] = pd.to_datetime(
            df[
                "Date"
            ],
            errors="coerce",
        )

    defaults = {

        "Speaker":
            "",

        "Speaker_KO":
            "",

        "Fed":
            "",

        "Voter":
            None,

        "Vote_Year":
            None,

        "Source":
            "",

        "Title":
            "",

        "URL":
            "",

        "Relevance":
            "",

        "Relevance_Score":
            None,

        "Hawk_Dove":
            "",

        "Hawk_Dove_Score":
            None,

        "Topics":
            "",
    }

    for (
        column,
        default,
    ) in defaults.items():

        if (
            column
            not in df.columns
        ):

            df[
                column
            ] = default

    numeric_columns = [
        "Relevance_Score",
        "Hawk_Dove_Score",
    ]

    for column in numeric_columns:

        if (
            column
            in df.columns
        ):

            df[
                column
            ] = pd.to_numeric(
                df[
                    column
                ],
                errors="coerce",
            )

    return df


# ============================================================
# LOAD FINAL EVENTS
# ============================================================

@st.cache_data(
    show_spinner=False
)
def load_final_events(
    path_str,
    modified_time,
):

    path = Path(
        path_str
    )

    if not path.exists():
        return []

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            payload = json.load(
                file
            )

        return (
            payload.get(
                "events"
            )
            or
            []
        )

    except Exception:

        return []


# ============================================================
# RUN PIPELINE
# ============================================================

def run_pipeline():

    return subprocess.run(
        [
            sys.executable,
            str(
                PIPELINE_FILE
            ),
        ],
        cwd=str(
            PROJECT_ROOT
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


# ============================================================
# HELPERS
# ============================================================

def safe_text(
    value,
):

    if value is None:
        return ""

    try:

        if pd.isna(
            value
        ):
            return ""

    except Exception:
        pass

    return str(
        value
    )


def safe_float(
    value,
):

    if value is None:
        return None

    try:

        if pd.isna(
            value
        ):
            return None

    except Exception:
        pass

    try:
        return float(
            value
        )

    except Exception:
        return None


def first_nonempty(
    series,
):

    if series is None:
        return ""

    values = (
        series.dropna()
    )

    if len(
        values
    ) == 0:

        return ""

    return values.iloc[
        0
    ]


# ============================================================
# VOTER
# ============================================================

def voter_flag(
    row,
):

    voter = row.get(
        "Voter"
    )

    if pd.isna(
        voter
    ):

        return False

    try:

        return (
            int(
                float(
                    voter
                )
            )
            == 1
        )

    except Exception:

        value = (
            safe_text(
                voter
            )
            .strip()
            .lower()
        )

        return value in [
            "1",
            "true",
            "yes",
            "y",
        ]


# ============================================================
# MEMBER DISPLAY
# ============================================================

def member_display_name(
    speaker,
    row,
):

    value = row.get(
        "Vote_Year"
    )

    if pd.notna(
        value
    ):

        try:

            year = str(
                int(
                    float(
                        value
                    )
                )
            )

        except Exception:

            year = (
                safe_text(
                    value
                )
                .strip()
            )

        if year:

            return (
                f"{speaker} (~{year})"
            )

    return (
        f"{speaker} (당연직)"
    )


# ============================================================
# DISPLAY
# ============================================================

def hd_display(
    label,
):

    mapping = {

        "HAWKISH":
            "🔴 Hawkish",

        "NEUTRAL_HAWKISH":
            "🟥 Neutral Hawkish",

        "NEUTRAL":
            "⚪ Neutral",

        "NEUTRAL_DOVISH":
            "🟩 Neutral Dovish",

        "DOVISH":
            "🟢 Dovish",

        "INSUFFICIENT":
            "– Insufficient",

        "UNKNOWN":
            "– Unknown",
    }

    return mapping.get(
        safe_text(
            label
        ).upper(),
        safe_text(
            label
        ),
    )


def confidence_display(
    value,
):

    value = (
        safe_text(
            value
        )
        .upper()
        .strip()
    )

    mapping = {
        "HIGH":
            "High",
        "MEDIUM":
            "Medium",
        "LOW":
            "Low",
        "INSUFFICIENT":
            "Insufficient",
    }

    return mapping.get(
        value,
        value,
    )


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
        safe_text(
            label
        ),
    )


# ============================================================
# COLORS
# ============================================================

def stance_background(
    value,
):

    colors = {

        "HAWKISH":
            (
                "background-color:#e57373;"
                "color:#7f0000;"
                "font-weight:700;"
            ),

        "NEUTRAL_HAWKISH":
            (
                "background-color:#ffcdd2;"
                "color:#8e2424;"
                "font-weight:650;"
            ),

        "NEUTRAL":
            (
                "background-color:#eeeeee;"
                "color:#424242;"
            ),

        "NEUTRAL_DOVISH":
            (
                "background-color:#c8e6c9;"
                "color:#1b5e20;"
                "font-weight:650;"
            ),

        "DOVISH":
            (
                "background-color:#66bb6a;"
                "color:#0b4f12;"
                "font-weight:700;"
            ),

        "INSUFFICIENT":
            (
                "background-color:#f8f8f8;"
                "color:#999999;"
            ),

        "UNKNOWN":
            (
                "background-color:#f8f8f8;"
                "color:#999999;"
            ),
    }

    return colors.get(
        safe_text(
            value
        ).upper(),
        "",
    )


# ============================================================
# FINAL EVENT MEMBER MAP
# ============================================================

def build_final_member_map(
    events,
):

    member_map = {}

    for event in events:

        member = (
            event.get(
                "member_name_en"
            )
        )

        if (
            not member
            or
            member
            in HIDDEN_APP_MEMBERS
        ):

            continue

        if (
            member
            not in member_map
        ):

            member_map[
                member
            ] = event

    return member_map


# ============================================================
# SPEAKER SUMMARY
# ============================================================

def build_speaker_summary(
    events,
    full_df,
):

    member_map = (
        build_final_member_map(
            events
        )
    )

    rows = []

    for speaker in sorted(
        member_map.keys()
    ):

        event = (
            member_map[
                speaker
            ]
        )

        full_member_df = (
            full_df[
                full_df[
                    "Speaker"
                ]
                == speaker
            ]
        )

        if not full_member_df.empty:

            member_row = (
                full_member_df.iloc[
                    0
                ]
            )

        else:

            member_row = {}

        if (
            isinstance(
                member_row,
                pd.Series,
            )
        ):

            is_voter = (
                voter_flag(
                    member_row
                )
            )

            speaker_display = (
                member_display_name(
                    speaker,
                    member_row,
                )
            )

        else:

            is_voter = False
            speaker_display = (
                f"{speaker} (당연직)"
            )

        fed = (
            safe_text(
                event.get(
                    "member_fed"
                )
                or
                event.get(
                    "fed"
                )
            )
        )

        if (
            not fed
            and
            not full_member_df.empty
        ):

            fed = (
                safe_text(
                    first_nonempty(
                        full_member_df[
                            "Fed"
                        ]
                    )
                )
            )

        rows.append({

            "Speaker":
                speaker,

            "Speaker_Display":
                speaker_display,

            "Fed":
                fed,

            "Is_Voter":
                is_voter,

            # ---------------------------------------------
            # MODEL
            # ---------------------------------------------

            "Model_Stance":
                event.get(
                    "model_stance"
                )
                or
                "INSUFFICIENT",

            "Model_Score":
                safe_float(
                    event.get(
                        "model_score"
                    )
                ),

            "Model_Confidence":
                event.get(
                    "model_confidence"
                )
                or
                "INSUFFICIENT",

            "Model_Evidence_Count":
                event.get(
                    "model_evidence_count"
                )
                or
                0,

            # ---------------------------------------------
            # RECENT
            # ---------------------------------------------

            "Recent_Signal":
                event.get(
                    "recent_signal"
                )
                or
                "INSUFFICIENT",

            "Recent_Score":
                safe_float(
                    event.get(
                        "recent_signal_score"
                    )
                ),

            "Recent_Confidence":
                event.get(
                    "recent_signal_confidence"
                )
                or
                "INSUFFICIENT",

            "Aux_Speech_Count":
                event.get(
                    "aux_speech_count"
                )
                or
                0,

            "Recent_News_Count":
                event.get(
                    "recent_news_usable_count"
                )
                or
                0,

            # ---------------------------------------------
            # FINAL
            # ---------------------------------------------

            "Final_Stance":
                event.get(
                    "final_stance"
                )
                or
                "INSUFFICIENT",

            "Final_Score":
                safe_float(
                    event.get(
                        "final_score"
                    )
                ),

            "Final_Confidence":
                event.get(
                    "final_confidence"
                )
                or
                "INSUFFICIENT",

            "Final_Model_Weight":
                safe_float(
                    event.get(
                        "final_model_weight"
                    )
                ),

            "Final_Recent_Weight":
                safe_float(
                    event.get(
                        "final_recent_weight"
                    )
                ),

            "Final_Conflict":
                bool(
                    event.get(
                        "final_signal_conflict",
                        False,
                    )
                ),

            "Final_Reason":
                safe_text(
                    event.get(
                        "final_reason"
                    )
                ),

            # ---------------------------------------------
            # MOMENTUM
            # ---------------------------------------------

            "Momentum_Label":
                event.get(
                    "momentum_label"
                )
                or
                "INSUFFICIENT",

            "Momentum_Score":
                safe_float(
                    event.get(
                        "momentum_score"
                    )
                ),

            "Momentum_Recent_Avg":
                safe_float(
                    event.get(
                        "momentum_recent_avg"
                    )
                ),

            "Momentum_Previous_Avg":
                safe_float(
                    event.get(
                        "momentum_previous_avg"
                    )
                ),

            "Momentum_Confidence":
                event.get(
                    "momentum_confidence"
                )
                or
                "INSUFFICIENT",
        })

    result = (
        pd.DataFrame(
            rows
        )
    )

    if result.empty:
        return result

    return (
        result.sort_values(
            [
                "Final_Score",
                "Model_Score",
            ],
            ascending=[
                False,
                False,
            ],
            na_position="last",
        )
    )


# ============================================================
# NEWS UPDATED HELPERS
# ============================================================

def parse_news_date(
    value,
):

    if not value:
        return None

    try:

        parsed = pd.to_datetime(
            value,
            errors="coerce",
            utc=True,
        )

        if pd.isna(
            parsed
        ):
            return None

        return (
            parsed.tz_convert(
                None
            )
        )

    except Exception:
        return None


def news_stance_display(
    value,
):

    return hd_display(
        value
    )


def build_recent_news(
    events,
    lookback_days=14,
):

    cutoff = (
        pd.Timestamp.now()
        .normalize()
        -
        pd.Timedelta(
            days=lookback_days
        )
    )

    rows = []
    seen = set()
    member_meta = {}

    for event in events:

        member = (
            event.get(
                "member_name_en"
            )
        )

        if (
            not member
            or
            member
            in HIDDEN_APP_MEMBERS
        ):

            continue

        if (
            member
            not in member_meta
        ):

            member_meta[
                member
            ] = {

                "member_name_ko":
                    event.get(
                        "member_name_ko"
                    )
                    or
                    member,

                "member_fed":
                    event.get(
                        "member_fed"
                    )
                    or
                    event.get(
                        "fed"
                    )
                    or
                    "",

                "member_role_ko":
                    event.get(
                        "member_role_ko"
                    )
                    or
                    "",

                # ★ 기존 consensus_label 아님
                "final_stance":
                    event.get(
                        "final_stance"
                    )
                    or
                    "INSUFFICIENT",
            }

        news_articles = (
            event.get(
                "news_articles"
            )
            or
            []
        )

        for article in news_articles:

            published_at = (
                article.get(
                    "published_at"
                )
                or
                article.get(
                    "date"
                )
            )

            published_dt = (
                parse_news_date(
                    published_at
                )
            )

            if published_dt is None:
                continue

            if (
                published_dt.normalize()
                <
                cutoff
            ):

                continue

            url = (
                article.get(
                    "url"
                )
                or
                ""
            )

            title = (
                article.get(
                    "title"
                )
                or
                ""
            )

            identity = (
                url
                or
                (
                    f"{member}|"
                    f"{published_dt}|"
                    f"{title}"
                )
            )

            if identity in seen:
                continue

            seen.add(
                identity
            )

            source = (
                article.get(
                    "source"
                )
                or
                ""
            )

            description = (
                article.get(
                    "description"
                )
                or
                ""
            )

            # News 자체 성향이 아니라 최종 판단
            stance = (
                member_meta[
                    member
                ][
                    "final_stance"
                ]
            )

            summary = (
                description.strip()
                if description
                else title.strip()
            )

            if (
                summary
                ==
                title
            ):

                summary = ""

            if len(
                summary
            ) > 320:

                summary = (
                    summary[
                        :317
                    ]
                    +
                    "..."
                )

            rows.append({

                "member":
                    member,

                "member_ko":
                    member_meta[
                        member
                    ][
                        "member_name_ko"
                    ],

                "fed":
                    member_meta[
                        member
                    ][
                        "member_fed"
                    ],

                "role":
                    member_meta[
                        member
                    ][
                        "member_role_ko"
                    ],

                "published_at":
                    published_dt,

                "source":
                    source,

                "title":
                    title,

                "summary":
                    summary,

                "stance":
                    stance,

                "url":
                    url,
            })

    rows.sort(
        key=lambda item:
            item[
                "published_at"
            ],
        reverse=True,
    )

    return rows


# ============================================================
# LOAD DATA
# ============================================================

latest_file = (
    get_latest_excel()
)

if latest_file is None:

    st.warning(
        "분석 결과가 없습니다."
    )

    st.stop()


df = (
    load_excel(
        str(
            latest_file
        ),
        latest_file
        .stat()
        .st_mtime,
    )
)

df[
    "Speaker"
] = (
    df[
        "Speaker"
    ]
    .fillna("")
    .astype(str)
    .str.strip()
)


# ============================================================
# APP에서는 HIDDEN MEMBER 제외
# ============================================================

fomc_df = (
    df[
        ~df[
            "Speaker"
        ]
        .isin(
            HIDDEN_APP_MEMBERS
        )
    ]
    .copy()
)


# ============================================================
# FINAL EVENTS
# ============================================================

if (
    FINAL_EVENTS_PATH.exists()
):

    final_events = (
        load_final_events(
            str(
                FINAL_EVENTS_PATH
            ),
            FINAL_EVENTS_PATH
            .stat()
            .st_mtime,
        )
    )

else:

    final_events = []


# ============================================================
# HEADER
# ============================================================

total_articles = len(
    fomc_df
)

high_articles = int(
    (
        fomc_df[
            "Relevance"
        ]
        == "HIGH"
    ).sum()
)

hawk_articles = int(
    fomc_df[
        "Hawk_Dove"
    ]
    .isin([
        "HAWKISH",
        "NEUTRAL_HAWKISH",
    ])
    .sum()
)

dove_articles = int(
    fomc_df[
        "Hawk_Dove"
    ]
    .isin([
        "DOVISH",
        "NEUTRAL_DOVISH",
    ])
    .sum()
)


st.markdown(
    (
        '<div class="main-title">'
        '🏦 Fed Speaker Monitor'
        '</div>'
    ),
    unsafe_allow_html=True,
)


header_html = (
    '<div class="header-row">'
    '<div class="sub-title">'
    'Federal Reserve 발언 · Model Stance · Recent Signal Monitor'
    '</div>'
    '<div class="top-stats">'
    f'전체 발언 <b>{total_articles}</b>'
    f' &nbsp;·&nbsp; HIGH <b>{high_articles}</b>'
    f' &nbsp;·&nbsp; Hawk 계열 <b>{hawk_articles}</b>'
    f' &nbsp;·&nbsp; Dove 계열 <b>{dove_articles}</b>'
    '</div>'
    '</div>'
)

st.markdown(
    header_html,
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title(
        "Filters"
    )

    st.caption(
        f"Latest: {latest_file.name}"
    )

    if st.button(
        "🔄 데이터 업데이트",
        use_container_width=True,
        type="primary",
    ):

        with st.spinner(
            "Model Stance · Recent Signal · Final Stance를 "
            "재계산하고 있습니다..."
        ):

            result = (
                run_pipeline()
            )

        if (
            result.returncode
            == 0
        ):

            st.success(
                "업데이트 완료"
            )

            st.cache_data.clear()

            st.rerun()

        else:

            st.error(
                "업데이트 실패"
            )

            st.code(
                result.stderr
                or
                result.stdout
            )

    st.divider()

    selected_relevance = (
        st.multiselect(
            "FOMC Relevance",
            [
                "HIGH",
                "MEDIUM",
                "LOW",
            ],
            default=[
                "HIGH",
                "MEDIUM",
            ],
        )
    )

    selected_hd = (
        st.multiselect(
            "Hawk / Dove",
            [
                "HAWKISH",
                "NEUTRAL_HAWKISH",
                "NEUTRAL",
                "NEUTRAL_DOVISH",
                "DOVISH",
            ],
            default=[
                "HAWKISH",
                "NEUTRAL_HAWKISH",
                "NEUTRAL",
                "NEUTRAL_DOVISH",
                "DOVISH",
            ],
        )
    )

    speaker_options = sorted(
        [
            value
            for value
            in fomc_df[
                "Speaker"
            ]
            .dropna()
            .unique()
            .tolist()
            if value
        ]
    )

    selected_speakers = (
        st.multiselect(
            "Speaker",
            speaker_options,
        )
    )

    keyword = (
        st.text_input(
            "Search"
        )
    )


# ============================================================
# FILTER - ARTICLE TAB용
# ============================================================

filtered = (
    fomc_df.copy()
)

if selected_relevance:

    filtered = (
        filtered[
            filtered[
                "Relevance"
            ]
            .isin(
                selected_relevance
            )
        ]
    )

if selected_hd:

    filtered = (
        filtered[
            filtered[
                "Hawk_Dove"
            ]
            .isin(
                selected_hd
            )
        ]
    )

if selected_speakers:

    filtered = (
        filtered[
            filtered[
                "Speaker"
            ]
            .isin(
                selected_speakers
            )
        ]
    )

if keyword:

    mask = (
        filtered[
            "Title"
        ]
        .fillna("")
        .str.contains(
            keyword,
            case=False,
            regex=False,
        )
        |
        filtered[
            "Speaker"
        ]
        .fillna("")
        .str.contains(
            keyword,
            case=False,
            regex=False,
        )
    )

    filtered = (
        filtered[
            mask
        ]
    )


# ============================================================
# TABS
# ============================================================

(
    tab1,
    tab2,
    tab3,
    tab4,
) = st.tabs(
    [
        "👤 Speakers",
        "𝕏 SNS",
        "📰 News Updated",
        "📋 All Data",
    ]
)


# ============================================================
# TAB 1 - SPEAKERS
# ============================================================

with tab1:

    st.subheader(
        "FOMC Member Stance"
    )

    if not final_events:

        st.warning(
            "final_events.json이 없습니다. "
            "merge_pipeline.py를 먼저 실행해주세요."
        )

    else:

        speaker_df = (
            build_speaker_summary(
                final_events,
                fomc_df,
            )
        )

        # Sidebar Speaker 선택은 Speaker table에도 반영
        if selected_speakers:

            speaker_df = (
                speaker_df[
                    speaker_df[
                        "Speaker"
                    ]
                    .isin(
                        selected_speakers
                    )
                ]
            )

        if speaker_df.empty:

            st.info(
                "표시할 위원 데이터가 없습니다."
            )

        else:

            # =================================================
            # MAIN TABLE
            # =================================================

            display_df = (
                speaker_df[
                    [
                        "Speaker_Display",
                        "Fed",
                        "Model_Stance",
                        "Recent_Signal",
                        "Final_Stance",
                        "Final_Confidence",
                        "Momentum_Label",
                        "Is_Voter",
                    ]
                ]
                .copy()
            )

            display_df[
                "Momentum"
            ] = (
                display_df[
                    "Momentum_Label"
                ]
                .apply(
                    momentum_display
                )
            )

            display_df[
                "Final_Confidence"
            ] = (
                display_df[
                    "Final_Confidence"
                ]
                .apply(
                    confidence_display
                )
            )

            display_df = (
                display_df.rename(
                    columns={

                        "Speaker_Display":
                            "위원",

                        "Fed":
                            "소속",

                        "Model_Stance":
                            "Model Stance",

                        "Recent_Signal":
                            "Recent Signal",

                        "Final_Stance":
                            "최종 판단",

                        "Final_Confidence":
                            "신뢰도",
                    }
                )
            )

            display_df = (
                display_df[
                    [
                        "위원",
                        "소속",
                        "Model Stance",
                        "Recent Signal",
                        "최종 판단",
                        "신뢰도",
                        "Momentum",
                        "Is_Voter",
                    ]
                ]
            )


            def bold_voter_row(
                row,
            ):

                if bool(
                    row.get(
                        "Is_Voter",
                        False,
                    )
                ):

                    return [
                        "font-weight:700;"
                        for _ in row
                    ]

                return [
                    ""
                    for _ in row
                ]


            styled_df = (
                display_df
                .style
                .apply(
                    bold_voter_row,
                    axis=1,
                )
                .map(
                    stance_background,
                    subset=[
                        "Model Stance",
                        "Recent Signal",
                        "최종 판단",
                    ],
                )
                .hide(
                    subset=[
                        "Is_Voter"
                    ],
                    axis="columns",
                )
            )

            st.caption(
                "* 현재 투표권이 있는 위원은 Bold체로 표시했습니다."
            )

            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                height=570,

                column_config={

                    "위원":
                        st.column_config.TextColumn(
                            width="medium",
                        ),

                    "소속":
                        st.column_config.TextColumn(
                            width="small",
                        ),

                    "Model Stance":
                        st.column_config.TextColumn(
                            width="medium",
                        ),

                    "Recent Signal":
                        st.column_config.TextColumn(
                            width="medium",
                        ),

                    "최종 판단":
                        st.column_config.TextColumn(
                            width="medium",
                        ),

                    "신뢰도":
                        st.column_config.TextColumn(
                            width="small",
                        ),

                    "Momentum":
                        st.column_config.TextColumn(
                            width="medium",
                        ),
                },
            )

            # =================================================
            # MEMBER DETAIL
            # =================================================

            st.divider()

            st.subheader(
                "위원별 상세"
            )

            selected_member = (
                st.selectbox(
                    "위원 선택",
                    speaker_df[
                        "Speaker"
                    ]
                    .tolist(),
                )
            )

            member_summary = (
                speaker_df[
                    speaker_df[
                        "Speaker"
                    ]
                    == selected_member
                ]
                .iloc[
                    0
                ]
            )

            c1, c2, c3, c4, c5 = (
                st.columns(
                    5
                )
            )

            c1.metric(
                "Model Stance",
                hd_display(
                    member_summary[
                        "Model_Stance"
                    ]
                ),
            )

            c2.metric(
                "Recent Signal",
                hd_display(
                    member_summary[
                        "Recent_Signal"
                    ]
                ),
            )

            c3.metric(
                "최종 판단",
                hd_display(
                    member_summary[
                        "Final_Stance"
                    ]
                ),
            )

            c4.metric(
                "신뢰도",
                confidence_display(
                    member_summary[
                        "Final_Confidence"
                    ]
                ),
            )

            c5.metric(
                "Momentum",
                momentum_display(
                    member_summary[
                        "Momentum_Label"
                    ]
                ),
            )

            # =================================================
            # MODEL / RECENT / FINAL DETAILS
            # =================================================

            with st.expander(
                "성향 계산 상세"
            ):

                d1, d2, d3 = (
                    st.columns(
                        3
                    )
                )

                model_score = (
                    member_summary[
                        "Model_Score"
                    ]
                )

                recent_score = (
                    member_summary[
                        "Recent_Score"
                    ]
                )

                final_score = (
                    member_summary[
                        "Final_Score"
                    ]
                )

                d1.metric(
                    "Model Score",
                    (
                        "-"
                        if pd.isna(
                            model_score
                        )
                        else
                        f"{model_score:+.2f}"
                    ),
                )

                d2.metric(
                    "Recent Score",
                    (
                        "-"
                        if pd.isna(
                            recent_score
                        )
                        else
                        f"{recent_score:+.2f}"
                    ),
                )

                d3.metric(
                    "Final Score",
                    (
                        "-"
                        if pd.isna(
                            final_score
                        )
                        else
                        f"{final_score:+.2f}"
                    ),
                )

                st.caption(
                    f"Model Evidence "
                    f"{int(member_summary['Model_Evidence_Count'])}건 "
                    f"· Model Confidence "
                    f"{member_summary['Model_Confidence']} "
                    f"· Recent Confidence "
                    f"{member_summary['Recent_Confidence']}"
                )

                st.caption(
                    f"Recent Signal 근거: "
                    f"보조발언 {int(member_summary['Aux_Speech_Count'])}건 "
                    f"+ 사용가능 뉴스 {int(member_summary['Recent_News_Count'])}건"
                )

                model_weight = (
                    member_summary[
                        "Final_Model_Weight"
                    ]
                )

                recent_weight = (
                    member_summary[
                        "Final_Recent_Weight"
                    ]
                )

                if (
                    model_weight is not None
                    and
                    recent_weight is not None
                ):

                    st.caption(
                        f"최종 가중치: "
                        f"Model {model_weight * 100:.0f}% "
                        f"/ Recent {recent_weight * 100:.0f}%"
                    )

                if (
                    member_summary[
                        "Final_Conflict"
                    ]
                ):

                    st.warning(
                        "Model Stance와 Recent Signal의 "
                        "방향이 서로 충돌합니다."
                    )

                final_reason = (
                    member_summary[
                        "Final_Reason"
                    ]
                )

                if final_reason:

                    st.caption(
                        f"판단 근거: {final_reason}"
                    )

            # =================================================
            # MOMENTUM DETAIL
            # =================================================

            with st.expander(
                "Momentum 계산 상세"
            ):

                m1, m2, m3 = (
                    st.columns(
                        3
                    )
                )

                recent_avg = (
                    member_summary[
                        "Momentum_Recent_Avg"
                    ]
                )

                previous_avg = (
                    member_summary[
                        "Momentum_Previous_Avg"
                    ]
                )

                momentum_score = (
                    member_summary[
                        "Momentum_Score"
                    ]
                )

                m1.metric(
                    "최근 구간 평균",
                    (
                        "-"
                        if pd.isna(
                            recent_avg
                        )
                        else
                        f"{recent_avg:.2f}"
                    ),
                )

                m2.metric(
                    "직전 구간 평균",
                    (
                        "-"
                        if pd.isna(
                            previous_avg
                        )
                        else
                        f"{previous_avg:.2f}"
                    ),
                )

                m3.metric(
                    "Momentum Score",
                    (
                        "-"
                        if pd.isna(
                            momentum_score
                        )
                        else
                        f"{momentum_score:+.2f}"
                    ),
                )

                st.caption(
                    "Momentum은 최근 중요발언과 직전 중요발언을 "
                    "비교해 방향 변화를 측정하는 독립 지표이며 "
                    "Final Stance 계산에는 직접 사용하지 않습니다."
                )

            # =================================================
            # ARTICLE DETAIL
            # =================================================

            member_articles = (
                fomc_df[
                    fomc_df[
                        "Speaker"
                    ]
                    == selected_member
                ]
                .sort_values(
                    "Date",
                    ascending=False,
                )
            )

            if not member_articles.empty:

                st.markdown(
                    "#### 개별 발언"
                )

                options = {}

                for idx, row in (
                    member_articles.iterrows()
                ):

                    date = (
                        row[
                            "Date"
                        ]
                        .strftime(
                            "%Y-%m-%d"
                        )
                        if pd.notna(
                            row[
                                "Date"
                            ]
                        )
                        else "-"
                    )

                    label = (
                        f"{date} | "
                        f"{safe_text(row['Title'])}"
                    )

                    options[
                        label
                    ] = idx

                selected_label = (
                    st.selectbox(
                        "발언 선택",
                        list(
                            options.keys()
                        ),
                    )
                )

                selected_row = (
                    member_articles.loc[
                        options[
                            selected_label
                        ]
                    ]
                )

                st.markdown(
                    f"### "
                    f"{safe_text(selected_row['Title'])}"
                )

                r1, r2, r3 = (
                    st.columns(
                        3
                    )
                )

                r1.metric(
                    "개별 발언 성향",
                    hd_display(
                        selected_row[
                            "Hawk_Dove"
                        ]
                    ),
                )

                r2.metric(
                    "H/D Score",
                    selected_row[
                        "Hawk_Dove_Score"
                    ],
                )

                r3.metric(
                    "Relevance",
                    selected_row[
                        "Relevance"
                    ],
                )

                url = safe_text(
                    selected_row[
                        "URL"
                    ]
                )

                if url:

                    st.link_button(
                        "원문 보기 ↗",
                        url,
                    )

st.markdown(
    """
    <div class="model-box">

    <b>Model Stance</b> ·
    신뢰도가 높은 직접 통화정책 발언을 기반으로 기본 성향을 추정합니다.
    Official 신뢰도 HIGH 발언과 검증된 정책발언(뉴스출처)을 사용하며 최근 최대 5개에
    완만한 최신성 가중치를 적용합니다.<br>

    <b>Recent Signal</b> ·
    최근 90일 동안 Model에 이미 사용된 발언은 제외하고,
    모델 신뢰도 MEDIUM/LOW 보조발언과 뉴스 보도를 이용해 최근 방향을 확인합니다.<br>

    <b>최종 판단</b> ·
    Model Stance를 Anchor로 두고 Recent Signal을 보정 신호로 제한적으로 반영합니다.
    Model Confidence가 높을수록 Model 비중이 높으며,
    Recent Signal의 신뢰도가 낮으면 보정 비중을 추가로 축소합니다.
    Recent Signal이 Insufficient이면 Model Stance를 그대로 유지합니다.<br>

    <b>Momentum</b> ·
    중요 발언의 최근 구간과 직전 구간을 비교해
    이전보다 매파적·비둘기파적으로 이동하는지를 별도로 나타냅니다.

    <br>
    <span style="font-size:11px; color:#8a8a8a;">
    ※ 참고 · 위 성향은 공식 발언 및 뉴스 데이터를 기반으로 AI가 추정한 참고 지표이며,
    실제 정책 판단 및 향후 투표 방향과 다를 수 있습니다.
    </span>
    </div>
    """,
    unsafe_allow_html=True,
)
# ============================================================
# TAB 2 - SNS
# ============================================================

with tab2:

    st.subheader(
        "𝕏 Latest Posts"
    )

    st.markdown(
        (
            '<div class="sns-note">'
            'fed_members.csv에 등록된 X 계정의 '
            '<b>가장 최근 original post 1개</b>를 표시합니다. '
            '기관계정은 해당 연은/연준 공식 X의 최신 게시물입니다. '
            'SNS 데이터는 Model Stance · Recent Signal · '
            'Final Stance 계산에는 반영하지 않습니다.'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    cache_updated_at = (
        get_x_cache_updated_at()
    )

    left, right = (
        st.columns(
            [5, 1]
        )
    )

    with left:

        if cache_updated_at:

            st.caption(
                f"X Cache Updated: "
                f"{cache_updated_at}"
            )

        else:

            st.caption(
                "저장된 X 캐시가 없습니다."
            )

    with right:

        update_clicked = (
            st.button(
                "🔄 X 업데이트",
                use_container_width=True,
            )
        )

    if update_clicked:

        if not os.getenv(
            "X_BEARER_TOKEN"
        ):

            st.error(
                "X_BEARER_TOKEN이 설정되어 있지 않습니다."
            )

        else:

            with st.spinner(
                "최신 X 게시물을 가져오고 있습니다..."
            ):

                try:

                    update_x_cache()

                    st.success(
                        "X 게시물 업데이트 완료"
                    )

                    st.rerun()

                except Exception as exc:

                    st.error(
                        f"X 업데이트 실패: "
                        f"{exc}"
                    )

    sns_df = (
        load_x_cache()
    )

    if sns_df.empty:

        st.info(
            "저장된 X 게시물이 없습니다. "
            "'X 업데이트' 버튼을 눌러 데이터를 생성해주세요."
        )

    else:

        sns_view = (
            sns_df.copy()
        )

        if (
            "member_name_en"
            in sns_view.columns
        ):

            sns_view = (
                sns_view[
                    ~sns_view[
                        "member_name_en"
                    ]
                    .isin(
                        HIDDEN_APP_MEMBERS
                    )
                ]
            )

        sns_view[
            "x_published_at"
        ] = pd.to_datetime(
            sns_view[
                "x_published_at"
            ],
            errors="coerce",
            utc=True,
        )

        sns_view = (
            sns_view.sort_values(
                "x_published_at",
                ascending=False,
                na_position="last",
            )
            .reset_index(
                drop=True
            )
        )

        with st.container(
            height=650,
            border=True,
        ):

            for _, row in (
                sns_view.iterrows()
            ):

                member = safe_text(
                    row.get(
                        "member_name_en"
                    )
                )

                fed = safe_text(
                    row.get(
                        "fed"
                    )
                )

                handle = safe_text(
                    row.get(
                        "x_handle"
                    )
                )

                post_text = safe_text(
                    row.get(
                        "x_text"
                    )
                )

                post_url = safe_text(
                    row.get(
                        "x_url"
                    )
                )

                published_at = (
                    row.get(
                        "x_published_at"
                    )
                )

                if (
                    handle
                    in PERSONAL_X_HANDLES
                ):

                    account_type = (
                        "개인계정"
                    )

                    account_icon = (
                        "👤"
                    )

                else:

                    account_type = (
                        "기관계정"
                    )

                    account_icon = (
                        "🏛️"
                    )

                if pd.notna(
                    published_at
                ):

                    date_text = (
                        published_at
                        .strftime(
                            "%Y-%m-%d"
                        )
                    )

                else:

                    date_text = "-"

                st.markdown(
                    f"### {member}"
                )

                st.caption(
                    f"{fed} · "
                    f"@{handle} · "
                    f"{account_icon} "
                    f"{account_type} · "
                    f"{date_text}"
                )

                if post_text:

                    st.markdown(
                        post_text
                    )

                else:

                    st.caption(
                        "게시물 없음"
                    )

                if post_url:

                    st.link_button(
                        "𝕏 원문 보기",
                        post_url,
                    )

                st.divider()

        st.caption(
            "* 기관계정은 해당 위원의 개인 게시물이 아니라 "
            "소속 연은 또는 Federal Reserve 공식 계정의 최신 게시물입니다. "
            "Reply와 Retweet은 제외하며 게시물이 오래되었더라도 "
            "해당 계정의 가장 최근 게시물을 표시합니다."
        )


# ============================================================
# TAB 3 - NEWS UPDATED
# ============================================================

with tab3:

    st.subheader(
        "📰 News Updated"
    )

    st.markdown(
        (
            '<div class="news-note">'
            '<b>최근 14일</b> 동안 수집된 연준위원 관련 뉴스입니다. '
            '각 뉴스 옆 성향은 해당 기사 자체의 성향이 아니라 '
            '<b>현재 Final Stance</b>를 표시합니다.'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    if not final_events:

        st.info(
            "final_events.json이 없습니다. "
            "merge_pipeline.py를 먼저 실행해주세요."
        )

    else:

        recent_news = (
            build_recent_news(
                final_events,
                lookback_days=(
                    NEWS_UPDATED_LOOKBACK_DAYS
                ),
            )
        )

        if not recent_news:

            st.info(
                "최근 14일간 표시할 뉴스가 없습니다."
            )

        else:

            news_members = sorted(
                {
                    item[
                        "member_ko"
                    ]
                    for item
                    in recent_news
                }
            )

            top_left, top_right = (
                st.columns(
                    [4, 1]
                )
            )

            with top_left:

                selected_news_members = (
                    st.multiselect(
                        "위원 필터",
                        news_members,
                        placeholder=(
                            "전체 위원"
                        ),
                    )
                )

            with top_right:

                st.markdown(
                    f"""
                    <div style="text-align:right;">
                        <div style="font-size:12px; color:#6b7280;">
                            최근 14일
                        </div>
                        <div style="font-size:20px; font-weight:700;">
                            {len(recent_news)}건
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if selected_news_members:

                recent_news = [
                    item
                    for item
                    in recent_news
                    if item[
                        "member_ko"
                    ]
                    in selected_news_members
                ]

            with st.container(
                height=500,
                border=True,
            ):

                for item in recent_news:

                    published_text = (
                        item[
                            "published_at"
                        ]
                        .strftime(
                            "%Y-%m-%d"
                        )
                    )

                    member_text = (
                        f"{item['member_ko']} "
                        f"({item['member']})"
                    )

                    affiliation = (
                        item[
                            "fed"
                        ]
                        or
                        item[
                            "role"
                        ]
                        or
                        "-"
                    )

                    stance_text = (
                        news_stance_display(
                            item[
                                "stance"
                            ]
                        )
                    )

                    source_text = (
                        item[
                            "source"
                        ]
                        or
                        "News"
                    )

                    st.markdown(
                        (
                            '<div class="news-card">'
                            f'<div class="news-date">'
                            f'{published_text} · {source_text}'
                            f'</div>'
                            f'<div class="news-member">'
                            f'{member_text}'
                            f'</div>'
                            f'<div class="news-meta">'
                            f'{affiliation}'
                            f' &nbsp;·&nbsp; '
                            f'최종 판단: {stance_text}'
                            f'</div>'
                            f'<div class="news-title">'
                            f'{safe_text(item["title"])}'
                            f'</div>'
                        ),
                        unsafe_allow_html=True,
                    )

                    if (
                        item[
                            "summary"
                        ]
                    ):

                        st.markdown(
                            (
                                '<div class="news-summary">'
                                f'{safe_text(item["summary"])}'
                                '</div>'
                            ),
                            unsafe_allow_html=True,
                        )

                    if (
                        item[
                            "url"
                        ]
                    ):

                        st.link_button(
                            "기사 보기 ↗",
                            item[
                                "url"
                            ],
                        )

                    st.divider()


# ============================================================
# TAB 4 - ALL DATA
# ============================================================

with tab4:

    st.subheader(
        "All Articles"
    )

    columns = [
        "Date",
        "Speaker",
        "Source",
        "Title",
        "Relevance",
        "Relevance_Score",
        "Hawk_Dove",
        "Hawk_Dove_Score",
        "Topics",
        "URL",
    ]

    columns = [
        column
        for column
        in columns
        if column
        in filtered.columns
    ]

    st.dataframe(
        filtered[
            columns
        ],
        use_container_width=True,
        hide_index=True,

        column_config={

            "Date":
                st.column_config.DateColumn(
                    format="YYYY-MM-DD",
                ),

            "URL":
                st.column_config.LinkColumn(
                    display_text="Open",
                ),
        },
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

updated_at = (
    datetime.fromtimestamp(
        latest_file
        .stat()
        .st_mtime
    )
    .strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)

valid_dates = (
    fomc_df[
        "Date"
    ]
    .dropna()
)

if len(
    valid_dates
):

    data_coverage = (
        f"{valid_dates.min().strftime('%Y-%m-%d')}"
        " ~ "
        f"{valid_dates.max().strftime('%Y-%m-%d')}"
    )

else:

    data_coverage = "-"

st.caption(
    f"Data coverage: {data_coverage} · "
    f"Updated: {updated_at} · "
    f"Source: {latest_file.name}"
)