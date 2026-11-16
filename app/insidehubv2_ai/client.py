import json
import logging

from openai import AsyncOpenAI, OpenAIError

from app.core.config import settings

from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class AIUnavailable(Exception):
    pass


async def complete_draft(user_message: str) -> dict:
    client = AsyncOpenAI(
        api_key=settings.AI_API_KEY,
        base_url=settings.AI_BASE_URL or None,
        timeout=settings.AI_TIMEOUT_SECONDS,
        max_retries=1,
    )
    try:
        response = await client.chat.completions.create(
            model=settings.AI_MODEL,
            temperature=0.7,
            max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except OpenAIError as exc:
        logger.warning("AI draft request failed: %s", exc)
        raise AIUnavailable from exc

    raw = response.choices[0].message.content or ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("AI draft was not JSON")
        raise AIUnavailable from exc
    if not isinstance(data, dict):
        raise AIUnavailable
    return data
