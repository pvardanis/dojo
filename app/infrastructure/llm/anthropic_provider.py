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
        """Build with a muzzled client (test-seam `client=...`)."""
        if client is None:
            key = get_settings().anthropic_api_key.get_secret_value()
            client = anthropic.Anthropic(api_key=key, max_retries=0)
        self._client = client
        self._model = model

    def generate_note_and_cards(
        self,
        source_text: str | None,
        user_prompt: str,
    ) -> tuple[NoteDTO, list[CardDTO]]:
        """Generate a note + cards; one semantic retry on malformed."""
        try:
            try:
                resp = self._sdk_call(_SYSTEM_PROMPT, source_text, user_prompt)
                return parse_and_validate(resp)
            except pydantic.ValidationError:
                log.warning("llm.malformed.retrying_stricter")
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
                raise LLMContextTooLarge(str(e)) from e
            raise LLMRequestRejected(str(e)) from e
        except (
            anthropic.NotFoundError,
            anthropic.UnprocessableEntityError,
        ) as e:
            raise LLMRequestRejected(str(e)) from e

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
            tools=[cast(Any, TOOL_DEFINITION)],
            tool_choice=cast(
                Any,
                {"type": "tool", "name": "generate_note_and_cards"},
            ),
        )
