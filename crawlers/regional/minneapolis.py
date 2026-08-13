# crawlers/regional/minneapolis.py

from .adapter import (
    GenericRegionalFedAdapter,
)


class MinneapolisFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = "Minneapolis Fed"

    base_url = (
        "https://www.minneapolisfed.org"
    )

    list_url = (
        "https://www.minneapolisfed.org/"
        "publications-archive/all-speeches"
    )

    href_contains = [
        "/speeches/",
    ]

    require_member_in_context = True