# run_crawler.py

from pprint import pprint
from collections import Counter

from crawlers import (
    crawl_fed_board,
    crawl_regional_fed,
)


# ============================================================
# CONFIG
# ============================================================

TARGET_YEAR = 2026

FETCH_BODY = False


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # FED BOARD
    # ========================================================

    print()
    print(
        "=" * 90
    )

    print(
        "FED BOARD"
    )

    print(
        "=" * 90
    )

    try:

        board = (
            crawl_fed_board(
                year=TARGET_YEAR,
                fetch_body=FETCH_BODY,
            )
        )

    except Exception as exc:

        print(
            "[FED BOARD ERROR]"
        )

        print(
            exc
        )

        board = []

    print(
        "count:",
        len(board)
    )

    # --------------------------------------------------------
    # Board sample
    # --------------------------------------------------------

    print()
    print(
        "[FED BOARD SAMPLE]"
    )

    for item in board[:5]:

        pprint(
            item
        )

    # ========================================================
    # REGIONAL
    # ========================================================

    print()
    print(
        "=" * 90
    )

    print(
        "REGIONAL FED"
    )

    print(
        "=" * 90
    )

    try:

        regional = (
            crawl_regional_fed(
                fetch_body=FETCH_BODY,
                year=TARGET_YEAR,
            )
        )

    except Exception as exc:

        print(
            "[REGIONAL ERROR]"
        )

        print(
            exc
        )

        regional = []

    print()
    print(
        "count:",
        len(regional)
    )

    # ========================================================
    # SOURCE COUNT
    # ========================================================

    print()
    print(
        "-" * 90
    )

    print(
        "SOURCE COUNT"
    )

    print(
        "-" * 90
    )

    source_counter = Counter(

        item.get(
            "source"
        )
        or "UNKNOWN"

        for item in regional
    )

    for source, count in sorted(
        source_counter.items()
    ):

        print(
            f"{source:<25} "
            f"{count:>5}건"
        )

    # ========================================================
    # SPEAKER COUNT
    # ========================================================

    print()
    print(
        "-" * 90
    )

    print(
        "SPEAKER COUNT"
    )

    print(
        "-" * 90
    )

    speaker_counter = Counter(

        item.get(
            "speaker_raw"
        )
        or "UNKNOWN"

        for item in regional
    )

    for speaker, count in sorted(
        speaker_counter.items()
    ):

        print(
            f"{speaker:<30} "
            f"{count:>5}건"
        )

    # ========================================================
    # REGIONAL SAMPLE
    # ========================================================

    print()
    print(
        "-" * 90
    )

    print(
        "LATEST REGIONAL ITEMS"
    )

    print(
        "-" * 90
    )

    for item in regional[:20]:

        pprint(
            item
        )

    # ========================================================
    # TOTAL
    # ========================================================

    print()
    print(
        "=" * 90
    )

    print(
        "TOTAL"
    )

    print(
        "=" * 90
    )

    print(
        "Fed Board :",
        len(board)
    )

    print(
        "Regional  :",
        len(regional)
    )

    print(
        "Total     :",
        len(board)
        + len(regional)
    )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    main()