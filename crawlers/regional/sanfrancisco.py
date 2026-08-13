# crawlers/regional/sanfrancisco.py

from .adapter import (
    GenericRegionalFedAdapter,
)


class SanFranciscoFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = "San Francisco Fed"

    base_url = (
        "https://www.frbsf.org"
    )

    list_url = (
        "https://www.frbsf.org/"
        "news-and-media/speeches/"
        "mary-c-daly/"
    )

    href_contains = [
        "/news-and-media/speeches/mary-c-daly/",
    ]

    # Daly 전용 archive
    require_member_in_context = False