# ABOUTME: AnthropicLLMProvider — tenacity retries + DTO validation.
# ABOUTME: max_retries=0 on client (PITFALL C7); wrap SDK into domain.
"""Anthropic LLMProvider adapter."""

from __future__ import annotations

from typing import Any, cast

import anthropic
import pydantic

# See `_exceptions_map.py` for why these three aren't imported from the
# top-level `anthropic` module in SDK 0.97.
from anthropic._exceptions import (  # type: ignore[import-not-found]
    DeadlineExceededError,
    OverloadedError,
    ServiceUnavailableError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.application.dtos import CardDTO, NoteDTO
from app.application.exceptions import LLMOutputMalformed
from app.infrastructure.llm._exceptions_map import wrap_sdk_error
from app.infrastructure.llm._response_parser import parse_and_validate
from app.infrastructure.llm.tool_schema import TOOL_DEFINITION
from app.logging_config import get_logger
from app.settings import get_settings

log = get_logger(__name__)

_DEFAULT_MODEL = "claude-opus-4-7"
_MAX_TOKENS = 4096
# Anthropic SDK default timeout is 600s. Tenacity retries
# APITimeoutError up to 3x, so without an explicit cap a stalled
# upstream could hang the request thread for ~30 minutes. 30s is
# generous for a study-app generation call and caps the worst-case
# total under 2 minutes.
_SDK_TIMEOUT_SECONDS = 30.0
_SYSTEM_PROMPT = (
    "You are a study-note and flashcard generator. Call the "
    "generate_note_and_cards tool exactly once with a note and a "
    "non-empty list of cards."
)
_STRICTER_ADDENDUM = (
    " IMPORTANT: the cards array MUST contain at least one card."
)


class AnthropicLLMProvider:
    """LLMProvider Protocol adapter using anthropic SDK + tenacity."""

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        """Build the provider with an optional pre-built SDK client.

        :param client: Pre-built ``anthropic.Anthropic`` instance,
            typically injected by integration tests so respx can
            intercept HTTP. Production callers leave it as ``None``
            and the class builds a default client from
            ``ANTHROPIC_API_KEY`` in settings.
        :param model: Model id; defaults to Claude Opus 4.7.
        """
        if client is None:
            key = get_settings().anthropic_api_key.get_secret_value()
            # max_retries=0 muzzles the SDK's built-in retry loop;
            # without this, SDK retries stack with tenacity and 3x the
            # SC #4 retry counts (PITFALL C7). Tenacity owns all retry
            # policy.
            client = anthropic.Anthropic(
                api_key=key,
                max_retries=0,
                timeout=_SDK_TIMEOUT_SECONDS,
            )
        self._client = client
        self._model = model

    def generate_note_and_cards(
        self,
        source_text: str | None,
        user_prompt: str,
    ) -> tuple[NoteDTO, list[CardDTO]]:
        """Generate a note and Q&A cards from source text + user prompt.

        Delegates the happy-path + semantic retry to
        ``_generate_with_retry``; translates any SDK-layer error to a
        domain exception at this outer boundary (D-03b).

        :param source_text: Extracted study material, or ``None`` for
            TOPIC source kind (LLM generates from prompt alone).
        :param user_prompt: User instruction shaping the note emphasis.
        :returns: ``(NoteDTO, list[CardDTO])`` — list is non-empty.
        :raises LLMRateLimited: After all tenacity retries exhaust on
            429.
        :raises LLMAuthFailed: On 401 / 403 (no retry by design).
        :raises LLMUnreachable: On connection or timeout error, or 5xx
            after retries exhaust.
        :raises LLMContextTooLarge: On a 400 whose body reports
            context-window overflow.
        :raises LLMRequestRejected: On any other permanent 4xx
            (malformed tool schema, not-found, unprocessable) or an
            SDK error subclass not yet in the dispatch table.
        :raises LLMOutputMalformed: When the tool_use output fails DTO
            validation twice (initial + one semantic retry).
        """
        try:
            return self._generate_with_retry(source_text, user_prompt)
        except anthropic.APIError as e:
            raise wrap_sdk_error(e) from e

    def _generate_with_retry(
        self,
        source_text: str | None,
        user_prompt: str,
    ) -> tuple[NoteDTO, list[CardDTO]]:
        """Two-attempt DTO validation with a stricter-prompt retry (D-03a).

        First attempt: the default system prompt. On
        ``pydantic.ValidationError`` log the reason and fall through
        to a second attempt with ``_STRICTER_ADDENDUM`` appended to
        the system prompt. A second failure raises
        ``LLMOutputMalformed``; no third attempt.

        Does NOT catch ``anthropic.APIError`` — those propagate to the
        caller (``generate_note_and_cards``) which owns SDK → domain
        translation.

        :param source_text: Extracted study material, or ``None`` for
            TOPIC source kind.
        :param user_prompt: User instruction shaping the note.
        :returns: ``(NoteDTO, list[CardDTO])`` from whichever attempt
            succeeded.
        :raises LLMOutputMalformed: When both attempts fail DTO
            validation; chains to the second attempt's
            ``pydantic.ValidationError``.
        """
        try:
            resp = self._sdk_call(_SYSTEM_PROMPT, source_text, user_prompt)
            return parse_and_validate(resp)
        except pydantic.ValidationError as ve:
            log.warning(
                "llm.malformed.retrying_stricter",
                validation_error=str(ve),
            )

        # Second attempt — outside the `except` block so an anthropic
        # error here doesn't chain onto the prior ValidationError.
        resp = self._sdk_call(
            _SYSTEM_PROMPT + _STRICTER_ADDENDUM,
            source_text,
            user_prompt,
        )
        try:
            return parse_and_validate(resp)
        except pydantic.ValidationError as e:
            raise LLMOutputMalformed(str(e)) from e

    # Retry whitelist is transients only — 4xx must NOT retry
    # (CONTEXT D-03). Using the parent `APIStatusError` would retry
    # 4xx and break SC #4; keep the explicit tuple below.
    # 5xx coverage: InternalServerError (500 fallback),
    # ServiceUnavailable (503), DeadlineExceeded (504), Overloaded
    # (529) — none are subclasses of InternalServerError, so each
    # must be listed independently or tenacity silently skips them.
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (
                anthropic.RateLimitError,
                anthropic.APIConnectionError,
                anthropic.APITimeoutError,
                anthropic.InternalServerError,
                ServiceUnavailableError,
                OverloadedError,
                DeadlineExceededError,
            )
        ),
        reraise=True,
    )
    def _sdk_call(
        self,
        system: str,
        source_text: str | None,
        user_prompt: str,
    ) -> Any:
        """Call messages.create with tenacity retries on transients."""
        body = (
            f"Source:\n{source_text}\n\nUser prompt: {user_prompt}"
            if source_text is not None
            else f"User prompt: {user_prompt}"
        )
        return self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": body}],
            # ty cannot narrow the SDK's ToolParam TypedDict union
            # against our hand-written dict literal. cast(Any, ...) is
            # the sanctioned escape for SDK-imposed overload shapes.
            tools=[cast(Any, TOOL_DEFINITION)],
            tool_choice=cast(
                Any,
                {"type": "tool", "name": "generate_note_and_cards"},
            ),
        )
