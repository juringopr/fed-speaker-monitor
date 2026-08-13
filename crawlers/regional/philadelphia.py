# crawlers/regional/philadelphia.py

import re
from urllib.parse import urljoin

from crawlers.base import (
    get_soup,
    clean_text,
)

from .adapter import (
    GenericRegionalFedAdapter,
)


class PhiladelphiaFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = (
        "Philadelphia Fed"
    )

    base_url = (
        "https://www.philadelphiafed.org"
    )

    list_url = (
        "https://www.philadelphiafed.org/"
        "the-economy/"
        "speeches-anna-paulson"
    )

    require_member_in_context = False

    # ========================================================
    # MAIN
    # ========================================================

    def crawl(self):

        soup = get_soup(
            self.list_url,
            timeout=(
                5,
                12,
            ),
        )

        results = []
        seen_urls = set()

        for link in soup.find_all(
            "a",
            href=True,
        ):

            href = (
                link.get(
                    "href",
                    ""
                )
                or ""
            ).strip()

            if not href:
                continue

            # =================================================
            # 실제 Anna Paulson speech 상세 페이지 URL만 허용
            #
            # 예:
            #
            # /the-economy/monetary-policy/
            # 260519-2026-financial-markets-conference
            #
            # /the-economy/macroeconomics/
            # 260414-...
            #
            # =================================================

            match = re.search(
                r"/the-economy/"
                r"[^/]+/"
                r"(\d{6})"
                r"[-/]",
                href,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            # ------------------------------------------------
            # YYMMDD
            # ------------------------------------------------

            date_token = (
                match.group(1)
            )

            yy = int(
                date_token[0:2]
            )

            mm = int(
                date_token[2:4]
            )

            dd = int(
                date_token[4:6]
            )

            # 20xx 전제
            year = (
                2000
                + yy
            )

            if not (
                1 <= mm <= 12
            ):
                continue

            if not (
                1 <= dd <= 31
            ):
                continue

            published_at = (
                f"{year:04d}-"
                f"{mm:02d}-"
                f"{dd:02d}"
            )

            # ------------------------------------------------
            # 2026만
            # ------------------------------------------------

            if year != 2026:
                continue

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            title = clean_text(
                link.get_text(
                    " ",
                    strip=True,
                )
            )

            if not title:
                continue

            # 카테고리성 제목 방지
            excluded_titles = {
                "monetary policy",
                "banking & financial markets",
                "macroeconomics",
                "regional economics",
                "the economy",
                "research",
                "speeches",
            }

            if (
                title.lower()
                in excluded_titles
            ):
                continue

            # ------------------------------------------------
            # URL
            # ------------------------------------------------

            url = urljoin(
                self.base_url,
                href,
            )

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(
                url
            )

            # ------------------------------------------------
            # OPTIONAL CONTEXT CHECK
            #
            # Anna Paulson 전용 페이지라 강제하지 않음.
            # ------------------------------------------------

            results.append(
                self.make_result(
                    title=title,
                    url=url,
                    published_at=published_at,
                    speaker_raw=(
                        self.member.get(
                            "name_en"
                        )
                        or "Anna Paulson"
                    ),
                    text="",
                )
            )

        return self._deduplicate(
            results
        )