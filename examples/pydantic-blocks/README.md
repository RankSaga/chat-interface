# Pydantic Blocks

Type-safe structured outputs for LLM responses using Pydantic.

## Overview

Pydantic blocks provide:
- **Type-safe validation** at parse time
- **Forward-compatible** handling of unknown block types
- **Structured schemas** that LLMs can reliably generate
- **Streaming support** with block events

## Usage

### Basic Block Creation

```python
from examples.pydantic_blocks.block_schema import ContentBlock

# Create a text block
text_block = ContentBlock(
    type="text",
    data={"content": "Hello [1]"}
)

# Create a table block
table_block = ContentBlock(
    type="table",
    data={
        "headers": ["Name", "Score"],
        "rows": [["Alice", "95"], ["Bob", "87"]]
    }
)
```

### Streaming Block Assembly

```python
from examples.pydantic_blocks.streaming_assembler import StreamingBlockAssembler

assembler = StreamingBlockAssembler()

# Start a block
assembler.start_block("b1", "text")

# Apply deltas
assembler.apply_delta("b1", "content", "Hello ")
assembler.apply_delta("b1", "content", "world")

# End block and get validated ContentBlock
block = assembler.end_block("b1")
# block.type == "text"
# block.data["content"] == "Hello world"
```

### Forward-Compatible Validation

Unknown block types are automatically converted to "unknown" blocks:

```python
# Future block type not yet supported
block = ContentBlock(
    type="future_type",
    data={"new_field": "value"}
)

# Automatically converted to "unknown" type
# block.type == "unknown"
# block.data["raw"]["original_type"] == "future_type"
# Original data is preserved
```

## Block Types

Supported block types:
- `text` - Plain text with inline citations
- `table` - Structured tables
- `list` - Ordered or unordered lists
- `code` - Code blocks with syntax highlighting
- `markdown` - Markdown content
- `quote` - Blockquotes with optional attribution
- `callout` - Info/warning/error/success callouts
- `key_value` - Key-value pairs
- `json` - JSON data display
- `metric` - Metrics with optional delta
- `steps` - Ordered step-by-step instructions
- `media` - Images or videos
- `error` - Error messages
- `divider` - Horizontal dividers

## API Reference

### ContentBlock

Main block class with forward-compatible validation.

**Fields:**
- `type: str` - Block type
- `data: Dict[str, Any]` - Block-specific data

**Methods:**
- `validate_and_normalize()` - Validates and normalizes block data

### StreamingBlockAssembler

Assembles blocks from streaming events.

**Methods:**
- `start_block(block_id, block_type)` - Start tracking a new block
- `apply_delta(block_id, path, value)` - Apply content delta
- `end_block(block_id, partial=False)` - Finalize block
- `get_all_blocks()` - Get all completed blocks
- `close_all_partial(reason)` - Close all open blocks as partial

## Best Practices

1. **Always validate blocks** - Use Pydantic validation for type safety
2. **Handle unknown types** - Unknown types become "unknown" blocks, not errors
3. **Preserve original data** - When validation fails, preserve original data
4. **Use unique IDs** - Each block should have a unique ID for React keys
5. **Stream incrementally** - Use streaming assembler for progressive rendering
