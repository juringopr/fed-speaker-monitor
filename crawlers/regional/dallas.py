# crawlers/regional/dallas.py

from .adapter import (
    GenericRegionalFedAdapter,
)


class DallasFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = "Dallas Fed"

    base_url = (
        "https://www.dallasfed.org"
    )

    list_url = (
        "https://www.dallasfed.org/"
        "news/speeches/logan"
    )

    href_contains = [
        "/news/speeches/logan/",
    ]

    # Logan 전용 페이지라 추가 필터 불필요
    require_member_in_context = False