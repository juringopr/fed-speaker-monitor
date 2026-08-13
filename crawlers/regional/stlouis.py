# crawlers/regional/stlouis.py

import re

import requests
from bs4 import BeautifulSoup

from crawlers.base import (
    get_soup,
    clean_text,
)

from .adapter import (
    GenericRegionalFedAdapter,
)


class StLouisFedAdapter(
    GenericRegionalFedAdapter
):

    source_name = (
        "St. Louis Fed"
    )

    base_url = (
        "https://www.stlouisfed.org"
    )

    list_url = (
        "https://www.stlouisfed.org/"
        "from-the-president/remarks"
    )

    sitemap_url = (
        "https://www.stlouisfed.org/"
        "sitemap.xml"
    )

    rss_url = (
        "https://www.stlouisfed.org/"
        "rss"
    )

    require_member_in_context = False

    # ========================================================
    # MAIN
    # ========================================================

    def crawl(self):

        # ----------------------------------------------------
        # 1. Main remarks
        # ----------------------------------------------------

        try:

            results = (
                self._crawl_main_page()
            )

            if results:

                return results

        except Exception as exc:

            print(
                "[STL MAIN FAIL]",
                exc
            )

        # ----------------------------------------------------
        # 2. Sitemap
        # ----------------------------------------------------

        try:

            results = (
                self._crawl_sitemap_fallback()
            )

            if results:

                print(
                    "[STL SITEMAP FALLBACK]",
                    len(results),
                    "건"
                )

                return results

        except Exception as exc:

            print(
                "[STL SITEMAP FAIL]",
                exc
            )

        # ----------------------------------------------------
        # 3. RSS hub
        # ----------------------------------------------------

        try:

            results = (
                self._crawl_rss_fallback()
            )

            if results:

                print(
                    "[STL RSS FALLBACK]",
                    len(results),
                    "건"
                )

                return results

        except Exception as exc:

            print(
                "[STL RSS FAIL]",
                exc
            )

        return []

    # ========================================================
    # MAIN PAGE
    # ========================================================

    def _crawl_main_page(self):

        soup = get_soup(
            self.list_url,
            timeout=(4, 8),
        )

        return self._extract_remark_links(
            soup
        )

    # ========================================================
    # SITEMAP FALLBACK
    # ========================================================

    def _crawl_sitemap_fallback(self):

        response = requests.get(
            self.sitemap_url,

            timeout=(
                5,
                12,
            ),

            headers={
                "User-Agent":
                    (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64)"
                    )
            },
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.content,
            "xml",
        )

        candidate_urls = []

        for loc in soup.find_all(
            "loc"
        ):

            url = clean_text(
                loc.get_text(
                    strip=True
                )
            )

            if not url:
                continue

            url_lower = (
                url.lower()
            )

            if (
                "/from-the-president/"
                "remarks/2026/"
                not in url_lower
            ):
                continue

            candidate_urls.append(
                url
            )

        candidate_urls = list(
            dict.fromkeys(
                candidate_urls
            )
        )

        print(
            "[STL SITEMAP]",
            len(candidate_urls),
            "candidate urls"
        )

        results = []

        for url in candidate_urls:

            slug = (
                url
                .rstrip("/")
                .split("/")[-1]
            )

            if not slug:
                continue

            title = (
                slug
                .replace(
                    "-",
                    " "
                )
                .strip()
                .title()
            )

            # Sitemap 자체에는 보통 날짜가 없으므로
            # 우선 None.
            # 이후 article body fetch에서
            # 상세페이지 날짜 보강 가능.
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
                        or "Alberto Musalem"
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
            self.rss_url,
            timeout=(5, 12),
        )

        feed_urls = []

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

            is_feed = any(
                token in href_lower
                for token in [
                    "rss",
                    "feed",
                    ".xml",
                ]
            )

            is_relevant = any(
                token in (
                    text
                    + " "
                    + href_lower
                )
                for token in [
                    "president",
                    "remarks",
                    "speech",
                    "fomc",
                ]
            )

            if (
                is_feed
                and
                is_relevant
            ):

                if href.startswith(
                    "http"
                ):

                    feed_url = href

                else:

                    feed_url = (
                        self.base_url.rstrip("/")
                        + "/"
                        + href.lstrip("/")
                    )

                feed_urls.append(
                    feed_url
                )

        feed_urls = list(
            dict.fromkeys(
                feed_urls
            )
        )

        print(
            "[STL RSS] feeds:",
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
                    "[STL RSS FEED FAIL]",
                    feed_url,
                    exc
                )

                continue

            for item in feed_soup.find_all(
                [
                    "item",
                    "entry",
                ]
            ):

                item_text = clean_text(
                    item.get_text(
                        " ",
                        strip=True,
                    )
                )

                lower_text = (
                    item_text.lower()
                )

                # Musalem / President remarks만
                if (
                    "musalem"
                    not in lower_text
                    and
                    "president"
                    not in lower_text
                ):
                    continue

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

                if (
                    "/from-the-president/"
                    "remarks/"
                    not in url.lower()
                ):
                    continue

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

                results.append(
                    self.make_result(
                        title=title,
                        url=url,
                        published_at=published_at,
                        speaker_raw=(
                            self.member.get(
                                "name_en"
                            )
                            or "Alberto Musalem"
                        ),
                        text="",
                    )
                )

        return self._deduplicate(
            results
        )

    # ========================================================
    # EXTRACT MAIN PAGE LINKS
    # ========================================================

    def _extract_remark_links(
        self,
        soup,
    ):

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

            href_lower = (
                href.lower()
            )

            if (
                "/from-the-president/"
                "remarks/2026/"
                not in href_lower
            ):
                continue

            if href.startswith(
                "http"
            ):

                url = href

            else:

                url = (
                    self.base_url.rstrip("/")
                    + "/"
                    + href.lstrip("/")
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
                        or "Alberto Musalem"
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