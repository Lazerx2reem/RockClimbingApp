"""Drives one coach turn: prompt -> Claude -> tool calls -> streamed reply.

The agentic loop is written out rather than delegated to the SDK's tool runner
because we need to interleave three different things onto a single SSE stream —
text deltas as they arrive, a notice each time the coach looks something up, and
a final persisted message. `anthropic` is imported lazily so the rest of the API
still boots without the package installed, matching how the phase 2 extractor
defers OpenCV.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from datetime import date

from sqlalchemy.orm import Session

from ..config import settings
from ..models import User
from .prompt import build_system_prompt
from .tools import TOOL_DEFINITIONS, run_tool

logger = logging.getLogger(__name__)


def coach_available() -> bool:
    """True when an API key is configured, in settings or the environment."""
    return bool(settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"))


def _client():
    import anthropic  # lazy: keeps the dependency optional at import time

    if settings.anthropic_api_key:
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY itself


def _profile(user: User) -> dict:
    return {
        "display_name": user.display_name,
        "climbing_style": user.climbing_style,
        "home_gym": user.home_gym,
        "grade_range_boulder": user.grade_range_boulder,
        "grade_range_route": user.grade_range_route,
        "goals": user.goals,
    }


def stream_reply(user: User, db: Session, history: list[dict]) -> Iterator[dict]:
    """Yield events for one coach turn.

    Event shapes:
      {"type": "tool",  "name": str}          coach is reading some training data
      {"type": "delta", "text": str}          incremental reply text
      {"type": "complete", "text": str, "tool_calls": list}   turn finished
      {"type": "error", "message": str}       turn failed; nothing more follows
    """
    import anthropic

    # Tools render before `system`, so one breakpoint on the system block caches
    # both. They're identical across every turn of a conversation.
    system = [
        {
            "type": "text",
            "text": build_system_prompt(_profile(user), date.today()),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    client = _client()
    messages: list[dict] = list(history)
    text_parts: list[str] = []
    tool_calls: list[dict] = []

    try:
        for round_index in range(settings.coach_max_tool_rounds + 1):
            with client.messages.stream(
                model=settings.coach_model,
                max_tokens=settings.coach_max_tokens,
                output_config={"effort": settings.coach_effort},
                system=system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    text_parts.append(text)
                    yield {"type": "delta", "text": text}
                final = stream.get_final_message()

            if final.stop_reason == "refusal":
                yield {
                    "type": "error",
                    "message": "The coach declined to answer that one. Try rephrasing.",
                }
                return

            if final.stop_reason != "tool_use":
                break

            if round_index == settings.coach_max_tool_rounds:
                logger.warning(
                    "Coach hit the tool-round ceiling for user %s", user.id
                )
                note = (
                    "\n\n(I ran out of lookups for this question — ask me again "
                    "and I'll pick up where I left off.)"
                )
                text_parts.append(note)
                yield {"type": "delta", "text": note}
                break

            # Echo the assistant turn back verbatim — it carries the tool_use
            # blocks, and on thinking models the thinking blocks too.
            messages.append({"role": "assistant", "content": final.content})

            results = []
            for block in final.content:
                if block.type != "tool_use":
                    continue
                yield {"type": "tool", "name": block.name}
                tool_calls.append({"name": block.name, "input": block.input})
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": run_tool(block.name, block.input, user, db),
                    }
                )
            # All results for one assistant turn go back in a single user message.
            messages.append({"role": "user", "content": results})

    except anthropic.RateLimitError:
        yield {
            "type": "error",
            "message": "The coach is rate limited right now — try again shortly.",
        }
        return
    except anthropic.APIStatusError as exc:
        logger.exception("Coach API error for user %s", user.id)
        yield {"type": "error", "message": f"Coach API error ({exc.status_code})."}
        return
    except anthropic.APIConnectionError:
        yield {"type": "error", "message": "Could not reach the Claude API."}
        return
    except Exception:  # noqa: BLE001 — a dead turn must not kill the stream
        logger.exception("Unexpected coach failure for user %s", user.id)
        yield {"type": "error", "message": "The coach hit an unexpected error."}
        return

    yield {
        "type": "complete",
        "text": "".join(text_parts).strip(),
        "tool_calls": tool_calls,
    }
