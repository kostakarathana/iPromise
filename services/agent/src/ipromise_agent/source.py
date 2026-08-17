"""Deterministic HTML capture and exact-quote grounding."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser


def normalize_visible_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


@dataclass(frozen=True, slots=True)
class CapturedSource:
    url: str
    title: str
    captured_at: datetime
    content_hash: str
    html: str
    visible_text: str
    marked_claims: dict[str, str] = field(default_factory=dict)


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.visible: list[str] = []
        self.title_parts: list[str] = []
        self.marked_claims: dict[str, str] = {}
        self._suppressed_depth = 0
        self._in_title = False
        self._claim_stack: list[tuple[str, str, list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._suppressed_depth += 1
            return
        if self._suppressed_depth:
            return
        if tag == "title":
            self._in_title = True
        attributes = dict(attrs)
        claim_id = attributes.get("data-ipromise-claim")
        if claim_id:
            self._claim_stack.append((tag, claim_id, []))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._suppressed_depth:
            self._suppressed_depth -= 1
            return
        if self._suppressed_depth:
            return
        if tag == "title":
            self._in_title = False
        if self._claim_stack and self._claim_stack[-1][0] == tag:
            _, claim_id, parts = self._claim_stack.pop()
            self.marked_claims[claim_id] = normalize_visible_text(" ".join(parts))

    def handle_data(self, data: str) -> None:
        if self._suppressed_depth:
            return
        text = normalize_visible_text(data)
        if not text:
            return
        self.visible.append(text)
        if self._in_title:
            self.title_parts.append(text)
        for _, _, parts in self._claim_stack:
            parts.append(text)


def parse_capture(*, html: str, url: str, captured_at: datetime) -> CapturedSource:
    parser = _VisibleTextParser()
    parser.feed(html)
    return CapturedSource(
        url=url,
        title=normalize_visible_text(" ".join(parser.title_parts)) or "Untitled source",
        captured_at=captured_at,
        content_hash=f"sha256:{hashlib.sha256(html.encode('utf-8')).hexdigest()}",
        html=html,
        visible_text=normalize_visible_text(" ".join(parser.visible)),
        marked_claims=dict(parser.marked_claims),
    )


def exact_quote_is_grounded(exact_quote: str, capture: CapturedSource) -> bool:
    """Require a literal normalized quote; fuzzy or semantic matches are unsafe."""

    normalized_quote = normalize_visible_text(exact_quote)
    if not normalized_quote:
        return False
    if capture.marked_claims:
        return normalized_quote in capture.marked_claims.values()
    return normalized_quote in capture.visible_text
