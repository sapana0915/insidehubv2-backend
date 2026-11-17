import logging
import re
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import status
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import DetailedException, ValidationException
from app.posts.constants import CATEGORIES

from .client import AIBusy, AIUnavailable, complete_draft, research
from .prompts import RESEARCH_PROMPT, build_research_message, build_user_message, system_prompt
from .schemas import MAX_QUESTIONS, DraftRequest, DraftResponse, DraftSource, DraftUsage
from .usage import TokenUsage, format_ai_log

logger = logging.getLogger(__name__)

CATEGORY_BY_SLUG = {c["slug"]: c for c in CATEGORIES}
TITLE_MAX_LENGTH = 200
QUESTION_MAX_LENGTH = 200
MAX_SOURCES = 5
SOURCE_TITLE_MAX_LENGTH = 200
SOURCE_URL_MAX_LENGTH = 500
KEY_TTL_SECONDS = 60 * 60 * 48


def _day_key(kind: str, user_id: UUID) -> str:
    return f"ai:{kind}:{user_id}:{datetime.now(timezone.utc):%Y-%m-%d}"


def _busy() -> DetailedException:
    return DetailedException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "The writing assistant is busy. Try again in a moment.",
    )


async def _increment(kind: str, user_id: UUID) -> int:
    redis = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    try:
        key = _day_key(kind, user_id)
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, KEY_TTL_SECONDS)
        return count
    except RedisError as exc:
        raise _busy() from exc
    finally:
        await redis.aclose()


async def _count_call(user_id: UUID) -> None:
    if await _increment("calls", user_id) > settings.AI_CALLS_PER_DAY:
        raise DetailedException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "You've used the writing assistant a lot today. Try again tomorrow.",
        )


async def _take_slot(user_id: UUID) -> int:
    used = await _increment("drafts", user_id)
    if used > settings.AI_DRAFTS_PER_DAY:
        await _give_back(user_id)
        raise DetailedException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"You've used today's {settings.AI_DRAFTS_PER_DAY} drafts. "
            "Keep writing from here, or try again tomorrow.",
        )
    return settings.AI_DRAFTS_PER_DAY - used


async def _give_back(user_id: UUID) -> None:
    redis = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    try:
        await redis.decr(_day_key("drafts", user_id))
    except RedisError:
        logger.warning("%s- WARNING could not return a draft slot", user_id)
    finally:
        await redis.aclose()


async def usage_for_user(user_id: UUID) -> DraftUsage:
    redis = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    try:
        raw = await redis.get(_day_key("drafts", user_id))
    except RedisError as exc:
        raise _busy() from exc
    finally:
        await redis.aclose()

    limit = settings.AI_DRAFTS_PER_DAY
    used = min(max(int(raw or 0), 0), limit)
    return DraftUsage(
        limit=limit,
        used=used,
        remaining=limit - used,
        web_search_categories=(
            sorted(settings.web_search_categories) if settings.AI_WEB_SEARCH_ENABLED else []
        ),
    )


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


def to_questions(raw: object) -> list[str]:
    if not isinstance(raw, list):
        raise ValueError("questions is not a list")
    questions = []
    for item in raw:
        text = re.sub(r"\s+", " ", str(item)).strip()
        if text:
            questions.append(text[:QUESTION_MAX_LENGTH])
    if not questions:
        raise ValueError("no questions")
    return questions[:MAX_QUESTIONS]


def to_sources(raw: object, research_notes: str) -> list[DraftSource]:
    if not isinstance(raw, list):
        raise ValueError("sources is not a list")
    sources: list[DraftSource] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not re.match(r"^https?://\S+$", url) or len(url) > SOURCE_URL_MAX_LENGTH or url in seen:
            continue
        if url not in research_notes:
            continue
        title = re.sub(r"\s+", " ", str(item.get("title", ""))).strip() or url
        seen.add(url)
        sources.append(DraftSource(title=title[:SOURCE_TITLE_MAX_LENGTH], url=url))
    if not sources:
        raise ValueError("news draft has no usable sources")
    return sources[:MAX_SOURCES]


def with_sources(content: str, sources: list[DraftSource]) -> str:
    listed = "; ".join(f"{source.title} ({source.url})" for source in sources)
    return f"{content}\n\nSources: {listed}"


def _log_ai(
    *,
    user_id: UUID,
    status: str,
    category_name: str,
    started: float,
    usage: TokenUsage | None = None,
    reason: str | None = None,
    action: str = "AI generated",
) -> None:
    message = format_ai_log(
        user_id=user_id,
        status=status,
        category_name=category_name,
        seconds=time.perf_counter() - started,
        usage=usage,
        reason=reason,
        action=action,
    )
    if status == "SUCCESS":
        logger.info(message)
    else:
        logger.warning(message)


async def draft_for_user(user_id: UUID, data: DraftRequest) -> DraftResponse:
    if not settings.AI_API_KEY:
        raise DetailedException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The writing assistant isn't switched on yet.",
        )

    category = CATEGORY_BY_SLUG[data.category]
    category_name = category["name"]
    web_search = data.use_web_search
    if web_search and not settings.AI_WEB_SEARCH_ENABLED:
        raise ValidationException("Writing about news events isn't switched on.")
    if web_search and data.category not in settings.web_search_categories:
        raise ValidationException("Writing about news events is only available for Tech posts.")

    await _count_call(user_id)
    remaining = await _take_slot(user_id)
    failed = DetailedException(
        status.HTTP_502_BAD_GATEWAY,
        "The writing assistant couldn't draft this right now. Try again in a moment.",
    )
    research_notes: str | None = None
    usage = TokenUsage()
    started = time.perf_counter()
    try:
        if web_search:
            research_notes, research_usage = await research(RESEARCH_PROMPT, build_research_message(data))
            usage.add(research_usage)
        message = build_user_message(category, data, research_notes)
        raw, draft_usage = await complete_draft(system_prompt(web_search), message)
        usage.add(draft_usage)
    except AIBusy as exc:
        await _give_back(user_id)
        usage.add(exc.usage)
        _log_ai(
            user_id=user_id,
            status="FAILED",
            category_name=category_name,
            started=started,
            usage=usage,
            reason=exc.reason,
        )
        raise DetailedException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The writing assistant has reached its limit for now. Try again later today."
            if exc.daily_quota
            else "The writing assistant is busy right now. Try again in a minute.",
        )
    except AIUnavailable as exc:
        await _give_back(user_id)
        usage.add(exc.usage)
        _log_ai(
            user_id=user_id,
            status="FAILED",
            category_name=category_name,
            started=started,
            usage=usage,
            reason=exc.reason,
        )
        raise failed

    reply_status = raw.get("status")
    try:
        if reply_status == "questions":
            if data.answers:
                raise ValueError("asked questions again after the writer answered")
            questions = to_questions(raw.get("questions"))
            await _give_back(user_id)
            _log_ai(
                user_id=user_id,
                status="SUCCESS",
                category_name=category_name,
                started=started,
                usage=usage,
                action=f"AI asked {len(questions)} questions",
            )
            return DraftResponse(status="questions", questions=questions, remaining_today=remaining + 1)
        if reply_status not in (None, "draft"):
            raise ValueError("unknown reply status")
        title, content = to_plain_story(str(raw.get("title", "")), str(raw.get("content", "")))
        sources = to_sources(raw.get("sources"), research_notes or "") if web_search else []
    except ValueError as exc:
        await _give_back(user_id)
        _log_ai(
            user_id=user_id,
            status="FAILED",
            category_name=category_name,
            started=started,
            usage=usage,
            reason=str(exc),
        )
        raise failed

    if sources:
        content = with_sources(content, sources)
    _log_ai(
        user_id=user_id,
        status="SUCCESS",
        category_name=category_name,
        started=started,
        usage=usage,
    )
    return DraftResponse(
        status="draft",
        title=title,
        content=content,
        sources=sources,
        remaining_today=remaining,
    )
