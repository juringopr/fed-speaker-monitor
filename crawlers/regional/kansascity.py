# crawlers/regional/kansascity.py

import re
from urllib.parse import urljoin

from crawlers.base import (
    get_soup,
    clean_text,
)

from .adapter import (
    GenericRegionalFedAdapter,
)


class KansasCityFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = (
        "Kansas City Fed"
    )

    base_url = (
        "https://www.kansascityfed.org"
    )

    list_url = (
        "https://www.kansascityfed.org/"
        "speeches/"
    )

    rss_hub_url = (
        "https://www.kansascityfed.org/"
        "about-us/rss/"
    )

    president_url = (
        "https://www.kansascityfed.org/"
        "senior-leadership/president/"
    )

    require_member_in_context = True

    # ========================================================
    # MAIN
    # ========================================================

    def crawl(self):

        # ----------------------------------------------------
        # 1. 기존 speeches page
        # ----------------------------------------------------

        try:

            results = (
                self._crawl_speeches_page()
            )

            if results:

                return results

        except Exception as exc:

            print(
                "[KC MAIN FAIL]",
                exc
            )

        # ----------------------------------------------------
        # 2. RSS fallback
        # ----------------------------------------------------

        try:

            results = (
                self._crawl_rss_fallback()
            )

            if results:

                print(
                    "[KC RSS FALLBACK]",
                    len(results),
                    "건"
                )

                return results

        except Exception as exc:

            print(
                "[KC RSS FAIL]",
                exc
            )

        # ----------------------------------------------------
        # 3. President profile fallback
        # ----------------------------------------------------

        try:

            results = (
                self._crawl_president_page()
            )

            if results:

                print(
                    "[KC PROFILE FALLBACK]",
                    len(results),
                    "건"
                )

                return results

        except Exception as exc:

            print(
                "[KC PROFILE FAIL]",
                exc
            )

        return []

    # ========================================================
    # SPEECHES PAGE
    # ========================================================

    def _crawl_speeches_page(self):

        soup = get_soup(
            self.list_url,
            timeout=(4, 8),
        )

        results = []
        seen = set()

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

            if (
                "/speeches/"
                not in href.lower()
            ):
                continue

            if href.rstrip("/") in [
                "/speeches",
                "/speeches/",
            ]:
                continue

            title = clean_text(
                link.get_text(
                    " ",
                    strip=True,
                )
            )

            if not title:
                continue

            context = (
                self._get_link_context(
                    link
                )
            )

            search_text = (
                title
                + " "
                + context
            ).lower()

            if (
                "schmid"
                not in search_text
            ):
                continue

            url = urljoin(
                self.base_url,
                href,
            )

            if url in seen:
                continue

            seen.add(
                url
            )

            published_at = (
                self._date_from_context(
                    context
                )
                or
                self._date_from_url(
                    url
                )
                or
                self._extract_date_text(
                    context
                )
            )

            results.append(
                self.make_result(
                    title=title,
                    url=url,
                    published_at=published_at,
                    speaker_raw=(
                        self.member.get(
                            "name_en"
                        )
                        or "Jeffrey Schmid"
                    ),
                    text="",
                )
            )

        return self._deduplicate(
            results
        )

    # ========================================================
    # RSS FALLBACK
    # ========================================================

    def _crawl_rss_fallback(self):

        soup = get_soup(
            self.rss_hub_url,
            timeout=(5, 12),
        )

        feed_urls = []

        # ----------------------------------------------------
        # RSS hub에서 feed 링크 탐색
        # ----------------------------------------------------

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

            text = clean_text(
                link.get_text(
                    " ",
                    strip=True,
                )
            ).lower()

            href_lower = (
                href.lower()
            )

            # RSS / XML / feed 후보
            is_feed = any(
                token in href_lower
                for token in [
                    "rss",
                    "feed",
                    ".xml",
                ]
            )

            # speech 관련 feed 우선
            is_speech_related = (
                "speech" in text
                or
                "speech" in href_lower
                or
                "president" in text
                or
                "president" in href_lower
            )

            if (
                is_feed
                and
                is_speech_related
            ):

                feed_urls.append(
                    urljoin(
                        self.base_url,
                        href,
                    )
                )

        # 중복 제거
        feed_urls = list(
            dict.fromkeys(
                feed_urls
            )
        )

        print(
            "[KC RSS] feeds:",
            feed_urls
        )

        results = []

        for feed_url in feed_urls:

            try:

                feed_soup = get_soup(
                    feed_url,
                    timeout=(5, 12),
                )

            except Exception as exc:

                print(
                    "[KC RSS FEED FAIL]",
                    feed_url,
                    exc
                )

                continue

            items = feed_soup.find_all(
                [
                    "item",
                    "entry",
                ]
            )

            for item in items:

                title_tag = (
                    item.find(
                        "title"
                    )
                )

                if not title_tag:
                    continue

                title = clean_text(
                    title_tag.get_text(
                        " ",
                        strip=True,
                    )
                )

                if not title:
                    continue

                item_text = clean_text(
                    item.get_text(
                        " ",
                        strip=True,
                    )
                ).lower()

                # Jeff Schmid만
                if (
                    "schmid"
                    not in item_text
                    and
                    "schmid"
                    not in title.lower()
                ):
                    continue

                # --------------------------------------------
                # URL
                # --------------------------------------------

                link_tag = (
                    item.find(
                        "link"
                    )
                )

                url = None

                if link_tag:

                    url = (
                        link_tag.get(
                            "href"
                        )
                        or
                        link_tag.get_text(
                            strip=True
                        )
                    )

                if not url:
                    continue

                url = urljoin(
                    self.base_url,
                    url,
                )

                # --------------------------------------------
                # DATE
                # --------------------------------------------

                date_tag = (
                    item.find(
                        "pubdate"
                    )
                    or
                    item.find(
                        "published"
                    )
                    or
                    item.find(
                        "updated"
                    )
                )

                published_at = None

                if date_tag:

                    published_at = (
                        self._extract_date_text(
                            date_tag.get_text(
                                " ",
                                strip=True,
                            )
                        )
                    )

                if not published_at:

                    published_at = (
                        self._date_from_url(
                            url
                        )
                    )

                results.append(
                    self.make_result(
                        title=title,
                        url=url,
                        published_at=published_at,
                        speaker_raw=(
                            self.member.get(
                                "name_en"
                            )
                            or "Jeffrey Schmid"
                        ),
                        text="",
                    )
                )

        return self._deduplicate(
            results
        )

    # ========================================================
    # PRESIDENT PROFILE FALLBACK
    # ========================================================

    def _crawl_president_page(self):

        soup = get_soup(
            self.president_url,
            timeout=(5, 12),
        )

        results = []
        seen = set()

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

            if (
                "/speeches/"
                not in href.lower()
            ):
                continue

            url = urljoin(
                self.base_url,
                href,
            )

            if url in seen:
                continue

            title = clean_text(
                link.get_text(
                    " ",
                    strip=True,
                )
            )

            if not title:
                continue

            seen.add(
                url
            )

            context = (
                self._get_link_context(
                    link
                )
            )

            published_at = (
                self._date_from_context(
                    context
                )
                or
                self._date_from_url(
                    url
                )
                or
                self._extract_date_text(
                    context
                )
            )

            results.append(
                self.make_result(
                    title=title,
                    url=url,
                    published_at=published_at,
                    speaker_raw=(
                        self.member.get(
                            "name_en"
                        )
                        or "Jeffrey Schmid"
                    ),
                    text="",
                )
            )

        return self._deduplicate(
            results
        )

    # ========================================================
    # DATE
    # ========================================================

    def _extract_date_text(
        self,
        text,
    ):

        if not text:
            return None

        months = {
            "jan": 1,
            "january": 1,

            "feb": 2,
            "february": 2,

            "mar": 3,
            "march": 3,

            "apr": 4,
            "april": 4,

            "may": 5,

            "jun": 6,
            "june": 6,

            "jul": 7,
            "july": 7,

            "aug": 8,
            "august": 8,

            "sep": 9,
            "sept": 9,
            "september": 9,

            "oct": 10,
            "october": 10,

            "nov": 11,
            "november": 11,

            "dec": 12,
            "december": 12,
        }

        match = re.search(
            r"\b"
            r"(January|February|March|April|May|June|July|"
            r"August|September|October|November|December|"
            r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
            r"\.?\s+"
            r"(\d{1,2}),?\s+"
            r"(20\d{2})",
            text,
            flags=re.I,
        )

        if not match:
            return None

        month = (
            months[
                match.group(1)
                .lower()
            ]
        )

        day = int(
            match.group(2)
        )

        year = int(
            match.group(3)
        )

        return (
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )