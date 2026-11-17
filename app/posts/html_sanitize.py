"""Sanitize user-authored post HTML (TipTap output)."""

from __future__ import annotations

import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "strike",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "a",
    "span",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel", "target"],
    "span": ["style"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

_CSS_SANITIZER = CSSSanitizer(allowed_css_properties=["font-size"])

_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_post_html(value: str) -> str:
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=_CSS_SANITIZER,
        strip=True,
    ).strip()


def html_to_plain(value: str) -> str:
    text = _TAG_RE.sub(" ", value)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    return re.sub(r"\s+", " ", text).strip()


def is_blank_html(value: str) -> bool:
    return not html_to_plain(value)
