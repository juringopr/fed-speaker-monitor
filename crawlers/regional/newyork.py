# crawlers/regional/newyork.py

from .adapter import (
    GenericRegionalFedAdapter,
)


class NewYorkFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = "New York Fed"

    base_url = (
        "https://www.newyorkfed.org"
    )

    # New York Fed speech archive
    list_url = (
        "https://www.newyorkfed.org/"
        "newsevents/speeches"
    )

    href_contains = [
        "/newsevents/speeches/",
    ]

    # New York Fed에는 Perli 등 다른 인사도 있기 때문에
    # John Williams만 필터
    require_member_in_context = True