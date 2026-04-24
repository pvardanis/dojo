# ABOUTME: AnthropicLLMProvider — tenacity retries + DTO validation.
# ABOUTME: max_retries=0 on client (PITFALL C7); wrap SDK into domain.
"""Anthropic LLMProvider adapter."""

from __future__ import annotations

from typing import Any, cast

import anthropic
import pydantic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.application.dtos import CardDTO, NoteDTO
from app.application.exceptions import (
    LLMAuthFailed,
    LLMContextTooLarge,
    LLMOutputMalformed,
    LLMRateLimited,
    LLMRequestRejected,
    LLMUnreachable,
)
from app.infrastructure.llm._exceptions_map import (
    context_payload,
    is_context_overflow,
    rate_limit_payload,
)
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

        On a malformed tool-use response (fails DTO validation), issues
        exactly one additional call with a stricter prompt (D-03a).
        Transient SDK errors (429 / 5xx / connection / timeout) are
        retried up to three times inside ``_sdk_call`` via tenacity
        (D-03). Every other SDK error wraps to a domain exception at
        the outer boundary (D-03b).

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
            (malformed tool schema, not-found, unprocessable).
        :raises LLMOutputMalformed: When the tool_use output fails DTO
            validation twice (initial + one semantic retry).
        """
        try:
            try:
                resp = self._sdk_call(_SYSTEM_PROMPT, source_text, user_prompt)
                return parse_and_validate(resp)
            except pydantic.ValidationError as ve:
                log.warning(
                    "llm.malformed.retrying_stricter",
                    validation_error=str(ve),
                )
                resp = self._sdk_call(
                    _SYSTEM_PROMPT + _STRICTER_ADDENDUM,
                    source_text,
                    user_prompt,
                )
                try:
                    return parse_and_validate(resp)
                except pydantic.ValidationError as e:
                    raise LLMOutputMalformed(str(e)) from e
        except anthropic.RateLimitError as e:
            raise LLMRateLimited(str(e), **rate_limit_payload(e)) from e
        except (
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
        ) as e:
            raise LLMAuthFailed(str(e)) from e
        except (
            anthropic.APIConnectionError,
            anthropic.APITimeoutError,
            anthropic.InternalServerError,
        ) as e:
            raise LLMUnreachable(str(e)) from e
        except anthropic.BadRequestError as e:
            if is_context_overflow(e):
                raise LLMContextTooLarge(str(e), **context_payload(e)) from e
            raise LLMRequestRejected(str(e)) from e
        except (
            anthropic.NotFoundError,
            anthropic.UnprocessableEntityError,
        ) as e:
            raise LLMRequestRejected(str(e)) from e

    # Retry whitelist is transients only — 4xx (Auth, BadRequest,
    # NotFound, UnprocessableEntity) must NOT retry (CONTEXT D-03).
    # Using the parent `APIStatusError` would retry 4xx and break
    # SC #4; keep the exact 4-tuple below.
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (
                anthropic.RateLimitError,
                anthropic.APIConnectionError,
                anthropic.APITimeoutError,
                anthropic.InternalServerError,
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
