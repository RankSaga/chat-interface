"""
Incremental JSON Parser: Parses streaming JSON tokens into complete objects.

This module handles the challenge of parsing JSON from streaming LLM responses,
where tokens arrive incrementally and JSON may be split across multiple chunks.

Key Features:
- Partial JSON handling (arbitrarily split tokens)
- Multiple JSON objects in one chunk
- Salvage mode for malformed data
- Buffer management with size limits
"""

import json
import re
import uuid
from typing import List, Dict, Any


# Salvage mode threshold - if buffer exceeds this, emit as text block
SALVAGE_BUFFER_THRESHOLD = 10_000  # 10KB


class IncrementalJSONParser:
    """
    Parses streaming JSON tokens into complete objects.
    
    Handles:
    - Partial JSON (arbitrarily split tokens)
    - Multiple JSON objects in one chunk
    - Whitespace between objects
    - Auto-repair for common LLM mistakes
    
    Example:
        >>> parser = IncrementalJSONParser()
        >>> parser.push('{"event":"block_start"')
        []
        >>> parser.push(',"block_id":"b1"}')
        [{'event': 'block_start', 'block_id': 'b1'}]
    """
    
    def __init__(self):
        self.buffer = ""
        self._decoder = json.JSONDecoder()
    
    def push(self, chunk: str) -> List[Dict[str, Any]]:
        """
        Push a chunk of text and return any complete JSON objects found.
        
        Args:
            chunk: Raw text chunk from LLM stream
            
        Returns:
            List of parsed JSON objects (may be empty if no complete objects yet)
        """
        # Strip markdown fences before adding to buffer
        chunk = strip_markdown_fences(chunk)
        self.buffer += chunk
        
        events = []
        while True:
            # Skip leading whitespace
            self.buffer = self.buffer.lstrip()
            if not self.buffer:
                break
            
            try:
                # Try to parse a complete JSON object from the buffer
                obj, idx = self._decoder.raw_decode(self.buffer)
                events.append(obj)
                # Remove parsed object from buffer
                self.buffer = self.buffer[idx:]
            except json.JSONDecodeError:
                # No complete JSON object yet - wait for more tokens
                break
        
        return events
    
    def needs_salvage(self) -> bool:
        """Check if buffer has grown too large without valid JSON."""
        return len(self.buffer) > SALVAGE_BUFFER_THRESHOLD
    
    def salvage(self) -> List[Dict[str, Any]]:
        """
        Emit buffer contents as a text block and reset.
        
        Called when buffer exceeds threshold - guarantees no data loss
        and prevents UI freeze.
        
        Returns:
            List of events to emit the salvaged content as a text block
        """
        if not self.buffer.strip():
            self.buffer = ""
            return []
        
        salvage_id = f"salvaged-{uuid.uuid4().hex[:8]}"
        events = [
            {
                "event": "block_start",
                "block_id": salvage_id,
                "block_type": "text"
            },
            {
                "event": "block_delta",
                "block_id": salvage_id,
                "path": "content",
                "value": self.buffer.strip()
            },
            {
                "event": "block_end",
                "block_id": salvage_id,
                "partial": True
            }
        ]
        self.buffer = ""
        return events
    
    def flush(self) -> List[Dict[str, Any]]:
        """
        Flush any remaining buffer content at end of stream.
        
        Returns:
            Salvage events if buffer has content, empty list otherwise
        """
        if self.buffer.strip():
            return self.salvage()
        return []


def strip_markdown_fences(text: str) -> str:
    """
    Remove markdown code fences from text.
    
    Critical for LLM output - models often wrap JSON in ```json fences
    even when instructed not to.
    
    Args:
        text: Raw text that may contain markdown fences
        
    Returns:
        Text with fences removed
        
    Example:
        >>> strip_markdown_fences('```json\\n{"key":"value"}\\n```')
        '{"key":"value"}'
    """
    # Remove ```json and ``` markers
    text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)
    return text


def normalize_block_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and validate a block event from the LLM.
    
    Ensures event has valid structure. Unknown events are converted
    to block_delta with the original content preserved as JSON.
    
    Args:
        event: Raw event dict from LLM
        
    Returns:
        Normalized event dict that's safe to process
        
    Example:
        >>> event = {"event": "block_start", "block_id": "b1", "block_type": "text"}
        >>> normalize_block_event(event)
        {'event': 'block_start', 'block_id': 'b1', 'block_type': 'text'}
    """
    event_type = event.get("event")
    valid_events = {"block_start", "block_delta", "block_end"}
    
    # Valid event - return as-is
    if event_type in valid_events:
        # Ensure required fields exist
        if event_type == "block_start":
            return {
                "event": "block_start",
                "block_id": event.get("block_id", f"auto-{uuid.uuid4().hex[:8]}"),
                "block_type": event.get("block_type", "text")
            }
        elif event_type == "block_delta":
            return {
                "event": "block_delta",
                "block_id": event.get("block_id", "unknown"),
                "path": event.get("path", "content"),
                "value": str(event.get("value", ""))
            }
        elif event_type == "block_end":
            return {
                "event": "block_end",
                "block_id": event.get("block_id", "unknown"),
                "partial": event.get("partial", False)
            }
    
    # Unknown event - convert to delta with raw content
    return {
        "event": "block_delta",
        "block_id": "unknown",
        "path": "content",
        "value": json.dumps(event)
    }
