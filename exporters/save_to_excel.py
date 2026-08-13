# exporters/save_to_excel.py

from pathlib import Path
from datetime import datetime

import pandas as pd


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "output"
)


# ============================================================
# LABEL ORDER
# ============================================================

HAWK_DOVE_ORDER = {
    "HAWKISH": 5,
    "NEUTRAL_HAWKISH": 4,
    "NEUTRAL": 3,
    "NEUTRAL_DOVISH": 2,
    "DOVISH": 1,
}

RELEVANCE_ORDER = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


# ============================================================
# EVIDENCE CLEAN
# ============================================================

def _evidence_to_text(
    sentences,
    max_items=5,
):

    if not sentences:
        return ""

    cleaned = []

    for sentence in sentences[:max_items]:

        sentence = str(
            sentence
        ).strip()

        if not sentence:
            continue

        cleaned.append(
            sentence
        )

    return "\n".join(
        cleaned
    )


# ============================================================
# TOPIC
# ============================================================

def _topics_to_text(
    topics
):

    if not topics:
        return ""

    if isinstance(
        topics,
        str
    ):
        return topics

    return ", ".join(
        str(topic)
        for topic in topics
    )


# ============================================================
# FLATTEN ONE ARTICLE
# ============================================================

def _flatten_article(
    item
):

    member_name = (
        item.get(
            "member_name_en"
        )
    )

    speaker_raw = (
        item.get(
            "speaker_raw"
        )
    )

    speaker = (
        member_name
        or speaker_raw
        or "UNMATCHED"
    )

    text = (
        item.get(
            "text"
        )
        or ""
    )

    return {

        # ----------------------------------------------------
        # Basic
        # ----------------------------------------------------

        "Date":
            item.get(
                "published_at"
            ),

        "Speaker":
            speaker,

        "Speaker_KR":
            item.get(
                "member_name_ko"
            ),

        "Role":
            item.get(
                "member_role_en"
            ),

        "Fed":
            item.get(
                "member_fed"
            ),

        "Voter":
            item.get(
                "member_voter"
            ),

        "Matched":
            bool(
                member_name
            ),

        # ----------------------------------------------------
        # Article
        # ----------------------------------------------------

        "Title":
            item.get(
                "title"
            ),

        "Source":
            item.get(
                "source"
            ),

        # ----------------------------------------------------
        # Relevance
        # ----------------------------------------------------

        "Relevance":
            item.get(
                "fomc_relevance"
            ),

        "Relevance_Score":
            item.get(
                "fomc_relevance_score"
            ),

        "Policy_Score":
            item.get(
                "policy_score"
            ),

        "Dual_Mandate_Score":
            item.get(
                "dual_mandate_score"
            ),

        "Macro_Score":
            item.get(
                "macro_score"
            ),

        # ----------------------------------------------------
        # Topic
        # ----------------------------------------------------

        "Topics":
            _topics_to_text(
                item.get(
                    "topics"
                )
            ),

        # ----------------------------------------------------
        # Hawk / Dove
        # ----------------------------------------------------

        "Hawk_Dove":
            item.get(
                "hawk_dove_label"
            ),

        "Hawk_Dove_Score":
            item.get(
                "hawk_dove_score"
            ),

        "Confidence":
            item.get(
                "hawk_dove_confidence"
            ),

        "Hawkish_Score":
            item.get(
                "hawkish_score"
            ),

        "Dovish_Score":
            item.get(
                "dovish_score"
            ),

        "Hawk_Evidence":
            _evidence_to_text(
                item.get(
                    "hawk_evidence_sentences"
                )
            ),

        "Dove_Evidence":
            _evidence_to_text(
                item.get(
                    "dove_evidence_sentences"
                )
            ),

        # ----------------------------------------------------
        # Fetch
        # ----------------------------------------------------

        "Body_Fetched":
            item.get(
                "body_fetched"
            ),

        "Body_Length":
            len(
                text
            ),

        "Body_Error":
            item.get(
                "body_fetch_error"
            ),

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        "URL":
            item.get(
                "url"
            ),
    }


# ============================================================
# DATAFRAME
# ============================================================

def _build_dataframe(
    processed
):

    rows = [
        _flatten_article(
            item
        )
        for item in processed
    ]

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        return df

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    df[
        "Date"
    ] = pd.to_datetime(
        df[
            "Date"
        ],
        errors="coerce",
    )

    # --------------------------------------------------------
    # SORT SUPPORT
    # --------------------------------------------------------

    df[
        "_relevance_order"
    ] = (
        df[
            "Relevance"
        ]
        .map(
            RELEVANCE_ORDER
        )
        .fillna(0)
    )

    df[
        "_hawk_order"
    ] = (
        df[
            "Hawk_Dove"
        ]
        .map(
            HAWK_DOVE_ORDER
        )
        .fillna(0)
    )

    # 최신순
    df = df.sort_values(
        by=[
            "Date",
            "_relevance_order",
        ],
        ascending=[
            False,
            False,
        ],
        na_position="last",
    )

    df = df.drop(
        columns=[
            "_relevance_order",
            "_hawk_order",
        ]
    )

    return df


# ============================================================
# SUMMARY
# ============================================================

def _build_summary(
    df
):

    rows = []

    rows.append({
        "Category": "TOTAL",
        "Label": "Articles",
        "Count": len(df),
    })

    rows.append({
        "Category": "MATCH",
        "Label": "Matched",
        "Count": int(
            df[
                "Matched"
            ].sum()
        ),
    })

    rows.append({
        "Category": "MATCH",
        "Label": "Unmatched",
        "Count": int(
            (
                ~df[
                    "Matched"
                ]
            ).sum()
        ),
    })

    # --------------------------------------------------------
    # Relevance
    # --------------------------------------------------------

    for label in [
        "HIGH",
        "MEDIUM",
        "LOW",
    ]:

        rows.append({
            "Category":
                "RELEVANCE",

            "Label":
                label,

            "Count":
                int(
                    (
                        df[
                            "Relevance"
                        ]
                        == label
                    ).sum()
                ),
        })

    # --------------------------------------------------------
    # Hawk / Dove
    # --------------------------------------------------------

    for label in [
        "HAWKISH",
        "NEUTRAL_HAWKISH",
        "NEUTRAL",
        "NEUTRAL_DOVISH",
        "DOVISH",
    ]:

        rows.append({
            "Category":
                "HAWK_DOVE",

            "Label":
                label,

            "Count":
                int(
                    (
                        df[
                            "Hawk_Dove"
                        ]
                        == label
                    ).sum()
                ),
        })

    # --------------------------------------------------------
    # Body
    # --------------------------------------------------------

    rows.append({
        "Category":
            "BODY",

        "Label":
            "Fetched",

        "Count":
            int(
                df[
                    "Body_Fetched"
                ]
                .fillna(False)
                .sum()
            ),
    })

    rows.append({
        "Category":
            "BODY",

        "Label":
            "Failed",

        "Count":
            int(
                (
                    ~df[
                        "Body_Fetched"
                    ]
                    .fillna(False)
                ).sum()
            ),
    })

    return pd.DataFrame(
        rows
    )


# ============================================================
# COLUMN WIDTH
# ============================================================

def _set_column_widths(
    worksheet
):

    widths = {

        "A": 13,   # Date
        "B": 24,   # Speaker
        "C": 18,   # KR
        "D": 35,   # Role
        "E": 22,   # Fed
        "F": 9,    # voter
        "G": 10,   # matched

        "H": 55,   # title
        "I": 24,   # source

        "J": 14,   # relevance
        "K": 16,
        "L": 14,
        "M": 18,
        "N": 14,

        "O": 40,   # topics

        "P": 22,   # HD
        "Q": 17,
        "R": 14,
        "S": 15,
        "T": 15,

        "U": 70,   # Hawk evidence
        "V": 70,   # Dove evidence

        "W": 14,
        "X": 14,
        "Y": 35,

        "Z": 70,   # URL
    }

    for column, width in (
        widths.items()
    ):

        worksheet.column_dimensions[
            column
        ].width = width


# ============================================================
# STYLE WORKSHEET
# ============================================================

def _style_worksheet(
    worksheet
):

    from openpyxl.styles import (
        Alignment,
        Font,
        PatternFill,
    )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="1F4E78",
    )

    header_font = Font(
        color="FFFFFF",
        bold=True,
    )

    for cell in worksheet[
        1
    ]:

        cell.fill = (
            header_fill
        )

        cell.font = (
            header_font
        )

        cell.alignment = (
            Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )
        )

    worksheet.freeze_panes = (
        "A2"
    )

    worksheet.auto_filter.ref = (
        worksheet.dimensions
    )

    worksheet.row_dimensions[
        1
    ].height = 30

    # --------------------------------------------------------
    # BODY
    # --------------------------------------------------------

    for row in worksheet.iter_rows(
        min_row=2
    ):

        for cell in row:

            cell.alignment = (
                Alignment(
                    vertical="top",
                    wrap_text=True,
                )
            )

    _set_column_widths(
        worksheet
    )


# ============================================================
# CONDITIONAL STYLE
# ============================================================

def _apply_label_colors(
    worksheet,
    header_map,
):

    from openpyxl.styles import (
        PatternFill,
        Font,
    )

    relevance_colors = {
        "HIGH": "FCE4D6",
        "MEDIUM": "FFF2CC",
        "LOW": "E2F0D9",
    }

    hawk_colors = {
        "HAWKISH": "F4CCCC",
        "NEUTRAL_HAWKISH": "FCE5CD",
        "NEUTRAL": "EEEEEE",
        "NEUTRAL_DOVISH": "D9EAF7",
        "DOVISH": "CFE2F3",
    }

    relevance_col = (
        header_map.get(
            "Relevance"
        )
    )

    hawk_col = (
        header_map.get(
            "Hawk_Dove"
        )
    )

    for row in range(
        2,
        worksheet.max_row + 1,
    ):

        # ----------------------------------------------------
        # Relevance
        # ----------------------------------------------------

        if relevance_col:

            cell = worksheet.cell(
                row=row,
                column=relevance_col,
            )

            value = cell.value

            if value in relevance_colors:

                cell.fill = PatternFill(
                    fill_type="solid",
                    fgColor=(
                        relevance_colors[
                            value
                        ]
                    ),
                )

                cell.font = Font(
                    bold=True
                )

        # ----------------------------------------------------
        # Hawk Dove
        # ----------------------------------------------------

        if hawk_col:

            cell = worksheet.cell(
                row=row,
                column=hawk_col,
            )

            value = cell.value

            if value in hawk_colors:

                cell.fill = PatternFill(
                    fill_type="solid",
                    fgColor=(
                        hawk_colors[
                            value
                        ]
                    ),
                )

                cell.font = Font(
                    bold=True
                )


# ============================================================
# SAVE
# ============================================================

def save_to_excel(
    processed,
    filename=None,
):
    """
    processed list를 Excel로 저장.

    시트:
        SUMMARY
        IMPORTANT
        ALL
        UNMATCHED
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # FILENAME
    # ========================================================

    if not filename:

        timestamp = (
            datetime.now()
            .strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        filename = (
            f"fed_speaker_monitor_"
            f"{timestamp}.xlsx"
        )

    if not filename.lower().endswith(
        ".xlsx"
    ):

        filename += ".xlsx"

    output_path = (
        OUTPUT_DIR
        / filename
    )

    # ========================================================
    # DATA
    # ========================================================

    df = _build_dataframe(
        processed
    )

    if df.empty:

        raise ValueError(
            "저장할 processed 데이터가 없습니다."
        )

    summary_df = (
        _build_summary(
            df
        )
    )

    important_df = df[
        df[
            "Relevance"
        ].isin(
            [
                "HIGH",
                "MEDIUM",
            ]
        )
    ].copy()

    unmatched_df = df[
        df[
            "Matched"
        ]
        == False
    ].copy()

    # ========================================================
    # WRITE
    # ========================================================

    with pd.ExcelWriter(
        output_path,
        engine="openpyxl",
    ) as writer:

        # SUMMARY 먼저
        summary_df.to_excel(
            writer,
            sheet_name="SUMMARY",
            index=False,
        )

        important_df.to_excel(
            writer,
            sheet_name="IMPORTANT",
            index=False,
        )

        df.to_excel(
            writer,
            sheet_name="ALL",
            index=False,
        )

        unmatched_df.to_excel(
            writer,
            sheet_name="UNMATCHED",
            index=False,
        )

        workbook = (
            writer.book
        )

        # ====================================================
        # SUMMARY STYLE
        # ====================================================

        summary_ws = workbook[
            "SUMMARY"
        ]

        _style_worksheet(
            summary_ws
        )

        summary_ws.column_dimensions[
            "A"
        ].width = 20

        summary_ws.column_dimensions[
            "B"
        ].width = 25

        summary_ws.column_dimensions[
            "C"
        ].width = 12

        # ====================================================
        # DATA SHEETS
        # ====================================================

        for sheet_name in [
            "IMPORTANT",
            "ALL",
            "UNMATCHED",
        ]:

            ws = workbook[
                sheet_name
            ]

            _style_worksheet(
                ws
            )

            headers = {
                cell.value:
                    cell.column
                for cell
                in ws[1]
            }

            _apply_label_colors(
                ws,
                headers,
            )

            # Date format
            date_col = (
                headers.get(
                    "Date"
                )
            )

            if date_col:

                for row in range(
                    2,
                    ws.max_row + 1,
                ):

                    ws.cell(
                        row=row,
                        column=date_col,
                    ).number_format = (
                        "yyyy-mm-dd"
                    )

            # URL hyperlink
            url_col = (
                headers.get(
                    "URL"
                )
            )

            if url_col:

                for row in range(
                    2,
                    ws.max_row + 1,
                ):

                    cell = ws.cell(
                        row=row,
                        column=url_col,
                    )

                    if cell.value:

                        cell.hyperlink = (
                            cell.value
                        )

                        cell.style = (
                            "Hyperlink"
                        )

    print()
    print(
        "=" * 90
    )

    print(
        "EXCEL SAVED"
    )

    print(
        "=" * 90
    )

    print(
        output_path
    )

    return str(
        output_path
    )