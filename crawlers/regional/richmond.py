# crawlers/regional/richmond.py

from .adapter import (
    GenericRegionalFedAdapter,
)


class RichmondFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = "Richmond Fed"

    base_url = (
        "https://www.richmondfed.org"
    )

    list_url = (
        "https://www.richmondfed.org/"
        "press_room/speeches"
    )

    href_contains = [
        "/press_room/speeches/",
    ]

    require_member_in_context = True