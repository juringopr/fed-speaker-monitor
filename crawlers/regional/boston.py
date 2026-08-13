# crawlers/regional/boston.py

from .adapter import (
    GenericRegionalFedAdapter,
)


class BostonFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = "Boston Fed"

    base_url = (
        "https://www.bostonfed.org"
    )

    list_url = (
        "https://www.bostonfed.org/"
        "news-and-events/speeches.aspx"
    )

    href_contains = [
        "/news-and-events/speeches/",
    ]

    require_member_in_context = True