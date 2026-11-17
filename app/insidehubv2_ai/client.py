import json
import logging
import re

from openai import APIStatusError, AsyncOpenAI, OpenAIError, RateLimitError

from app.core.config import settings

from .usage import TokenUsage

logger = logging.getLogger(__name__)


class AIUnavailable(Exception):
    def __init__(self, reason: str = "provider unavailable", usage: TokenUsage | None = None):
        super().__init__(reason)
        self.reason = reason
        self.usage = usage or TokenUsage()


class AIBusy(AIUnavailable):
    def __init__(self, daily_quota: bool = False, reason: str = "busy", usage: TokenUsage | None = None):
        super().__init__(reason=reason, usage=usage)
        self.daily_quota = daily_quota


def _parse_json_object(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in reply")
    data = json.loads(raw[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")
    return data


def _is_invented_tool_call(exc: APIStatusError) -> bool:
    return exc.status_code == 400 and "tool call validation failed" in str(exc)


def _wait_hint(exc: Exception) -> str:
    match = re.search(r"try again in ([0-9]+m[0-9.]*s|[0-9.]+s)", str(exc), re.I)
    return f" · try again in {match.group(1)}" if match else ""


async def _complete(*, model: str, system_prompt: str, user_message: str, timeout: float, label: str, **extra) -> tuple[str, TokenUsage]:
    client = AsyncOpenAI(
        api_key=settings.AI_API_KEY,
        base_url=settings.AI_BASE_URL or None,
        timeout=timeout,
        max_retries=2,
    )
    request = dict(
        model=model,
        temperature=0.7,
        max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        **extra,
    )
    usage = TokenUsage(model=model)
    try:
        try:
            response = await client.chat.completions.create(**request)
        except APIStatusError as exc:
            # gpt-oss sometimes tries to answer through a tool that wasn't offered; a fresh attempt usually doesn't.
            if not ("tools" in extra and _is_invented_tool_call(exc)):
                raise
            response = await client.chat.completions.create(**request)
    except RateLimitError as exc:
        hint = _wait_hint(exc)
        reason = (
            f"daily free limit reached{hint}"
            if "per day" in str(exc)
            else f"provider busy{hint}"
        )
        raise AIBusy(daily_quota="per day" in str(exc), reason=reason, usage=usage) from exc
    except APIStatusError as exc:
        if exc.status_code == 413:
            raise AIBusy(reason="request too large for provider limits", usage=usage) from exc
        raise AIUnavailable(reason=f"{label} request failed", usage=usage) from exc
    except OpenAIError as exc:
        raise AIUnavailable(reason=f"{label} request failed", usage=usage) from exc

    usage.from_response(model, response.usage)
    return response.choices[0].message.content or "", usage


async def complete_draft(system_prompt: str, user_message: str) -> tuple[dict, TokenUsage]:
    raw, usage = await _complete(
        model=settings.AI_MODEL,
        system_prompt=system_prompt,
        user_message=user_message,
        timeout=settings.AI_TIMEOUT_SECONDS,
        label="draft",
        response_format={"type": "json_object"},
    )
    try:
        return _parse_json_object(raw), usage
    except (ValueError, json.JSONDecodeError) as exc:
        raise AIUnavailable(reason="draft was not valid JSON", usage=usage) from exc


async def research(system_prompt: str, user_message: str) -> tuple[str, TokenUsage]:
    notes, usage = await _complete(
        model=search_model(),
        system_prompt=system_prompt,
        user_message=user_message,
        timeout=settings.AI_SEARCH_TIMEOUT_SECONDS,
        label="research",
        tools=[{"type": "browser_search"}],
    )
    if not notes.strip():
        raise AIUnavailable(reason="web search returned no notes", usage=usage)
    return notes, usage


def search_model() -> str:
    return settings.AI_SEARCH_MODEL or settings.AI_MODEL
