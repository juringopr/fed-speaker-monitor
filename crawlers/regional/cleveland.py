# crawlers/regional/cleveland.py

from .adapter import (
    GenericRegionalFedAdapter,
)


class ClevelandFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = "Cleveland Fed"

    base_url = (
        "https://www.clevelandfed.org"
    )

    list_url = (
        "https://www.clevelandfed.org/"
        "collections/speeches"
    )

    href_contains = [
        "/collections/speeches/",
    ]

    # 다른 인사 연설도 섞일 수 있으므로
    # Beth Hammack만 필터
    require_member_in_context = True