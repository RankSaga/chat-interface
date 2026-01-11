"""Pydantic blocks for type-safe structured outputs."""

from .block_schema import (
    ContentBlock,
    BlockResponse,
    BlockStartEvent,
    BlockDeltaEvent,
    BlockEndEvent,
    parse_block_response,
    blocks_to_markdown,
)
from .streaming_assembler import StreamingBlockAssembler

__all__ = [
    "ContentBlock",
    "BlockResponse",
    "BlockStartEvent",
    "BlockDeltaEvent",
    "BlockEndEvent",
    "StreamingBlockAssembler",
    "parse_block_response",
    "blocks_to_markdown",
]
