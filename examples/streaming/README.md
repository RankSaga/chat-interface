# Streaming Handlers

Server-Sent Events (SSE) streaming handlers and incremental JSON parsing.

## Overview

This module provides:
- **SSE format parsing** for LLM API responses
- **Incremental JSON parsing** for streaming block events
- **Timeout management** (first chunk, between chunks, total duration)
- **Error handling and recovery**

## Usage

### Streaming Handler

```python
from examples.streaming.streaming_handler import StreamingHandler
import httpx

handler = StreamingHandler(
    stream_timeout=30.0,  # Timeout for first chunk
    chunk_timeout=5.0,    # Timeout between chunks
    max_duration=120.0    # Maximum total duration
)

async with httpx.AsyncClient() as client:
    async with client.stream('POST', url, json=data) as response:
        async for chunk in handler.process_stream(response):
            print(chunk)  # Process text chunks
```

### Incremental JSON Parser

```python
from examples.streaming.incremental_parser import IncrementalJSONParser

parser = IncrementalJSONParser()

# Push chunks incrementally
for chunk in token_stream:
    events = parser.push(chunk)
    for event in events:
        # Process complete JSON events
        if event["event"] == "block_start":
            handle_block_start(event)

# Flush remaining buffer
events = parser.flush()
for event in events:
    process_event(event)
```

### Salvage Mode

When buffer exceeds threshold (10KB), parser automatically salvages content:

```python
if parser.needs_salvage():
    events = parser.salvage()
    # Returns block events to emit buffer as text block
    for event in events:
        yield event
```

## API Reference

### StreamingHandler

Handles SSE streaming with timeout protection.

**Parameters:**
- `stream_timeout: float` - Timeout for first chunk (seconds)
- `chunk_timeout: float` - Timeout between chunks (seconds)
- `max_duration: float` - Maximum total stream duration (seconds)

**Methods:**
- `process_stream(response)` - Process streaming response (async iterator)

### IncrementalJSONParser

Parses streaming JSON tokens into complete objects.

**Methods:**
- `push(chunk)` - Push chunk and return complete JSON objects
- `needs_salvage()` - Check if buffer needs salvaging
- `salvage()` - Emit buffer as text block events
- `flush()` - Flush remaining buffer

### Utility Functions

- `strip_markdown_fences(text)` - Remove markdown code fences
- `normalize_block_event(event)` - Normalize and validate block events

## Best Practices

1. **Use incremental parsing** - Handle partial JSON gracefully
2. **Implement salvage mode** - Prevent buffer overflow and data loss
3. **Multiple timeout layers** - First chunk, between chunks, total duration
4. **Error recovery** - Emit error events in same format as normal events
5. **Buffer management** - Monitor buffer size and salvage when needed
