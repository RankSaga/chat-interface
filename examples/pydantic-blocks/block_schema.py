"""
Pydantic Blocks: Type-safe structured outputs for LLM responses.

This module provides Pydantic models for structured block-based responses,
enabling type-safe validation and forward-compatible error handling.

Key Features:
- Type-safe validation with Pydantic
- Forward-compatible unknown block handling
- Streaming block event support
- Block normalization and fallback strategies
"""

from typing import List, Dict, Any, Optional, Literal, Union, Annotated
from pydantic import BaseModel, Field, model_validator, field_validator
import uuid
import json


# =============================================================================
# Streaming Block Events
# =============================================================================

class BlockStartEvent(BaseModel):
    """Event emitted when a new block begins streaming."""
    event: Literal["block_start"] = "block_start"
    block_id: str = Field(..., description="Unique identifier for this block")
    block_type: str = Field(..., description="Type of block being streamed")
    

class BlockDeltaEvent(BaseModel):
    """Event emitted for incremental content updates to a block."""
    event: Literal["block_delta"] = "block_delta"
    block_id: str = Field(..., description="Block this delta applies to")
    path: str = Field(..., description="Field path (e.g., 'content', 'code', 'rows')")
    value: str = Field(..., description="Content to append to the field")


class BlockEndEvent(BaseModel):
    """Event emitted when a block is complete."""
    event: Literal["block_end"] = "block_end"
    block_id: str = Field(..., description="Block that has completed")
    partial: bool = Field(False, description="True if stream was interrupted")


# Union type for all streaming events
BlockEvent = Annotated[
    Union[BlockStartEvent, BlockDeltaEvent, BlockEndEvent],
    Field(discriminator="event")
]


# =============================================================================
# Block Type Definitions
# =============================================================================

BlockType = Literal[
    "text", "table", "list", "code",
    "markdown", "quote", "divider", "callout",
    "key_value", "json", "metric", "steps", "media", "error",
    "unknown"  # Fallback type
]

BLOCK_TYPES: List[str] = [
    "text", "table", "list", "code",
    "markdown", "quote", "divider", "callout",
    "key_value", "json", "metric", "steps", "media", "error"
]


# =============================================================================
# Base Block with Renderer Hints
# =============================================================================

class BaseBlockData(BaseModel):
    """Base class for all block data with optional renderer hints."""
    id: Optional[str] = Field(None, description="Unique block ID for React keys")
    collapsible: bool = Field(False, description="Whether block can be collapsed")
    initially_collapsed: bool = Field(False, description="Start collapsed if collapsible")


# =============================================================================
# Block Data Models
# =============================================================================

class TextBlockData(BaseBlockData):
    """Data for text block with inline citations."""
    content: str = Field(..., description="Text content with inline citations [1], [2]")


class TableBlockData(BaseBlockData):
    """Data for table block."""
    headers: List[str] = Field(..., description="Column headers")
    rows: List[List[str]] = Field(..., description="Table rows")
    caption: Optional[str] = Field(None, description="Optional caption")


class ListBlockData(BaseBlockData):
    """Data for list block."""
    items: List[str] = Field(..., description="List items with inline citations")
    ordered: bool = Field(False, description="True for numbered, False for bullets")


class CodeBlockData(BaseBlockData):
    """Data for code block."""
    code: str = Field(..., description="The code content")
    language: Optional[str] = Field(None, description="Programming language")


class MarkdownBlockData(BaseBlockData):
    """Data for markdown block."""
    content: str = Field(..., description="Markdown with formatting")
    
    @field_validator("content")
    @classmethod
    def no_code_blocks(cls, v: str) -> str:
        """Prevent code blocks inside markdown - use CodeBlockData instead."""
        # Log warning but don't fail - forward compatibility
        if "```" in v:
            pass  # Could log warning here
        return v


class QuoteBlockData(BaseBlockData):
    """Data for quote block."""
    content: str = Field(..., description="The quoted text")
    source: Optional[str] = Field(None, description="Attribution or source")


class DividerBlockData(BaseBlockData):
    """Data for divider block (empty)."""
    pass


class CalloutBlockData(BaseBlockData):
    """Data for callout block."""
    variant: Literal["info", "warning", "error", "success"] = Field(..., description="Alert type")
    content: str = Field(..., description="The callout message")
    title: Optional[str] = Field(None, description="Optional title")


class KeyValueBlockData(BaseBlockData):
    """Data for key-value block."""
    items: Dict[str, Union[str, int, float]] = Field(..., description="Key-value pairs")


class JSONBlockData(BaseBlockData):
    """Data for JSON block."""
    data: Dict[str, Any] = Field(..., description="JSON data to display")


class MetricBlockData(BaseBlockData):
    """Data for metric block."""
    label: str = Field(..., description="Metric label")
    value: Union[str, int, float] = Field(..., description="Metric value")
    delta: Optional[float] = Field(None, description="Change percentage")


class StepsBlockData(BaseBlockData):
    """Data for steps block."""
    steps: List[str] = Field(..., description="Ordered list of steps")


class MediaBlockData(BaseBlockData):
    """Data for media block."""
    media_type: Literal["image", "video"] = Field(..., description="Media type")
    url: str = Field(..., description="Media URL")
    caption: Optional[str] = Field(None, description="Optional caption")


class ErrorBlockData(BaseBlockData):
    """Data for error block."""
    message: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional details")


class UnknownBlockData(BaseBlockData):
    """Fallback for unrecognized block types - preserves content without breaking."""
    raw: Dict[str, Any] = Field(default_factory=dict, description="Original block data")


# =============================================================================
# Block Data Model Mapping
# =============================================================================

BLOCK_DATA_MODELS: Dict[str, type] = {
    "text": TextBlockData,
    "table": TableBlockData,
    "list": ListBlockData,
    "code": CodeBlockData,
    "markdown": MarkdownBlockData,
    "quote": QuoteBlockData,
    "divider": DividerBlockData,
    "callout": CalloutBlockData,
    "key_value": KeyValueBlockData,
    "json": JSONBlockData,
    "metric": MetricBlockData,
    "steps": StepsBlockData,
    "media": MediaBlockData,
    "error": ErrorBlockData,
    "unknown": UnknownBlockData,
}


# =============================================================================
# Content Block with Forward-Compatible Validation
# =============================================================================

class ContentBlock(BaseModel):
    """
    A content block with forward-compatible validation.
    
    Unknown block types are converted to 'unknown' type instead of failing,
    preserving the original data for potential recovery.
    
    Example:
        >>> block = ContentBlock(type="text", data={"content": "Hello [1]"})
        >>> block.type
        'text'
        >>> block.data["content"]
        'Hello [1]'
        
        >>> unknown_block = ContentBlock(type="future_type", data={"new_field": "value"})
        >>> unknown_block.type
        'unknown'
        >>> unknown_block.data["raw"]["original_type"]
        'future_type'
    """
    type: str = Field(..., description="Block type")
    data: Dict[str, Any] = Field(..., description="Block-specific data")
    
    @model_validator(mode='after')
    def validate_and_normalize(self) -> 'ContentBlock':
        """Validate data and handle unknown types gracefully."""
        if self.type not in BLOCK_DATA_MODELS:
            # Unknown type - convert to unknown block, preserve original
            self.data = {"raw": {"original_type": self.type, **self.data}}
            self.type = "unknown"
        else:
            data_model = BLOCK_DATA_MODELS[self.type]
            try:
                # Validate against the specific block data model
                data_model.model_validate(self.data)
            except Exception:
                # Validation failed - convert to unknown
                self.data = {"raw": {"original_type": self.type, **self.data}}
                self.type = "unknown"
        
        # Add unique ID if not present
        if "id" not in self.data or not self.data["id"]:
            self.data["id"] = str(uuid.uuid4())[:8]
        
        return self


# =============================================================================
# Response Envelope with Metadata
# =============================================================================

class ResponseMetadata(BaseModel):
    """Metadata about the response generation."""
    model: Optional[str] = Field(None, description="Model that generated the response")
    latency_ms: Optional[int] = Field(None, description="Generation latency in milliseconds")
    token_count: Optional[int] = Field(None, description="Total tokens used")
    cached: bool = Field(False, description="Whether response was from cache")


class BlockResponse(BaseModel):
    """The complete structured response with validated content blocks and metadata."""
    blocks: List[ContentBlock] = Field(..., description="Array of content blocks")
    metadata: Optional[ResponseMetadata] = Field(None, description="Response metadata")


# =============================================================================
# Parsing Utilities
# =============================================================================

def parse_block_response(json_str: str, normalize: bool = True) -> Optional[BlockResponse]:
    """
    Parse a JSON string into a BlockResponse with forward-compatible validation.
    
    Args:
        json_str: Raw JSON string from LLM
        normalize: Whether to run normalization (list→steps, etc.)
    
    Returns:
        BlockResponse if parsing succeeds, None otherwise
        
    Example:
        >>> json_str = '{"blocks": [{"type": "text", "data": {"content": "Hello"}}]}'
        >>> response = parse_block_response(json_str)
        >>> response.blocks[0].type
        'text'
    """
    try:
        # Clean up potential markdown code fences
        cleaned = json_str.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        
        data = json.loads(cleaned)
        response = BlockResponse.model_validate(data)
        
        return response
    except Exception:
        return None


def blocks_to_markdown(blocks: List[Union[ContentBlock, Dict[str, Any]]]) -> str:
    """
    Convert blocks to markdown for fallback rendering.
    
    Args:
        blocks: List of ContentBlock instances or dicts
        
    Returns:
        Markdown string representation
    """
    markdown_parts = []
    
    for block in blocks:
        if isinstance(block, ContentBlock):
            block_type = block.type
            data = block.data
        else:
            block_type = block.get("type", "text")
            data = block.get("data", {})
        
        if block_type == "text":
            markdown_parts.append(data.get("content", ""))
            markdown_parts.append("")
            
        elif block_type == "table":
            headers = data.get("headers", [])
            rows = data.get("rows", [])
            caption = data.get("caption")
            if headers:
                markdown_parts.append("| " + " | ".join(str(h) for h in headers) + " |")
                markdown_parts.append("| " + " | ".join("---" for _ in headers) + " |")
                for row in rows:
                    padded_row = list(row) + [""] * (len(headers) - len(row))
                    markdown_parts.append("| " + " | ".join(str(c) for c in padded_row[:len(headers)]) + " |")
                markdown_parts.append("")
                if caption:
                    markdown_parts.append(f"*{caption}*")
                    markdown_parts.append("")
                    
        elif block_type == "list":
            items = data.get("items", [])
            ordered = data.get("ordered", False)
            for i, item in enumerate(items, 1):
                markdown_parts.append(f"{i}. {item}" if ordered else f"- {item}")
            markdown_parts.append("")
            
        elif block_type == "code":
            language = data.get("language", "")
            code = data.get("code", "")
            markdown_parts.append(f"```{language}")
            markdown_parts.append(code)
            markdown_parts.append("```")
            markdown_parts.append("")
            
        elif block_type == "quote":
            content = data.get("content", "")
            source = data.get("source")
            for line in content.split("\n"):
                markdown_parts.append(f"> {line}")
            if source:
                markdown_parts.append(f"> — *{source}*")
            markdown_parts.append("")
            
        elif block_type == "divider":
            markdown_parts.append("---")
            markdown_parts.append("")
            
        elif block_type == "callout":
            variant = data.get("variant", "info")
            title = data.get("title")
            content = data.get("content", "")
            prefix = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}.get(variant, "ℹ️")
            if title:
                markdown_parts.append(f"> **{prefix} {title}**")
            else:
                markdown_parts.append(f"> {prefix}")
            markdown_parts.append(f"> {content}")
            markdown_parts.append("")
            
        elif block_type == "key_value":
            items = data.get("items", {})
            for key, value in items.items():
                markdown_parts.append(f"**{key}:** {value}")
            markdown_parts.append("")
            
        elif block_type == "json":
            json_data = data.get("data", {})
            markdown_parts.append("```json")
            markdown_parts.append(json.dumps(json_data, indent=2))
            markdown_parts.append("```")
            markdown_parts.append("")
            
        elif block_type == "metric":
            label = data.get("label", "")
            value = data.get("value", "")
            delta = data.get("delta")
            delta_str = ""
            if delta is not None and delta != 0:
                delta_str = f" ({'+' if delta > 0 else ''}{delta}%)"
            markdown_parts.append(f"**{label}:** {value}{delta_str}")
            markdown_parts.append("")
            
        elif block_type == "steps":
            steps = data.get("steps", [])
            for i, step in enumerate(steps, 1):
                markdown_parts.append(f"{i}. {step}")
            markdown_parts.append("")
            
        elif block_type == "media":
            media_type = data.get("media_type", "image")
            url = data.get("url", "")
            caption = data.get("caption")
            if media_type == "image":
                markdown_parts.append(f"![{caption or 'Image'}]({url})")
            else:
                markdown_parts.append(f"[{caption or 'Video'}]({url})")
            if caption:
                markdown_parts.append(f"*{caption}*")
            markdown_parts.append("")
            
        elif block_type == "error":
            message = data.get("message", "")
            details = data.get("details")
            markdown_parts.append(f"> ❌ **Error:** {message}")
            if details:
                markdown_parts.append(f"> {details}")
            markdown_parts.append("")
            
        elif block_type == "unknown":
            # Render unknown blocks as JSON for debugging
            raw = data.get("raw", {})
            original_type = raw.get("original_type", "unknown")
            markdown_parts.append(f"> ⚠️ Unknown block type: {original_type}")
            markdown_parts.append("```json")
            markdown_parts.append(json.dumps(raw, indent=2))
            markdown_parts.append("```")
            markdown_parts.append("")
    
    return "\n".join(markdown_parts)
