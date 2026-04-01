from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WebSearchHit:
    title: str
    url: str
    snippet: str


@dataclass(slots=True)
class WebFetchResult:
    url: str
    title: str | None
    text: str
    content_type: str | None
