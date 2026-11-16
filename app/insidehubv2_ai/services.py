import logging
import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import status
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import DetailedException
from app.posts.constants import CATEGORIES

from .client import AIUnavailable, complete_draft
from .prompts import build_user_message
from .schemas import DraftRequest, DraftResponse, DraftUsage

logger = logging.getLogger(__name__)

CATEGORY_BY_SLUG = {c["slug"]: c for c in CATEGORIES}
TITLE_MAX_LENGTH = 200


def _day_key(user_id: UUID) -> str:
    return f"ai:drafts:{user_id}:{datetime.now(timezone.utc):%Y-%m-%d}"


async def _take_slot(user_id: UUID) -> int:
    redis = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    try:
        key = _day_key(user_id)
        used = await redis.incr(key)
        if used == 1:
            await redis.expire(key, 60 * 60 * 48)
    except RedisError as exc:
        raise DetailedException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The writing assistant is busy. Try again in a moment.",
        ) from exc
    finally:
        await redis.aclose()

    if used > settings.AI_DRAFTS_PER_DAY:
        raise DetailedException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"You've used today's {settings.AI_DRAFTS_PER_DAY} drafts. "
            "Keep writing from here, or try again tomorrow.",
        )
    return settings.AI_DRAFTS_PER_DAY - used


async def usage_for_user(user_id: UUID) -> DraftUsage:
    redis = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    try:
        raw = await redis.get(_day_key(user_id))
    except RedisError as exc:
        raise DetailedException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The writing assistant is busy. Try again in a moment.",
        ) from exc
    finally:
        await redis.aclose()

    limit = settings.AI_DRAFTS_PER_DAY
    used = min(int(raw or 0), limit)
    return DraftUsage(limit=limit, used=used, remaining=limit - used)


async def _give_back(user_id: UUID) -> None:
    redis = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    try:
        await redis.decr(_day_key(user_id))
    except RedisError:
        logger.warning("Could not return a draft slot for user %s", user_id)
    finally:
        await redis.aclose()


def to_plain_story(title: str, content: str) -> tuple[str, str]:
    title = re.sub(r"\s+", " ", title).strip().strip('"').strip()
    if len(title) > TITLE_MAX_LENGTH:
        title = title[: TITLE_MAX_LENGTH - 3].rsplit(" ", 1)[0]

    paragraphs = []
    for block in re.split(r"\n\s*\n", content.replace("\r\n", "\n").strip()):
        lines = []
        for line in block.split("\n"):
            line = re.sub(r"^#+\s*", "", line.strip())
            line = re.sub(r"^[-*]\s+", "", line)
            line = line.replace("**", "").replace("__", "")
            if line:
                lines.append(line)
        if lines:
            paragraphs.append(" ".join(lines))

    content = "\n\n".join(paragraphs)
    if not title or not content:
        raise ValueError("empty draft")
    return title, content


async def draft_for_user(user_id: UUID, data: DraftRequest) -> DraftResponse:
    if not settings.AI_API_KEY:
        raise DetailedException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The writing assistant isn't switched on yet.",
        )

    message = build_user_message(CATEGORY_BY_SLUG[data.category], data)
    remaining = await _take_slot(user_id)
    try:
        raw = await complete_draft(message)
        title, content = to_plain_story(str(raw.get("title", "")), str(raw.get("content", "")))
    except (AIUnavailable, ValueError):
        await _give_back(user_id)
        raise DetailedException(
            status.HTTP_502_BAD_GATEWAY,
            "The writing assistant couldn't draft this right now. Try again in a moment.",
        )

    logger.info("AI draft for user %s, %d left today", user_id, remaining)
    return DraftResponse(title=title, content=content, remaining_today=remaining)
