"""Tiny OpenRouter chat-completion helper used by all LLM activities.

Why a thin local helper instead of `litellm`/`openai`? Keeps the worker image
slim and avoids vendor-specific quirks. OpenRouter speaks the OpenAI
Chat-Completions API, so a 50-line wrapper is enough.

Failure handling philosophy
---------------------------
- 5xx / connection / 429: transient. We retry inside this function with
  exponential backoff so Temporal's activity-level retries don't burn
  attempts on rate limits that clear in a few seconds. We also send
  `activity.heartbeat()` between attempts so long backoffs don't trip
  Temporal's heartbeat timeout.
- 4xx other than 429 (model gone, bad key, etc.): permanent. We raise
  immediately so Temporal can mark the activity failed without retrying.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from typing import Any, Optional

import httpx
from temporalio import activity

from config import get_settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


_RETRYABLE_STATUSES = {408, 425, 429, 500, 502, 503, 504}
MAX_INTERNAL_RETRIES = 4
INITIAL_BACKOFF_SECONDS = 6.0
HEARTBEAT_INTERVAL_SECONDS = 15


def _safe_heartbeat(detail: dict[str, Any]) -> None:
    try:
        activity.heartbeat(detail)
    except RuntimeError:
        pass


async def chat(
    *,
    system: str,
    user: str,
    response_format_json: bool = False,
    temperature: float = 0.2,
    max_tokens: Optional[int] = 2048,
) -> str:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise LLMError(
            "OPENROUTER_API_KEY is not set. Get a free key at https://openrouter.ai"
        )

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/iwasist",
        "X-Title": "Meeting Assistant",
    }
    body: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    if max_tokens:
        body["max_tokens"] = max_tokens
    if response_format_json:
        body["response_format"] = {"type": "json_object"}

    url = f"{settings.openrouter_base_url}/chat/completions"

    last_error: str = ""
    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, MAX_INTERNAL_RETRIES + 1):
        response: Optional[httpx.Response] = None
        network_exc: Optional[BaseException] = None

        # Heartbeat in the background while we wait for the (potentially slow)
        # OpenRouter response. Otherwise Temporal's heartbeat-timeout safety
        # net trips and the activity gets retried before the response even
        # arrives.
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(stage="calling_llm", attempt=attempt)
        )
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
                response = await client.post(url, headers=headers, json=body)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            network_exc = exc
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        if network_exc is not None:
            last_error = f"{type(network_exc).__name__}: {network_exc}"
            logger.warning(
                "OpenRouter network error (attempt %d/%d): %s",
                attempt,
                MAX_INTERNAL_RETRIES,
                last_error,
            )
            if attempt == MAX_INTERNAL_RETRIES:
                raise LLMError(
                    f"OpenRouter unreachable after {attempt} attempts: {last_error}"
                ) from network_exc
            await _sleep_with_heartbeat(backoff, attempt, "network_error")
            backoff *= 2
            continue

        assert response is not None  # narrow type for static checkers

        if response.status_code < 400:
            data = response.json()
            try:
                choice = data["choices"][0]
                message = choice["message"]
            except (KeyError, IndexError) as exc:
                raise LLMError(f"Unexpected OpenRouter response: {data}") from exc

            finish_reason = choice.get("finish_reason")
            if finish_reason == "length":
                logger.warning(
                    "OpenRouter response was truncated (finish_reason=length, "
                    "model=%s, max_tokens=%s). The JSON repair pass may "
                    "salvage it; if it doesn't, raise max_tokens for this "
                    "activity.",
                    settings.llm_model,
                    max_tokens,
                )

            content = message.get("content")
            if not content:
                # Some free models (especially reasoning ones) return the answer
                # under `reasoning_content` instead of `content`. Try that.
                content = message.get("reasoning_content") or message.get(
                    "reasoning"
                )

            if not content or not isinstance(content, str) or not content.strip():
                # Empty/null content is treated as a transient failure: free
                # models occasionally hit content filters or produce no tokens.
                # Bubble up as LLMError so Temporal's retry policy kicks in.
                last_error = (
                    f"Empty content from OpenRouter (model={settings.llm_model}, "
                    f"finish_reason={data['choices'][0].get('finish_reason')!r})"
                )
                logger.warning(
                    "OpenRouter returned empty content (attempt %d/%d)",
                    attempt,
                    MAX_INTERNAL_RETRIES,
                )
                if attempt == MAX_INTERNAL_RETRIES:
                    raise LLMError(last_error)
                await _sleep_with_heartbeat(backoff, attempt, "empty_content")
                backoff *= 2
                continue

            return content

        text = response.text
        last_error = f"HTTP {response.status_code}: {text}"

        if "unavailable for free" in text or "No endpoints found" in text:
            raise LLMError(
                f"OpenRouter says `{settings.llm_model}` is no longer "
                f"available on the free tier. The free catalog rotates — "
                f"set LLM_MODEL=openrouter/free in .env (auto-selects an "
                f"available free model) or pick one from "
                f"https://openrouter.ai/models?q=free. Raw response: {text}"
            )

        if response.status_code not in _RETRYABLE_STATUSES:
            raise LLMError(f"OpenRouter error {last_error}")

        if attempt == MAX_INTERNAL_RETRIES:
            raise LLMError(
                f"OpenRouter still failing after {attempt} retries — {last_error}"
            )

        wait = backoff + random.uniform(0, backoff / 2)
        logger.warning(
            "OpenRouter %d (attempt %d/%d), backing off %.1fs",
            response.status_code,
            attempt,
            MAX_INTERNAL_RETRIES,
            wait,
        )
        await _sleep_with_heartbeat(
            wait, attempt, f"http_{response.status_code}"
        )
        backoff *= 2

    raise LLMError(f"OpenRouter unreachable: {last_error}")


async def _sleep_with_heartbeat(
    total_seconds: float, attempt: int, reason: str
) -> None:
    """Sleep, heartbeating every few seconds so Temporal sees us alive."""
    remaining = total_seconds
    while remaining > 0:
        chunk = min(remaining, 5.0)
        await asyncio.sleep(chunk)
        remaining -= chunk
        _safe_heartbeat(
            {"stage": "llm_backoff", "attempt": attempt, "reason": reason}
        )


async def _heartbeat_loop(*, stage: str, attempt: int) -> None:
    """Heartbeat every HEARTBEAT_INTERVAL seconds until cancelled.

    Used to keep Temporal aware that the activity is alive while we await a
    long-running HTTP call (free LLMs can take 1-3 minutes for big prompts).
    """
    elapsed = 0
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            elapsed += HEARTBEAT_INTERVAL_SECONDS
            _safe_heartbeat(
                {
                    "stage": stage,
                    "attempt": attempt,
                    "elapsed_seconds": elapsed,
                }
            )
    except asyncio.CancelledError:
        return


_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_json_response(content: Optional[str]) -> Any:
    """Robustly parse a JSON answer from a chat model.

    Free models occasionally wrap JSON in ```json ... ``` fences, add a short
    preamble, OR run out of tokens mid-output (truncated JSON). We try, in
    order:

    1. Strict JSON
    2. Stripped code-fence content
    3. From the first `{` or `[`
    4. Truncation repair: if the response was cut off mid-array of objects,
       trim back to the last complete `}` and close the brackets.

    Anything that still fails raises `LLMError` so Temporal can retry.
    """
    if not content or not isinstance(content, str) or not content.strip():
        raise LLMError("LLM returned empty content; cannot parse JSON")

    candidates: list[str] = [content.strip()]
    fenced = _FENCED_JSON_RE.search(content)
    if fenced:
        candidates.append(fenced.group(1).strip())

    bracket = re.search(r"[{\[]", content)
    if bracket:
        candidates.append(content[bracket.start():].strip())

    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue

    # Truncation-repair pass. We only attempt this on the most-stripped
    # candidate so we don't accidentally chop a valid response.
    repaired = _repair_truncated_json(candidates[-1])
    if repaired is not None:
        try:
            parsed = json.loads(repaired)
            logger.warning(
                "Recovered truncated JSON via repair (%d -> %d chars). The "
                "LLM likely hit max_tokens — bump it if this happens often.",
                len(content),
                len(repaired),
            )
            return parsed
        except json.JSONDecodeError:
            pass

    raise LLMError(f"Could not parse JSON from LLM response: {content[:300]}...")


def _repair_truncated_json(text: str) -> Optional[str]:
    """Best-effort fix for JSON cut off mid-array.

    Strategy: find the LAST `}` that has an unbalanced `{` before it, trim
    everything after, then close any open `[` and `{` brackets in order.
    Returns None if the text can't be repaired.
    """
    if not text:
        return None

    last_close = text.rfind("}")
    if last_close == -1:
        return None

    candidate = text[: last_close + 1]

    # Count outstanding brackets from the start, ignoring those inside strings.
    open_braces = 0
    open_brackets = 0
    in_string = False
    escape = False
    for ch in candidate:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            open_braces += 1
        elif ch == "}":
            open_braces -= 1
        elif ch == "[":
            open_brackets += 1
        elif ch == "]":
            open_brackets -= 1

    if open_braces < 0 or open_brackets < 0:
        return None
    if open_braces == 0 and open_brackets == 0:
        return candidate  # already balanced

    # Drop a trailing comma if the last meaningful character is a `,` after `}`.
    candidate = candidate.rstrip()
    closing = "]" * open_brackets + "}" * open_braces
    return candidate + closing
