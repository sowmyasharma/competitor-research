"""Helpers for consuming n8n Chat Trigger streaming responses."""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator


ORCHESTRATOR_NODE_NAME = "Competitor Research Orchestrator"
STREAM_EVENT_TYPES = frozenset(("begin", "item", "end", "error"))


def is_stream_event(line: str) -> bool:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return False
    return isinstance(event, dict) and event.get("type") in STREAM_EVENT_TYPES


def iter_orchestrator_chunks(lines: Iterable[str | None]) -> Iterator[str]:
    received_chunk = False

    for line in lines:
        if not line or not line.strip():
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("n8n returned invalid streaming data.") from error

        if not isinstance(event, dict):
            raise ValueError("n8n returned an invalid streaming event.")

        event_type = event.get("type")
        metadata = event.get("metadata")
        node_name = metadata.get("nodeName") if isinstance(metadata, dict) else None

        if event_type == "error" and node_name in (None, ORCHESTRATOR_NODE_NAME):
            message = event.get("content")
            raise ValueError(message if isinstance(message, str) and message else "The research workflow failed.")

        if node_name != ORCHESTRATOR_NODE_NAME:
            continue

        if event_type == "item":
            content = event.get("content")
            if not isinstance(content, str):
                raise ValueError("n8n returned a streaming chunk without text content.")
            if content:
                received_chunk = True
                yield content
        elif event_type not in ("begin", "end"):
            raise ValueError("n8n returned an unsupported streaming event.")

    if not received_chunk:
        raise ValueError(
            "No response chunks came from the Competitor Research Orchestrator. "
            "Check that the Chat Trigger and its chat model have streaming enabled."
        )
