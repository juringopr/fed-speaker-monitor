# app.py

from pathlib import Path
from datetime import datetime
import subprocess
import sys

import pandas as pd
import streamlit as st


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

PIPELINE_FILE = (
    PROJECT_ROOT
    / "test_processors.py"
)

CURRENT_STANCE_N = 5


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
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.3rem;
        padding-bottom: 3rem;
    }

    .main-title {
        font-size: 2.1rem;
        font-weight: 750;
        margin-bottom: 0.1rem;
    }

    .sub-title {
        color: #666666;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
    }

    .section-note {
        padding: 14px 16px;
        border-radius: 10px;
        background: #f7f8fa;
        border: 1px solid #e6e8eb;
        margin-bottom: 16px;
    }

    .small-text {
        color: #6b7280;
        font-size: 0.85rem;
    }

    div[data-testid="stMetric"] {
        border: 1px solid #ececec;
        padding: 12px;
        border-radius: 12px;
        background: white;
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
        key=lambda path: (
            path.stat().st_mtime
        ),
    )


# ============================================================
# LOAD DATA
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

    df = pd.read_excel(
        path,
        sheet_name="ALL",
    )

    if "Date" in df.columns:

        df["Date"] = pd.to_datetime(
            df["Date"],
            errors="coerce",
        )

    for column in [
        "Matched",
        "Body_Fetched",
    ]:

        if column in df.columns:

            df[column] = (
                df[column]
                .fillna(False)
                .astype(bool)
            )

    numeric_columns = [
        "Relevance_Score",
        "Hawk_Dove_Score",
        "Hawkish_Score",
        "Dovish_Score",
        "Body_Length",
    ]

    for column in numeric_columns:

        if column not in df.columns:
            continue

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    return df


# ============================================================
# RUN PIPELINE
# ============================================================

def run_pipeline():

    command = [
        sys.executable,
        str(
            PIPELINE_FILE
        ),
    ]

    result = subprocess.run(
        command,
        cwd=str(
            PROJECT_ROOT
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return result


# ============================================================
# SAFE TEXT
# ============================================================

def safe_text(
    value,
):

    if pd.isna(
        value
    ):
        return ""

    return str(
        value
    )


# ============================================================
# LABEL DISPLAY
# ============================================================

def hd_display(
    label
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

        "UNKNOWN":
            "Unknown",
    }

    return mapping.get(
        label,
        label,
    )


def relevance_display(
    label
):

    mapping = {

        "HIGH":
            "🔥 HIGH",

        "MEDIUM":
            "MEDIUM",

        "LOW":
            "LOW",
    }

    return mapping.get(
        label,
        label,
    )


# ============================================================
# CURRENT STANCE
# ============================================================

def current_stance_from_score(
    score
):

    if pd.isna(
        score
    ):
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
# SPEAKER SUMMARY
# ============================================================

def build_speaker_summary(
    df
):
    """
    위원별 현재 성향 계산.

    원칙
    ----------------------------------------------------------
    1. UNMATCHED는 원본 데이터에서 삭제하지 않는다.
    2. Speaker Summary에서는 제외한다.
    3. 현재 성향은 최근 HIGH/MEDIUM 중요 발언 최대 5개
       Hawk_Dove_Score 평균으로 계산한다.
    """

    work_df = (
        df.copy()
    )

    if (
        "Speaker"
        not in work_df.columns
    ):
        return pd.DataFrame()

    work_df["Speaker"] = (
        work_df["Speaker"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # UNMATCHED / 빈 Speaker 제외
    # --------------------------------------------------------

    work_df = (
        work_df[
            (
                work_df["Speaker"] != ""
            )
            &
            (
                work_df["Speaker"]
                .str.upper()
                != "UNMATCHED"
            )
        ]
        .copy()
    )

    rows = []

    speakers = (
        work_df["Speaker"]
        .dropna()
        .unique()
    )

    for speaker in speakers:

        speaker_df = (
            work_df[
                work_df["Speaker"]
                == speaker
            ]
            .copy()
        )

        speaker_df = (
            speaker_df.sort_values(
                "Date",
                ascending=False,
                na_position="last",
            )
        )

        # ----------------------------------------------------
        # 최근 HIGH / MEDIUM
        # ----------------------------------------------------

        important = (
            speaker_df[
                speaker_df["Relevance"]
                .isin(
                    [
                        "HIGH",
                        "MEDIUM",
                    ]
                )
            ]
            .copy()
        )

        if important.empty:

            recent = (
                speaker_df.head(
                    CURRENT_STANCE_N
                )
            )

        else:

            recent = (
                important.head(
                    CURRENT_STANCE_N
                )
            )

        # ----------------------------------------------------
        # CURRENT SCORE
        # ----------------------------------------------------

        scores = pd.to_numeric(
            recent[
                "Hawk_Dove_Score"
            ],
            errors="coerce",
        ).dropna()

        if len(
            scores
        ):

            current_score = (
                scores.mean()
            )

        else:

            current_score = 0.0

        current_stance = (
            current_stance_from_score(
                current_score
            )
        )

        # ----------------------------------------------------
        # LATEST DATE
        # ----------------------------------------------------

        valid_dates = (
            speaker_df[
                "Date"
            ]
            .dropna()
        )

        latest_date = (
            valid_dates.max()
            if len(
                valid_dates
            )
            else pd.NaT
        )

        # ----------------------------------------------------
        # LATEST TITLE
        # ----------------------------------------------------

        latest_title = ""

        if len(
            speaker_df
        ):

            latest_title = (
                speaker_df
                .iloc[0]
                .get(
                    "Title",
                    ""
                )
            )

        # ----------------------------------------------------
        # FED
        # ----------------------------------------------------

        fed = ""

        if (
            "Fed"
            in speaker_df.columns
        ):

            fed_values = (
                speaker_df[
                    "Fed"
                ]
                .dropna()
            )

            if len(
                fed_values
            ):

                fed = (
                    fed_values.iloc[0]
                )

        if not fed:

            source_values = (
                speaker_df[
                    "Source"
                ]
                .dropna()
            )

            if len(
                source_values
            ):

                fed = (
                    source_values.iloc[0]
                )

        # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------

        role = ""

        if (
            "Role"
            in speaker_df.columns
        ):

            role_values = (
                speaker_df[
                    "Role"
                ]
                .dropna()
            )

            if len(
                role_values
            ):

                role = (
                    role_values.iloc[0]
                )

        rows.append({

            "Speaker":
                speaker,

            "Role":
                role,

            "Fed":
                fed,

            "Current_Stance":
                current_stance,

            "Current_Score":
                round(
                    float(
                        current_score
                    ),
                    2,
                ),

            "Recent_Sample":
                len(
                    recent
                ),

            "Latest_Date":
                latest_date,

            "Articles":
                len(
                    speaker_df
                ),

            "High":
                int(
                    (
                        speaker_df[
                            "Relevance"
                        ]
                        == "HIGH"
                    ).sum()
                ),

            "Hawkish_Count":
                int(
                    speaker_df[
                        "Hawk_Dove"
                    ]
                    .isin(
                        [
                            "HAWKISH",
                            "NEUTRAL_HAWKISH",
                        ]
                    )
                    .sum()
                ),

            "Neutral_Count":
                int(
                    (
                        speaker_df[
                            "Hawk_Dove"
                        ]
                        == "NEUTRAL"
                    ).sum()
                ),

            "Dovish_Count":
                int(
                    speaker_df[
                        "Hawk_Dove"
                    ]
                    .isin(
                        [
                            "DOVISH",
                            "NEUTRAL_DOVISH",
                        ]
                    )
                    .sum()
                ),

            "Latest_Remark":
                latest_title,
        })

    result = pd.DataFrame(
        rows
    )

    if result.empty:
        return result

    result = (
        result.sort_values(
            [
                "Current_Score",
                "Latest_Date",
            ],
            ascending=[
                False,
                False,
            ],
            na_position="last",
        )
    )

    return result


# ============================================================
# STANCE COLOR
# ============================================================

def stance_background(
    value
):

    colors = {

        "HAWKISH":
            (
                "background-color: #e57373;"
                "color: #7f0000;"
                "font-weight: 700;"
            ),

        "NEUTRAL_HAWKISH":
            (
                "background-color: #ffcdd2;"
                "color: #8e2424;"
                "font-weight: 650;"
            ),

        "NEUTRAL":
            (
                "background-color: #eeeeee;"
                "color: #424242;"
                "font-weight: 550;"
            ),

        "NEUTRAL_DOVISH":
            (
                "background-color: #c8e6c9;"
                "color: #1b5e20;"
                "font-weight: 650;"
            ),

        "DOVISH":
            (
                "background-color: #66bb6a;"
                "color: #0b4f12;"
                "font-weight: 700;"
            ),

        "UNKNOWN":
            (
                "background-color: #f5f5f5;"
                "color: #757575;"
            ),
    }

    return colors.get(
        value,
        ""
    )


# ============================================================
# LOAD LATEST
# ============================================================

latest_file = (
    get_latest_excel()
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🏦 Fed Speaker Monitor</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sub-title">
    Federal Reserve 발언 · FOMC Relevance · Hawk / Dove Monitor
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# NO DATA
# ============================================================

if latest_file is None:

    st.warning(
        "output 폴더에 분석 결과 Excel이 없습니다."
    )

    if st.button(
        "▶ 데이터 수집 시작",
        type="primary",
    ):

        with st.spinner(
            "Fed 발언을 수집하고 분석하고 있습니다..."
        ):

            result = (
                run_pipeline()
            )

        if (
            result.returncode
            == 0
        ):

            st.success(
                "분석 완료"
            )

            st.cache_data.clear()

            st.rerun()

        else:

            st.error(
                "파이프라인 실행 중 오류가 발생했습니다."
            )

            st.code(
                result.stderr
                or result.stdout
            )

    st.stop()


# ============================================================
# LOAD EXCEL
# ============================================================

modified_time = (
    latest_file
    .stat()
    .st_mtime
)

df = load_excel(
    str(
        latest_file
    ),
    modified_time,
)


# ============================================================
# DATA COVERAGE
# ============================================================

valid_dates = (
    df[
        "Date"
    ]
    .dropna()
)

if len(
    valid_dates
):

    data_start = (
        valid_dates.min()
    )

    data_end = (
        valid_dates.max()
    )

    coverage_text = (
        f"{data_start.year}년 "
        f"{data_start.month}월"
        " ~ "
        f"{data_end.year}년 "
        f"{data_end.month}월"
    )

else:

    coverage_text = (
        "날짜 정보 없음"
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

        status = st.status(
            "Fed 데이터를 업데이트하고 있습니다...",
            expanded=True,
        )

        status.write(
            "1. 공식 Fed 사이트 크롤링"
        )

        status.write(
            "2. 발언 본문 수집"
        )

        status.write(
            "3. FOMC relevance 분석"
        )

        status.write(
            "4. Hawk / Dove 문장 분석"
        )

        status.write(
            "5. Excel 저장"
        )

        result = (
            run_pipeline()
        )

        if (
            result.returncode
            == 0
        ):

            status.update(
                label="업데이트 완료",
                state="complete",
                expanded=False,
            )

            st.cache_data.clear()

            st.rerun()

        else:

            status.update(
                label="업데이트 실패",
                state="error",
                expanded=True,
            )

            st.code(
                result.stderr
                or result.stdout
            )

    st.divider()

    # --------------------------------------------------------
    # RELEVANCE
    # --------------------------------------------------------

    relevance_options = [
        value
        for value in [
            "HIGH",
            "MEDIUM",
            "LOW",
        ]
        if value in (
            df[
                "Relevance"
            ]
            .dropna()
            .unique()
        )
    ]

    selected_relevance = (
        st.multiselect(
            "FOMC Relevance",
            relevance_options,
            default=[
                value
                for value in [
                    "HIGH",
                    "MEDIUM",
                ]
                if value
                in relevance_options
            ],
        )
    )

    # --------------------------------------------------------
    # HAWK DOVE
    # --------------------------------------------------------

    hd_order = [
        "HAWKISH",
        "NEUTRAL_HAWKISH",
        "NEUTRAL",
        "NEUTRAL_DOVISH",
        "DOVISH",
    ]

    hd_options = [
        value
        for value in hd_order
        if value in (
            df[
                "Hawk_Dove"
            ]
            .dropna()
            .unique()
        )
    ]

    selected_hd = (
        st.multiselect(
            "Hawk / Dove",
            hd_options,
            default=hd_options,
        )
    )

    # --------------------------------------------------------
    # SPEAKER
    # --------------------------------------------------------

    speaker_options = sorted(
        [
            value
            for value in (
                df[
                    "Speaker"
                ]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )
            if (
                value
                and
                value.upper()
                != "UNMATCHED"
            )
        ]
    )

    selected_speakers = (
        st.multiselect(
            "Speaker",
            speaker_options,
        )
    )

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    source_options = sorted(
        df[
            "Source"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    selected_sources = (
        st.multiselect(
            "Fed / Source",
            source_options,
        )
    )

    # --------------------------------------------------------
    # TOPIC
    # --------------------------------------------------------

    topic_options = [
        "INFLATION",
        "LABOR",
        "RATES",
        "GROWTH",
        "FINANCIAL_CONDITIONS",
        "BALANCE_SHEET",
        "TARIFFS",
        "FX",
    ]

    selected_topics = (
        st.multiselect(
            "Topic",
            topic_options,
        )
    )

    keyword = (
        st.text_input(
            "Search",
            placeholder=(
                "inflation, rate cuts, Powell..."
            ),
        )
    )


# ============================================================
# FILTER
# ============================================================

filtered = (
    df.copy()
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

if selected_sources:

    filtered = (
        filtered[
            filtered[
                "Source"
            ]
            .isin(
                selected_sources
            )
        ]
    )

if selected_topics:

    topic_mask = pd.Series(
        False,
        index=filtered.index,
    )

    for topic in selected_topics:

        topic_mask = (
            topic_mask
            |
            filtered[
                "Topics"
            ]
            .fillna("")
            .str.contains(
                topic,
                case=False,
                regex=False,
            )
        )

    filtered = (
        filtered[
            topic_mask
        ]
    )

if keyword:

    keyword_mask = (

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

        |

        filtered[
            "Topics"
        ]
        .fillna("")
        .str.contains(
            keyword,
            case=False,
            regex=False,
        )

        |

        filtered[
            "Hawk_Evidence"
        ]
        .fillna("")
        .str.contains(
            keyword,
            case=False,
            regex=False,
        )

        |

        filtered[
            "Dove_Evidence"
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
            keyword_mask
        ]
    )


filtered = (
    filtered.sort_values(
        by=[
            "Date",
            "Relevance_Score",
        ],
        ascending=[
            False,
            False,
        ],
        na_position="last",
    )
)


# ============================================================
# TOP KPIs
# ============================================================

col1, col2, col3, col4, col5 = (
    st.columns(5)
)

col1.metric(
    "전체 발언",
    len(
        df
    ),
)

col2.metric(
    "HIGH",
    int(
        (
            df[
                "Relevance"
            ]
            == "HIGH"
        ).sum()
    ),
)

col3.metric(
    "Hawkish 계열",
    int(
        df[
            "Hawk_Dove"
        ]
        .isin(
            [
                "HAWKISH",
                "NEUTRAL_HAWKISH",
            ]
        )
        .sum()
    ),
)

col4.metric(
    "Dovish 계열",
    int(
        df[
            "Hawk_Dove"
        ]
        .isin(
            [
                "DOVISH",
                "NEUTRAL_DOVISH",
            ]
        )
        .sum()
    ),
)

col5.metric(
    "현재 조회",
    len(
        filtered
    ),
)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = (
    st.tabs(
        [
            "👤 Speakers",
            "🔥 Important",
            "📊 Hawk / Dove",
            "📋 All Data",
        ]
    )
)


# ============================================================
# TAB 1 - SPEAKERS
# ============================================================

with tab1:

    st.subheader(
        "FOMC Member Current Stance"
    )

    st.markdown(
        f"""
        <div class="section-note">
        <b>분석 기준기간: {coverage_text}</b><br><br>

        현재 성향은 각 위원의
        <b>최근 HIGH/MEDIUM 중요 발언 최대 {CURRENT_STANCE_N}개</b>의
        Hawk/Dove Score 평균으로 계산합니다.<br><br>

        <b style="color:#b71c1c;">Hawkish</b>
        ←
        Neutral
        →
        <b style="color:#1b5e20;">Dovish</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    speaker_df = (
        build_speaker_summary(
            df
        )
    )

    if not speaker_df.empty:

        hawkish_members = (
            speaker_df[
                speaker_df[
                    "Current_Stance"
                ]
                .isin(
                    [
                        "HAWKISH",
                        "NEUTRAL_HAWKISH",
                    ]
                )
            ]
        )

        neutral_members = (
            speaker_df[
                speaker_df[
                    "Current_Stance"
                ]
                == "NEUTRAL"
            ]
        )

        dovish_members = (
            speaker_df[
                speaker_df[
                    "Current_Stance"
                ]
                .isin(
                    [
                        "DOVISH",
                        "NEUTRAL_DOVISH",
                    ]
                )
            ]
        )

        c1, c2, c3 = (
            st.columns(3)
        )

        c1.metric(
            "🔴 Hawkish 계열",
            len(
                hawkish_members
            ),
        )

        c2.metric(
            "⚪ Neutral",
            len(
                neutral_members
            ),
        )

        c3.metric(
            "🟢 Dovish 계열",
            len(
                dovish_members
            ),
        )

        st.divider()

        st.markdown(
            "### Speaker Summary"
        )

        display_df = (
            speaker_df[
                [
                    "Speaker",
                    "Fed",
                    "Current_Stance",
                    "Current_Score",
                    "Recent_Sample",
                    "Latest_Date",
                    "Articles",
                    "High",
                    "Hawkish_Count",
                    "Neutral_Count",
                    "Dovish_Count",
                    "Latest_Remark",
                ]
            ]
            .copy()
        )

        display_df = (
            display_df.rename(
                columns={

                    "Speaker":
                        "위원",

                    "Fed":
                        "소속",

                    "Current_Stance":
                        "현재 성향",

                    "Current_Score":
                        "현재 Score",

                    "Recent_Sample":
                        "최근 분석건수",

                    "Latest_Date":
                        "최근 발언일",

                    "Articles":
                        "전체 발언",

                    "High":
                        "HIGH",

                    "Hawkish_Count":
                        "Hawk 계열",

                    "Neutral_Count":
                        "Neutral",

                    "Dovish_Count":
                        "Dove 계열",

                    "Latest_Remark":
                        "최근 발언",
                }
            )
        )

        styled_df = (
            display_df
            .style
            .map(
                stance_background,
                subset=[
                    "현재 성향"
                ],
            )
            .format(
                {
                    "현재 Score":
                        "{:.2f}",
                }
            )
        )

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            height=600,
            column_config={

                "최근 발언일":
                    st.column_config.DateColumn(
                        "최근 발언일",
                        format="YYYY-MM-DD",
                    ),

                "위원":
                    st.column_config.TextColumn(
                        "위원",
                        width="medium",
                    ),

                "소속":
                    st.column_config.TextColumn(
                        "소속",
                        width="medium",
                    ),

                "현재 성향":
                    st.column_config.TextColumn(
                        "현재 성향",
                        width="medium",
                    ),

                "현재 Score":
                    st.column_config.NumberColumn(
                        "현재 Score",
                        format="%.2f",
                    ),

                "최근 발언":
                    st.column_config.TextColumn(
                        "최근 발언",
                        width="large",
                    ),
            },
        )

        st.caption(
            """
            현재 Score > 0이면 Hawkish 방향,
            현재 Score < 0이면 Dovish 방향입니다.
            """
        )

        # ====================================================
        # MEMBER DETAIL
        # ====================================================

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
            .iloc[0]
        )

        stance = (
            member_summary[
                "Current_Stance"
            ]
        )

        score = (
            member_summary[
                "Current_Score"
            ]
        )

        mc1, mc2, mc3, mc4 = (
            st.columns(4)
        )

        mc1.metric(
            "현재 성향",
            stance.replace(
                "_",
                " "
            ),
        )

        mc2.metric(
            "Current Score",
            score,
        )

        mc3.metric(
            "전체 발언",
            int(
                member_summary[
                    "Articles"
                ]
            ),
        )

        mc4.metric(
            "HIGH",
            int(
                member_summary[
                    "High"
                ]
            ),
        )

        member_articles = (
            df[
                df[
                    "Speaker"
                ]
                == selected_member
            ]
            .sort_values(
                "Date",
                ascending=False,
                na_position="last",
            )
        )

        detail_columns = [
            column
            for column in [
                "Date",
                "Title",
                "Relevance",
                "Relevance_Score",
                "Hawk_Dove",
                "Hawk_Dove_Score",
                "Topics",
                "URL",
            ]
            if column
            in member_articles.columns
        ]

        st.dataframe(
            member_articles[
                detail_columns
            ],
            use_container_width=True,
            hide_index=True,
            column_config={

                "Date":
                    st.column_config.DateColumn(
                        "Date",
                        format="YYYY-MM-DD",
                    ),

                "URL":
                    st.column_config.LinkColumn(
                        "원문",
                        display_text="Open",
                    ),
            },
        )

    # ========================================================
    # UNMATCHED DEBUG
    # ========================================================

    st.divider()

    unmatched_df = (
        df[
            df[
                "Speaker"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .eq(
                "UNMATCHED"
            )
        ]
        .copy()
    )

    if not unmatched_df.empty:

        with st.expander(
            f"⚠️ UNMATCHED 발언 확인 ({len(unmatched_df)}건)"
        ):

            st.caption(
                """
                인물 매칭에 실패한 자료입니다.
                Speaker Summary에는 포함하지 않지만
                원본 데이터에서는 삭제하지 않습니다.
                """
            )

            unmatched_columns = [
                column
                for column in [
                    "Date",
                    "Source",
                    "Title",
                    "Relevance",
                    "Topics",
                    "URL",
                ]
                if column
                in unmatched_df.columns
            ]

            st.dataframe(
                unmatched_df[
                    unmatched_columns
                ],
                use_container_width=True,
                hide_index=True,
                column_config={

                    "Date":
                        st.column_config.DateColumn(
                            "Date",
                            format="YYYY-MM-DD",
                        ),

                    "URL":
                        st.column_config.LinkColumn(
                            "원문",
                            display_text="Open",
                        ),
                },
            )


# ============================================================
# TAB 2 - IMPORTANT
# ============================================================

with tab2:

    st.subheader(
        "Latest Important Remarks"
    )

    important_filtered = (
        filtered[
            filtered[
                "Relevance"
            ]
            .isin(
                [
                    "HIGH",
                    "MEDIUM",
                ]
            )
        ]
        .copy()
    )

    if important_filtered.empty:

        st.info(
            "조건에 맞는 중요 발언이 없습니다."
        )

    else:

        for _, row in (
            important_filtered
            .head(
                50
            )
            .iterrows()
        ):

            date_value = (
                row.get(
                    "Date"
                )
            )

            if pd.notna(
                date_value
            ):

                date_text = (
                    date_value.strftime(
                        "%Y-%m-%d"
                    )
                )

            else:

                date_text = "-"

            speaker = (
                safe_text(
                    row.get(
                        "Speaker"
                    )
                )
            )

            title = (
                safe_text(
                    row.get(
                        "Title"
                    )
                )
            )

            source = (
                safe_text(
                    row.get(
                        "Source"
                    )
                )
            )

            relevance = (
                safe_text(
                    row.get(
                        "Relevance"
                    )
                )
            )

            hd = (
                safe_text(
                    row.get(
                        "Hawk_Dove"
                    )
                )
            )

            topics = (
                safe_text(
                    row.get(
                        "Topics"
                    )
                )
            )

            url = (
                safe_text(
                    row.get(
                        "URL"
                    )
                )
            )

            st.markdown(
                f"### {speaker} · {hd_display(hd)}"
            )

            st.caption(
                f"{date_text} · "
                f"{source} · "
                f"{relevance_display(relevance)} · "
                f"{topics}"
            )

            st.markdown(
                f"**{title}**"
            )

            c1, c2, c3 = (
                st.columns(
                    [
                        1,
                        1,
                        1,
                    ]
                )
            )

            c1.metric(
                "Relevance",
                row.get(
                    "Relevance_Score",
                    "-"
                ),
            )

            c2.metric(
                "H/D Score",
                row.get(
                    "Hawk_Dove_Score",
                    "-"
                ),
            )

            c3.metric(
                "Confidence",
                row.get(
                    "Confidence",
                    "-"
                ),
            )

            with st.expander(
                "근거 문장 보기"
            ):

                hawk_evidence = (
                    safe_text(
                        row.get(
                            "Hawk_Evidence"
                        )
                    )
                )

                dove_evidence = (
                    safe_text(
                        row.get(
                            "Dove_Evidence"
                        )
                    )
                )

                if hawk_evidence:

                    st.markdown(
                        "**🔴 Hawkish evidence**"
                    )

                    st.write(
                        hawk_evidence
                    )

                if dove_evidence:

                    st.markdown(
                        "**🟢 Dovish evidence**"
                    )

                    st.write(
                        dove_evidence
                    )

                if (
                    not hawk_evidence
                    and
                    not dove_evidence
                ):

                    st.caption(
                        "Hawk / Dove 핵심 근거문장이 없습니다."
                    )

            if url:

                st.link_button(
                    "원문 보기 ↗",
                    url,
                )

            st.divider()


# ============================================================
# TAB 3 - HAWK / DOVE
# ============================================================

with tab3:

    st.subheader(
        "Hawk / Dove Distribution"
    )

    hd_count = (
        df[
            "Hawk_Dove"
        ]
        .value_counts()
        .reindex(
            [
                "HAWKISH",
                "NEUTRAL_HAWKISH",
                "NEUTRAL",
                "NEUTRAL_DOVISH",
                "DOVISH",
            ]
        )
        .fillna(0)
        .astype(int)
    )

    st.bar_chart(
        hd_count
    )

    st.divider()

    st.subheader(
        "Current Speaker Stance Score"
    )

    speaker_summary_for_chart = (
        build_speaker_summary(
            df
        )
    )

    if not speaker_summary_for_chart.empty:

        chart_df = (
            speaker_summary_for_chart[
                [
                    "Speaker",
                    "Current_Score",
                ]
            ]
            .set_index(
                "Speaker"
            )
        )

        st.bar_chart(
            chart_df
        )

    st.caption(
        """
        + 방향은 Hawkish,
        - 방향은 Dovish입니다.
        최근 중요 발언 최대 5건 기준입니다.
        """
    )


# ============================================================
# TAB 4 - ALL DATA
# ============================================================

with tab4:

    st.subheader(
        "All Articles"
    )

    table_columns = [
        "Date",
        "Speaker",
        "Source",
        "Title",
        "Relevance",
        "Relevance_Score",
        "Topics",
        "Hawk_Dove",
        "Hawk_Dove_Score",
        "Confidence",
        "Body_Length",
        "URL",
    ]

    available_columns = [
        column
        for column in table_columns
        if column
        in filtered.columns
    ]

    st.dataframe(
        filtered[
            available_columns
        ],
        use_container_width=True,
        hide_index=True,
        column_config={

            "Date":
                st.column_config.DateColumn(
                    "Date",
                    format="YYYY-MM-DD",
                ),

            "URL":
                st.column_config.LinkColumn(
                    "Original",
                    display_text="Open",
                ),

            "Relevance_Score":
                st.column_config.NumberColumn(
                    "Rel. Score",
                ),

            "Hawk_Dove_Score":
                st.column_config.NumberColumn(
                    "H/D Score",
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

st.caption(
    f"Data coverage: {coverage_text} · "
    f"Updated: {updated_at} · "
    f"Source: {latest_file.name}"
)