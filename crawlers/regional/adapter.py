# crawlers/regional/adapter.py

import re

from urllib.parse import urlparse

from crawlers.base import (
    get_soup,
    clean_text,
    absolute_url,
    parse_english_date,
    extract_article_text,
)


class GenericRegionalFedAdapter:
    """
    지역 연은 공통 Adapter.

    각 지역별 파일에서는 주로 아래 값만 정의한다.

        source_name
        base_url
        list_url
        href_contains
        require_member_in_context

    반환 포맷
    ----------
    {
        "published_at": "2026-07-16",
        "title": "...",
        "speaker_raw": "Lorie Logan",
        "url": "...",
        "source": "Dallas Fed",
        "source_type": "OFFICIAL",
        "text": ""
    }
    """

    # ========================================================
    # SITE CONFIG
    # ========================================================

    source_name = None

    base_url = None

    list_url = None

    href_contains = []

    # 목록 페이지에 여러 연준 인사가 섞여있는 경우 True
    require_member_in_context = False

    # 너무 짧은 링크 텍스트 제거
    min_title_length = 3

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        member=None,
        fetch_body=False,
    ):

        self.member = (
            member
            or {}
        )

        self.fetch_body = (
            fetch_body
        )

    # ========================================================
    # MAIN
    # ========================================================

    def crawl(self):

        if not self.list_url:
            return []

        soup = get_soup(
            self.list_url
        )

        results = []

        seen_urls = set()

        # ====================================================
        # 모든 링크 확인
        # ====================================================

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = (
                link.get(
                    "href",
                    ""
                )
                or ""
            ).strip()

            # ------------------------------------------------
            # URL 필터
            # ------------------------------------------------

            if not self._valid_href(
                href
            ):
                continue

            url = absolute_url(
                self.base_url,
                href
            )

            if not url:
                continue

            if url in seen_urls:
                continue

            if not self._same_domain(
                url
            ):
                continue

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            title = clean_text(
                link.get_text(
                    " ",
                    strip=True
                )
            )

            if not title:
                continue

            if len(title) < (
                self.min_title_length
            ):
                continue

            # ------------------------------------------------
            # 목록 card / 주변 context
            # ------------------------------------------------

            context = (
                self._get_link_context(
                    link
                )
            )

            # ------------------------------------------------
            # 인물 필터
            # ------------------------------------------------

            if (
                self.require_member_in_context
                and
                not self._member_matches(
                    context
                )
            ):
                continue

            # 이 시점부터 유효 URL
            seen_urls.add(
                url
            )

            # ------------------------------------------------
            # 상세페이지
            # ------------------------------------------------

            if self.fetch_body:

                try:

                    article = (
                        self._crawl_article(
                            url
                        )
                    )

                except Exception:

                    # 상세페이지 실패해도
                    # 목록 데이터는 살린다.
                    article = {}

            else:

                article = {}

            # ------------------------------------------------
            # DATE
            #
            # 우선순위:
            # 1. 상세페이지 실제 날짜
            # 2. URL 날짜
            # 3. 목록 주변 context 날짜
            #
            # URL 날짜를 context보다 우선하는 것이 핵심.
            # ------------------------------------------------

            published_at = (
                article.get(
                    "published_at"
                )
                or
                self._date_from_url(
                    url
                )
                or
                self._date_from_context(
                    context
                )
            )

            # ------------------------------------------------
            # SPEAKER
            # ------------------------------------------------

            speaker_raw = (
                article.get(
                    "speaker_raw"
                )
                or
                self.member.get(
                    "name_en"
                )
            )

            # ------------------------------------------------
            # RESULT
            # ------------------------------------------------

            results.append(
                self.make_result(

                    title=(
                        article.get(
                            "title"
                        )
                        or title
                    ),

                    url=url,

                    published_at=(
                        published_at
                    ),

                    speaker_raw=(
                        speaker_raw
                    ),

                    text=(
                        article.get(
                            "text",
                            ""
                        )
                    ),
                )
            )

        return self._deduplicate(
            results
        )

    # ========================================================
    # RESULT BUILDER
    # ========================================================

    def make_result(
        self,
        title,
        url,
        published_at=None,
        speaker_raw=None,
        text="",
    ):

        return {

            "published_at":
                published_at,

            "title":
                clean_text(
                    title
                ),

            "speaker_raw":
                speaker_raw,

            "url":
                url,

            "source":
                self.source_name,

            "source_type":
                "OFFICIAL",

            "text":
                text
                or "",
        }

    # ========================================================
    # URL FILTER
    # ========================================================

    def _valid_href(
        self,
        href
    ):

        if not href:
            return False

        href_lower = (
            href.lower()
        )

        # ----------------------------------------------------
        # 불필요 링크
        # ----------------------------------------------------

        invalid_prefixes = (
            "mailto:",
            "javascript:",
            "tel:",
            "#",
        )

        if href_lower.startswith(
            invalid_prefixes
        ):
            return False

        # ----------------------------------------------------
        # PDF 등 제외
        # ----------------------------------------------------

        if href_lower.endswith(
            (
                ".pdf",
                ".jpg",
                ".jpeg",
                ".png",
                ".zip",
            )
        ):
            return False

        # ----------------------------------------------------
        # 지역별 path filter
        # ----------------------------------------------------

        if not self.href_contains:
            return True

        return any(

            keyword.lower()
            in href_lower

            for keyword
            in self.href_contains
        )

    # ========================================================
    # DOMAIN
    # ========================================================

    def _same_domain(
        self,
        url
    ):

        try:

            base_domain = (
                urlparse(
                    self.base_url
                )
                .netloc
                .lower()
            )

            target_domain = (
                urlparse(
                    url
                )
                .netloc
                .lower()
            )

            # www 차이 제거
            base_domain = (
                base_domain
                .removeprefix(
                    "www."
                )
            )

            target_domain = (
                target_domain
                .removeprefix(
                    "www."
                )
            )

            return (
                base_domain
                == target_domain
            )

        except Exception:

            return True

    # ========================================================
    # LINK CONTEXT
    # ========================================================

    def _get_link_context(
        self,
        link
    ):
        """
        링크 주변 card/list/div 텍스트 확보.

        날짜나 speaker name이
        링크 자체가 아니라 부모 요소에 있는 경우 대응.
        """

        candidates = [

            link.parent,

            link.find_parent(
                "article"
            ),

            link.find_parent(
                "li"
            ),

            link.find_parent(
                "section"
            ),

            link.find_parent(
                "div"
            ),
        ]

        texts = []

        for item in candidates:

            if item is None:
                continue

            try:

                text = clean_text(
                    item.get_text(
                        " ",
                        strip=True
                    )
                )

            except Exception:

                continue

            if not text:
                continue

            if text in texts:
                continue

            # 너무 큰 부모 div가 걸리면
            # 페이지 전체가 들어올 수 있으므로 제한
            if len(text) > 2000:
                continue

            texts.append(
                text
            )

        return " | ".join(
            texts
        )

    # ========================================================
    # MEMBER MATCH
    # ========================================================

    def _member_matches(
        self,
        text
    ):
        """
        CSV의

            name_en
            aliases

        를 활용해서 해당 인물 발언인지 판별.
        """

        if not text:
            return False

        search_text = (
            str(text)
            .lower()
        )

        candidates = []

        # ----------------------------------------------------
        # Name
        # ----------------------------------------------------

        name_en = self.member.get(
            "name_en"
        )

        if name_en:

            name_en = str(
                name_en
            ).strip()

            if name_en:

                candidates.append(
                    name_en
                )

                # surname
                parts = (
                    name_en.split()
                )

                if parts:

                    surname = (
                        parts[-1]
                    )

                    if len(
                        surname
                    ) >= 4:

                        candidates.append(
                            surname
                        )

        # ----------------------------------------------------
        # Aliases
        # ----------------------------------------------------

        aliases = self.member.get(
            "aliases"
        )

        if aliases:

            aliases = str(
                aliases
            )

            for alias in (
                aliases.split("|")
            ):

                alias = (
                    alias.strip()
                )

                if not alias:
                    continue

                candidates.append(
                    alias
                )

        # ----------------------------------------------------
        # Role EN도 보조적으로 사용 가능
        # ----------------------------------------------------

        role_en = self.member.get(
            "role_en"
        )

        if role_en:

            role_en = str(
                role_en
            ).strip()

            if role_en:

                candidates.append(
                    role_en
                )

        # ----------------------------------------------------
        # 중복 제거
        # ----------------------------------------------------

        candidates = list(
            dict.fromkeys(
                candidates
            )
        )

        return any(

            candidate.lower()
            in search_text

            for candidate
            in candidates

            if candidate
        )

    # ========================================================
    # ARTICLE DETAIL
    # ========================================================

    def _crawl_article(
        self,
        url
    ):

        soup = get_soup(
            url
        )

        page_text = (
            soup.get_text(
                "\n",
                strip=True
            )
            or ""
        )

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title = None

        # h1 우선
        h1 = soup.find(
            "h1"
        )

        if h1:

            title = clean_text(
                h1.get_text(
                    " ",
                    strip=True
                )
            )

        # h1 없으면 title tag
        if not title:

            title_tag = (
                soup.find(
                    "title"
                )
            )

            if title_tag:

                title = clean_text(
                    title_tag.get_text(
                        " ",
                        strip=True
                    )
                )

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        published_at = (
            self._find_date(
                page_text
            )
        )

        # 상세페이지에서 못 찾으면 URL
        if not published_at:

            published_at = (
                self._date_from_url(
                    url
                )
            )

        # ----------------------------------------------------
        # SPEAKER
        # ----------------------------------------------------

        speaker_raw = None

        name_en = self.member.get(
            "name_en"
        )

        if name_en:

            name_en = str(
                name_en
            ).strip()

            if (
                name_en
                and
                name_en.lower()
                in page_text.lower()
            ):

                speaker_raw = (
                    name_en
                )

        # aliases 확인
        if not speaker_raw:

            aliases = self.member.get(
                "aliases"
            )

            if aliases:

                for alias in str(
                    aliases
                ).split("|"):

                    alias = (
                        alias.strip()
                    )

                    if not alias:
                        continue

                    if (
                        alias.lower()
                        in page_text.lower()
                    ):

                        speaker_raw = (
                            name_en
                            or alias
                        )

                        break

        # ----------------------------------------------------
        # BODY
        # ----------------------------------------------------

        text = extract_article_text(
            soup,
            selectors=[

                "article",

                "main",

                ".article-content",

                ".entry-content",

                ".content",

                ".page-content",

                ".body-content",

                "#content",

                "#article",
            ]
        )

        return {

            "published_at":
                published_at,

            "title":
                title,

            "speaker_raw":
                speaker_raw,

            "text":
                text,
        }

    # ========================================================
    # DATE PARSING
    # ========================================================

    def _find_date(
        self,
        text
    ):

        if not text:
            return None

        # ----------------------------------------------------
        # Month DD, YYYY
        # ----------------------------------------------------

        patterns = [

            (
                r"(January|February|March|April|May|June|"
                r"July|August|September|October|November|December)"
                r"\s+\d{1,2},\s+20\d{2}"
            ),

            (
                r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                r"\.?\s+\d{1,2},\s+20\d{2}"
            ),
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE
            )

            if not match:
                continue

            raw_date = (
                match.group(0)
                .replace(
                    ".",
                    ""
                )
            )

            parsed = (
                parse_english_date(
                    raw_date
                )
            )

            if parsed:

                return parsed

        # ----------------------------------------------------
        # YYYY-MM-DD
        # ----------------------------------------------------

        match = re.search(
            r"\b"
            r"(20\d{2})"
            r"[-/]"
            r"(\d{1,2})"
            r"[-/]"
            r"(\d{1,2})"
            r"\b",
            text
        )

        if match:

            year = int(
                match.group(1)
            )

            month = int(
                match.group(2)
            )

            day = int(
                match.group(3)
            )

            if (
                self._valid_date_parts(
                    year,
                    month,
                    day
                )
            ):

                return (
                    f"{year:04d}-"
                    f"{month:02d}-"
                    f"{day:02d}"
                )

        return None

    def _date_from_context(
        self,
        context
    ):

        return self._find_date(
            context
        )

    # ========================================================
    # URL DATE
    # ========================================================

    def _date_from_url(
        self,
        url
    ):
        """
        Fed 공식 사이트 URL 날짜 패턴 지원.

        예:
            lkl260210
                → 2026-02-10

            wil260715
                → 2026-07-15

            20260731
                → 2026-07-31

            sp-20260731-...
                → 2026-07-31
        """

        if not url:
            return None

        url = str(
            url
        )

        # ====================================================
        # 1. YYYYMMDD
        # ====================================================

        matches = re.findall(
            r"(?<!\d)"
            r"(20\d{2})"
            r"(\d{2})"
            r"(\d{2})"
            r"(?!\d)",
            url
        )

        for match in matches:

            year = int(
                match[0]
            )

            month = int(
                match[1]
            )

            day = int(
                match[2]
            )

            if self._valid_date_parts(
                year,
                month,
                day
            ):

                return (
                    f"{year:04d}-"
                    f"{month:02d}-"
                    f"{day:02d}"
                )

        # ====================================================
        # 2. YYMMDD
        #
        # 반드시 앞에 영문자가 있는 형태 위주
        #
        # lkl260210
        # wil260715
        # ====================================================

        matches = re.findall(
            r"[A-Za-z_-]"
            r"(\d{2})"
            r"(\d{2})"
            r"(\d{2})"
            r"(?!\d)",
            url
        )

        for match in matches:

            year = (
                2000
                + int(
                    match[0]
                )
            )

            month = int(
                match[1]
            )

            day = int(
                match[2]
            )

            if self._valid_date_parts(
                year,
                month,
                day
            ):

                return (
                    f"{year:04d}-"
                    f"{month:02d}-"
                    f"{day:02d}"
                )

        return None

    # ========================================================
    # DATE VALIDATION
    # ========================================================

    def _valid_date_parts(
        self,
        year,
        month,
        day
    ):

        if not (
            2000
            <= year
            <= 2100
        ):
            return False

        if not (
            1
            <= month
            <= 12
        ):
            return False

        if not (
            1
            <= day
            <= 31
        ):
            return False

        # 월별 최대일 간단 검증
        if (
            month
            in [
                4,
                6,
                9,
                11,
            ]
            and
            day > 30
        ):
            return False

        if (
            month
            == 2
            and
            day > 29
        ):
            return False

        return True

    # ========================================================
    # DEDUP
    # ========================================================

    def _deduplicate(
        self,
        results
    ):

        unique = {}

        for item in results:

            if not isinstance(
                item,
                dict
            ):
                continue

            url = item.get(
                "url"
            )

            if not url:
                continue

            # 같은 URL이면 더 정보가 많은 쪽 우선
            existing = (
                unique.get(
                    url
                )
            )

            if existing is None:

                unique[
                    url
                ] = item

                continue

            existing_score = (
                self._result_quality_score(
                    existing
                )
            )

            new_score = (
                self._result_quality_score(
                    item
                )
            )

            if (
                new_score
                > existing_score
            ):

                unique[
                    url
                ] = item

        output = list(
            unique.values()
        )

        # ----------------------------------------------------
        # 날짜 최신순
        # 날짜 없는 항목은 뒤로
        # ----------------------------------------------------

        output.sort(
            key=lambda x: (
                x.get(
                    "published_at"
                )
                or "0000-00-00"
            ),
            reverse=True
        )

        return output

    # ========================================================
    # RESULT QUALITY
    # ========================================================

    def _result_quality_score(
        self,
        item
    ):

        score = 0

        if item.get(
            "published_at"
        ):
            score += 2

        if item.get(
            "speaker_raw"
        ):
            score += 2

        if item.get(
            "title"
        ):
            score += 1

        text = (
            item.get(
                "text"
            )
            or ""
        )

        if text:
            score += 2

        if len(text) > 500:
            score += 2

        return score