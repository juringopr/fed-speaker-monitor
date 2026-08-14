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

    source_name = "St. Louis Fed"

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
        # 1. MAIN REMARKS PAGE
        # ----------------------------------------------------

        try:

            results = (
                self._crawl_main_page()
            )

            if results:

                print(
                    "[STL MAIN]",
                    len(results),
                    "건"
                )

                return results

        except Exception as exc:

            print(
                "[STL MAIN FAIL]",
                exc
            )

        # ----------------------------------------------------
        # 2. SITEMAP FALLBACK
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
        # 3. RSS FALLBACK
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

    def _crawl_main_page(
        self,
    ):

        soup = get_soup(
            self.list_url,
            timeout=(
                4,
                8,
            ),
        )

        return (
            self._extract_remark_links(
                soup
            )
        )

    # ========================================================
    # SITEMAP FALLBACK
    # ========================================================

    def _crawl_sitemap_fallback(
        self,
    ):

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

        # ====================================================
        # URL COLLECTION
        # ====================================================

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

        # 중복 제거
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

        # ====================================================
        # EACH SPEECH
        # ====================================================

        for url in candidate_urls:

            slug = (
                url
                .rstrip("/")
                .split("/")[-1]
            )

            if not slug:
                continue

            # ------------------------------------------------
            # DEFAULT TITLE
            # ------------------------------------------------

            title = (
                slug
                .replace(
                    "-",
                    " "
                )
                .strip()
                .title()
            )

            # =================================================
            # 1. URL에서 날짜 추출
            #
            # 예:
            # bloomberg-tv-interview-may-28-2026
            # -> 2026-05-28
            #
            # URL에서 날짜가 잡히면 St. Louis 상세페이지를
            # 다시 요청하지 않는다.
            # =================================================

            published_at = (
                self._date_from_url(
                    url
                )
            )

            if published_at:

                print(
                    "[STL URL DATE]",
                    published_at,
                    "|",
                    title[:80],
                )

            # =================================================
            # 2. URL에 날짜가 없을 때만 JINA READER
            # =================================================

            if not published_at:

                try:

                    (
                        reader_title,
                        reader_date,
                    ) = (
                        self._fetch_reader_metadata(
                            url
                        )
                    )

                    if reader_title:

                        title = (
                            reader_title
                        )

                    if reader_date:

                        published_at = (
                            reader_date
                        )

                    print(
                        "[STL READER META]",
                        published_at
                        or "NO DATE",
                        "|",
                        title[:80],
                    )

                except Exception as exc:

                    print(
                        "[STL READER META FAIL]",
                        url,
                        "|",
                        exc,
                    )

            # =================================================
            # RESULT
            # =================================================

            result = (
                self.make_result(
                    title=title,
                    url=url,
                    published_at=published_at,
                    speaker_raw=(
                        self.member.get(
                            "name_en"
                        )
                        or
                        "Alberto Musalem"
                    ),
                    text="",
                )
            )

            # ------------------------------------------------
            # 중요
            #
            # downstream에서 date를 쓰든 published_at을 쓰든
            # 날짜가 사라지지 않도록 두 필드를 같이 저장.
            # ------------------------------------------------

            if published_at:

                result[
                    "published_at"
                ] = published_at

                result[
                    "date"
                ] = published_at

            results.append(
                result
            )

        return (
            self._deduplicate(
                results
            )
        )

    # ========================================================
    # JINA READER METADATA
    # ========================================================

    def _fetch_reader_metadata(
        self,
        url,
    ):
        """
        St. Louis 상세 페이지 직접 접근 timeout 회피.

        r.jina.ai를 이용해서
        title / published date를 확보한다.

        return:
            title, published_at
        """

        reader_url = (
            "https://r.jina.ai/"
            + url
        )

        response = requests.get(
            reader_url,
            timeout=(
                5,
                20,
            ),
            headers={
                "User-Agent":
                    (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64)"
                    ),
                "Accept":
                    "text/plain",
            },
        )

        response.raise_for_status()

        raw = (
            response.text
            or ""
        )

        title = None
        published_at = None

        # ====================================================
        # TITLE
        # ====================================================

        title_match = re.search(
            r"(?im)^"
            r"Title\s*:"
            r"\s*(.+?)"
            r"\s*$",
            raw,
        )

        if title_match:

            title = clean_text(
                title_match.group(1)
            )

        # ====================================================
        # DATE METADATA
        # ====================================================

        date_patterns = [

            r"(?im)^"
            r"Published\s+Time\s*:"
            r"\s*(.+?)"
            r"\s*$",

            r"(?im)^"
            r"Published\s*:"
            r"\s*(.+?)"
            r"\s*$",

            r"(?im)^"
            r"Date\s*:"
            r"\s*(.+?)"
            r"\s*$",
        ]

        for pattern in date_patterns:

            match = re.search(
                pattern,
                raw,
            )

            if not match:
                continue

            published_at = (
                self._parse_any_date(
                    match.group(1)
                )
            )

            if published_at:
                break

        # ====================================================
        # Metadata에 날짜가 없으면 Reader 앞부분 검색
        # ====================================================

        if not published_at:

            published_at = (
                self._parse_any_date(
                    raw[:4000]
                )
            )

        return (
            title,
            published_at,
        )

    # ========================================================
    # RSS FALLBACK
    # ========================================================

    def _crawl_rss_fallback(
        self,
    ):

        soup = get_soup(
            self.rss_url,
            timeout=(
                5,
                12,
            ),
        )

        feed_urls = []

        # ====================================================
        # RSS FEED URL COLLECTION
        # ====================================================

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
                token
                in href_lower

                for token in [
                    "rss",
                    "feed",
                    ".xml",
                ]
            )

            is_relevant = any(
                token
                in (
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

                    feed_url = (
                        href
                    )

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

        # ====================================================
        # EACH RSS FEED
        # ====================================================

        for feed_url in feed_urls:

            try:

                feed_soup = get_soup(
                    feed_url,
                    timeout=(
                        5,
                        12,
                    ),
                )

            except Exception as exc:

                print(
                    "[STL RSS FEED FAIL]",
                    feed_url,
                    exc,
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

                if (
                    "musalem"
                    not in lower_text
                    and
                    "president"
                    not in lower_text
                ):

                    continue

                # ------------------------------------------------
                # TITLE
                # ------------------------------------------------

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

                # ------------------------------------------------
                # URL
                # ------------------------------------------------

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

                # ------------------------------------------------
                # RSS DATE
                # ------------------------------------------------

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
                        self._parse_any_date(
                            date_tag.get_text(
                                " ",
                                strip=True,
                            )
                        )
                    )

                # ------------------------------------------------
                # URL DATE
                # ------------------------------------------------

                if not published_at:

                    published_at = (
                        self._date_from_url(
                            url
                        )
                    )

                # ------------------------------------------------
                # JINA FALLBACK
                # ------------------------------------------------

                if not published_at:

                    try:

                        (
                            reader_title,
                            reader_date,
                        ) = (
                            self._fetch_reader_metadata(
                                url
                            )
                        )

                        if reader_title:

                            title = (
                                reader_title
                            )

                        if reader_date:

                            published_at = (
                                reader_date
                            )

                    except Exception as exc:

                        print(
                            "[STL RSS READER FAIL]",
                            url,
                            "|",
                            exc,
                        )

                # ------------------------------------------------
                # RESULT
                # ------------------------------------------------

                result = (
                    self.make_result(
                        title=title,
                        url=url,
                        published_at=published_at,
                        speaker_raw=(
                            self.member.get(
                                "name_en"
                            )
                            or
                            "Alberto Musalem"
                        ),
                        text="",
                    )
                )

                if published_at:

                    result[
                        "published_at"
                    ] = published_at

                    result[
                        "date"
                    ] = published_at

                results.append(
                    result
                )

        return (
            self._deduplicate(
                results
            )
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

            # ------------------------------------------------
            # URL
            # ------------------------------------------------

            if href.startswith(
                "http"
            ):

                url = (
                    href
                )

            else:

                url = (
                    self.base_url.rstrip("/")
                    + "/"
                    + href.lstrip("/")
                )

            if url in seen:
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

                slug = (
                    url
                    .rstrip("/")
                    .split("/")[-1]
                )

                title = (
                    slug
                    .replace(
                        "-",
                        " "
                    )
                    .strip()
                    .title()
                )

            seen.add(
                url
            )

            # ------------------------------------------------
            # CONTEXT
            # ------------------------------------------------

            context = (
                self._get_link_context(
                    link
                )
            )

            # ------------------------------------------------
            # DATE
            #
            # 우선순위:
            # context → URL → Jina
            # ------------------------------------------------

            published_at = (
                self._date_from_context(
                    context
                )
            )

            if not published_at:

                published_at = (
                    self._date_from_url(
                        url
                    )
                )

            # ------------------------------------------------
            # 직접 상세페이지 요청 대신 Jina
            # ------------------------------------------------

            if not published_at:

                try:

                    (
                        reader_title,
                        reader_date,
                    ) = (
                        self._fetch_reader_metadata(
                            url
                        )
                    )

                    if reader_title:

                        title = (
                            reader_title
                        )

                    if reader_date:

                        published_at = (
                            reader_date
                        )

                except Exception as exc:

                    print(
                        "[STL MAIN READER FAIL]",
                        url,
                        "|",
                        exc,
                    )

            # ------------------------------------------------
            # RESULT
            # ------------------------------------------------

            result = (
                self.make_result(
                    title=title,
                    url=url,
                    published_at=published_at,
                    speaker_raw=(
                        self.member.get(
                            "name_en"
                        )
                        or
                        "Alberto Musalem"
                    ),
                    text="",
                )
            )

            if published_at:

                result[
                    "published_at"
                ] = published_at

                result[
                    "date"
                ] = published_at

            results.append(
                result
            )

        return (
            self._deduplicate(
                results
            )
        )

    # ========================================================
    # GENERIC DATE PARSER
    # ========================================================

    def _parse_any_date(
        self,
        text,
    ):
        """
        지원 예:

        2026-05-28
        2026-05-28T10:00:00
        May 28, 2026
        May 28 2026
        Jan. 13, 2026
        """

        if not text:
            return None

        value = str(
            text
        )

        # ====================================================
        # ISO DATE
        # ====================================================

        iso_match = re.search(
            r"\b"
            r"(20\d{2})"
            r"-"
            r"(\d{1,2})"
            r"-"
            r"(\d{1,2})"
            r"\b",
            value,
        )

        if iso_match:

            year = int(
                iso_match.group(1)
            )

            month = int(
                iso_match.group(2)
            )

            day = int(
                iso_match.group(3)
            )

            if (
                1 <= month <= 12
                and
                1 <= day <= 31
            ):

                return (
                    f"{year:04d}-"
                    f"{month:02d}-"
                    f"{day:02d}"
                )

        # ====================================================
        # ENGLISH DATE
        # ====================================================

        return (
            self._extract_date_text(
                value
            )
        )

    # ========================================================
    # ENGLISH DATE
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
            str(
                text
            ),
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

    # ========================================================
    # DATE FROM URL
    # ========================================================

    def _date_from_url(
        self,
        url,
    ):
        """
        URL slug의 날짜를 읽는다.

        예:

        bloomberg-tv-interview-may-28-2026
        -> 2026-05-28
        """

        if not url:
            return None

        slug = (
            str(
                url
            )
            .rstrip("/")
            .split("/")[-1]
            .replace(
                "-",
                " "
            )
        )

        return (
            self._parse_any_date(
                slug
            )
        )

    # ========================================================
    # DATE FROM CONTEXT
    # ========================================================

    def _date_from_context(
        self,
        context,
    ):

        if not context:
            return None

        return (
            self._parse_any_date(
                context
            )
        )

    # ========================================================
    # LINK CONTEXT
    # ========================================================

    def _get_link_context(
        self,
        link,
    ):

        contexts = []

        # ----------------------------------------------------
        # 링크 자체
        # ----------------------------------------------------

        own_text = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        if own_text:

            contexts.append(
                own_text
            )

        # ----------------------------------------------------
        # 부모 최대 4단계
        # ----------------------------------------------------

        parent = (
            link.parent
        )

        depth = 0

        while (
            parent
            is not None
            and
            depth < 4
        ):

            text = clean_text(
                parent.get_text(
                    " ",
                    strip=True,
                )
            )

            if text:

                contexts.append(
                    text
                )

            parent = (
                parent.parent
            )

            depth += 1

        return clean_text(
            " ".join(
                contexts
            )
        )

    # ========================================================
    # DEDUPLICATE
    # ========================================================

    def _deduplicate(
        self,
        results,
    ):

        deduped = []

        seen = set()

        for item in results:

            url = (
                item.get(
                    "url"
                )
                or ""
            ).strip()

            if not url:
                continue

            normalized_url = (
                url
                .rstrip("/")
                .lower()
            )

            if normalized_url in seen:
                continue

            seen.add(
                normalized_url
            )

            # ------------------------------------------------
            # DATE FINAL SYNC
            # ------------------------------------------------

            final_date = (
                item.get(
                    "published_at"
                )
                or
                item.get(
                    "date"
                )
            )

            if final_date:

                normalized_date = (
                    self._parse_any_date(
                        final_date
                    )
                )

                if normalized_date:

                    item[
                        "published_at"
                    ] = normalized_date

                    item[
                        "date"
                    ] = normalized_date

            deduped.append(
                item
            )

        return deduped