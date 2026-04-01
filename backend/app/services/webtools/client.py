from __future__ import annotations

import html
import ipaddress
import logging
import re
import socket
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.core.config import settings
from app.services.webtools.types import WebFetchResult, WebSearchHit


logger = logging.getLogger(__name__)


class _DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[WebSearchHit] = []
        self._current_link: str | None = None
        self._current_title_parts: list[str] = []
        self._in_result_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        if tag == "a" and "result__a" in attr_map.get("class", ""):
            self._in_result_link = True
            self._current_link = attr_map.get("href")
            self._current_title_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_result_link:
            self._current_title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_result_link:
            raw_url = (self._current_link or "").strip()
            title = " ".join(part.strip() for part in self._current_title_parts if part.strip())
            url = _normalize_duckduckgo_url(raw_url)
            if url and title:
                self.results.append(WebSearchHit(title=title, url=url, snippet=""))
            self._in_result_link = False
            self._current_link = None
            self._current_title_parts = []


def _normalize_duckduckgo_url(raw_url: str) -> str | None:
    if not raw_url:
        return None

    parsed = urlparse(raw_url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/l/":
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        if target:
            return unquote(target)
    return raw_url


class WebToolsService:
    def __init__(self) -> None:
        self.enabled = settings.WEB_TOOLS_ENABLED
        self.search_enabled = settings.WEB_SEARCH_ENABLED
        self.fetch_enabled = settings.WEB_FETCH_ENABLED
        self.timeout = settings.WEB_TOOLS_TIMEOUT_SECONDS
        self.max_results = settings.WEB_SEARCH_MAX_RESULTS
        self.max_chars = settings.WEB_FETCH_MAX_CHARS
        self.user_agent = settings.WEB_TOOLS_USER_AGENT
        self.allowed_domains = self._parse_allowed_domains(settings.WEB_ALLOWED_DOMAINS)

    def search_and_fetch(self, query: str, *, max_results: int | None = None) -> list[WebFetchResult]:
        if not (self.enabled and self.search_enabled and self.fetch_enabled):
            return []

        search_hits = self.search(query, max_results=max_results)
        documents: list[WebFetchResult] = []
        for hit in search_hits:
            fetched = self.fetch(hit.url)
            if fetched is not None:
                title = fetched.title or hit.title
                documents.append(
                    WebFetchResult(
                        url=fetched.url,
                        title=title,
                        text=fetched.text,
                        content_type=fetched.content_type,
                    )
                )
        return documents

    def search(self, query: str, *, max_results: int | None = None) -> list[WebSearchHit]:
        if not (self.enabled and self.search_enabled):
            return []

        limit = max(1, min(max_results or self.max_results, self.max_results))
        try:
            with httpx.Client(timeout=self.timeout, headers={"User-Agent": self.user_agent}) as client:
                response = client.get(
                    "https://duckduckgo.com/html/",
                    params={"q": query},
                    follow_redirects=True,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Web search failed: %s", exc)
            return []

        parser = _DuckDuckGoResultParser()
        parser.feed(response.text)

        results: list[WebSearchHit] = []
        for hit in parser.results:
            if self._is_url_allowed(hit.url):
                results.append(hit)
            if len(results) >= limit:
                break
        return results

    def fetch(self, url: str) -> WebFetchResult | None:
        if not (self.enabled and self.fetch_enabled):
            return None

        if not self._is_url_allowed(url):
            return None

        try:
            with httpx.Client(timeout=self.timeout, headers={"User-Agent": self.user_agent}) as client:
                response = client.get(url, follow_redirects=True)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Web fetch failed for %s: %s", url, exc)
            return None

        content_type = response.headers.get("content-type", "")
        is_html = "text/html" in content_type.lower()
        raw_text = response.text if is_html else response.text
        cleaned = self._extract_text(raw_text, is_html=is_html)
        if not cleaned:
            return None

        parsed = urlparse(str(response.url))
        final_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            final_url = f"{final_url}?{parsed.query}"

        title = self._extract_title(response.text) if is_html else None
        return WebFetchResult(
            url=final_url,
            title=title,
            text=cleaned[: self.max_chars],
            content_type=content_type or None,
        )

    def _extract_text(self, content: str, *, is_html: bool) -> str:
        if not content:
            return ""

        if not is_html:
            return content.strip()

        without_script = re.sub(r"<script[\\s\\S]*?</script>", " ", content, flags=re.IGNORECASE)
        without_style = re.sub(r"<style[\\s\\S]*?</style>", " ", without_script, flags=re.IGNORECASE)
        without_tags = re.sub(r"<[^>]+>", " ", without_style)
        unescaped = html.unescape(without_tags)
        return re.sub(r"\\s+", " ", unescaped).strip()

    def _extract_title(self, html_content: str) -> str | None:
        match = re.search(r"<title>(.*?)</title>", html_content, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        title = html.unescape(match.group(1))
        return re.sub(r"\\s+", " ", title).strip() or None

    def _parse_allowed_domains(self, raw: str | None) -> set[str]:
        if not raw:
            return set()
        items = [item.strip().lower() for item in raw.split(",") if item.strip()]
        return set(items)

    def _is_url_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False

        host = (parsed.hostname or "").lower()
        if not host:
            return False

        if self.allowed_domains and not any(host == domain or host.endswith(f".{domain}") for domain in self.allowed_domains):
            return False

        if settings.WEB_BLOCK_PRIVATE_NETWORK and self._is_private_host(host):
            return False

        return True

    def _is_private_host(self, host: str) -> bool:
        try:
            # If host is IP directly.
            ip_obj = ipaddress.ip_address(host)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved
        except ValueError:
            pass

        if host in {"localhost", "127.0.0.1", "::1"}:
            return True

        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            return True

        for info in infos:
            try:
                ip_obj = ipaddress.ip_address(info[4][0])
            except ValueError:
                return True
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                return True

        return False
