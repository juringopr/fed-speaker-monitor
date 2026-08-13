# crawlers/regional/chicago.py

from .adapter import (
    GenericRegionalFedAdapter,
)


class ChicagoFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = "Chicago Fed"

    base_url = (
        "https://www.chicagofed.org"
    )

    list_url = (
        "https://www.chicagofed.org/"
        "utilities/about-us/"
        "office-of-the-president/"
        "office-of-the-president-speaking"
    )

    href_contains = [
        "/publications/speeches/",
    ]

    require_member_in_context = True