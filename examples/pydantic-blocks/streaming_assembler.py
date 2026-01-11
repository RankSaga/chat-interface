"""
Streaming Block Assembler: Assembles blocks from streaming events.

This module provides the StreamingBlockAssembler class that tracks in-progress
blocks and handles the block lifecycle (start → deltas → end).

Key Features:
- Block lifecycle management
- Field accumulation for different block types
- Partial block recovery on stream interruption
- Table row parsing (pipe-delimited)
"""

from typing import Dict, List, Any, Optional, Union
from .block_schema import (
    ContentBlock, 
    BlockStartEvent, 
    BlockDeltaEvent, 
    BlockEndEvent
)


class StreamingBlockAssembler:
    """
    Assembles blocks from streaming events.
    
    Tracks in-progress blocks and handles:
    - Block lifecycle (start → deltas → end)
    - Field accumulation for different block types
    - Partial block recovery on stream interruption
    - Table row parsing (pipe-delimited)
    
    Example:
        >>> assembler = StreamingBlockAssembler()
        >>> assembler.start_block("b1", "text")
        >>> assembler.apply_delta("b1", "content", "Hello ")
        >>> assembler.apply_delta("b1", "content", "world")
        >>> block = assembler.end_block("b1")
        >>> block.type
        'text'
        >>> block.data["content"]
        'Hello world'
    """
    
    def __init__(self):
        self.blocks: Dict[str, Dict[str, Any]] = {}
        self.block_order: List[str] = []  # Track order for rendering
        self.completed_blocks: List[ContentBlock] = []
    
    def start_block(self, block_id: str, block_type: str) -> BlockStartEvent:
        """
        Start tracking a new block.
        
        Args:
            block_id: Unique identifier for the block
            block_type: Type of block (text, code, table, etc.)
            
        Returns:
            BlockStartEvent
        """
        self.blocks[block_id] = {
            "type": block_type,
            "id": block_id,
        }
        self.block_order.append(block_id)
        return BlockStartEvent(block_id=block_id, block_type=block_type)
    
    def apply_delta(self, block_id: str, path: str, value: str) -> Optional[BlockDeltaEvent]:
        """
        Apply a content delta to a block.
        
        Args:
            block_id: Block to update
            path: Field path (e.g., 'content', 'code', 'rows')
            value: Content to append to the field
            
        Returns:
            BlockDeltaEvent or None if block not found
        """
        if block_id not in self.blocks:
            return None
        
        block = self.blocks[block_id]
        block_type = block.get("type", "text")
        
        # Handle different path types
        if path == "rows":
            # Table rows: accumulate as list, value is pipe-delimited
            if "rows" not in block:
                block["rows"] = []
            # Split on | for table cells
            row = [cell.strip() for cell in value.split("|")]
            block["rows"].append(row)
        elif path == "headers":
            # Table headers: pipe-delimited
            block["headers"] = [h.strip() for h in value.split("|")]
        elif path == "items":
            # List items: accumulate as list
            if "items" not in block:
                block["items"] = []
            block["items"].append(value)
        elif path == "steps":
            # Steps: accumulate as list
            if "steps" not in block:
                block["steps"] = []
            block["steps"].append(value)
        elif "." in path:
            # Nested path like "items.0" - for future use
            parts = path.split(".")
            field = parts[0]
            if field not in block:
                block[field] = []
            if isinstance(block[field], list):
                block[field].append(value)
            else:
                block[field] = str(block.get(field, "")) + value
        else:
            # Simple string field (content, code, etc.) - concatenate
            block[path] = str(block.get(path, "")) + value
        
        return BlockDeltaEvent(block_id=block_id, path=path, value=value)
    
    def end_block(self, block_id: str, partial: bool = False) -> Optional[ContentBlock]:
        """
        Finalize a block and return the validated ContentBlock.
        
        Args:
            block_id: The block to finalize
            partial: Whether the stream was interrupted
            
        Returns:
            Validated ContentBlock or None if block not found
        """
        if block_id not in self.blocks:
            return None
        
        block_data = self.blocks.pop(block_id)
        block_type = block_data.pop("type", "text")
        block_id_field = block_data.pop("id", block_id)
        
        # Add the id back into data
        block_data["id"] = block_id_field
        
        if partial:
            # Mark as partial - wrap in error-like structure
            block_data["partial"] = True
        
        try:
            content_block = ContentBlock(type=block_type, data=block_data)
            self.completed_blocks.append(content_block)
            return content_block
        except Exception:
            # Validation failed - return as unknown
            return ContentBlock(
                type="unknown",
                data={"raw": {"original_type": block_type, **block_data}, "id": block_id_field}
            )
    
    def apply_event(
        self, 
        event: Union[BlockStartEvent, BlockDeltaEvent, BlockEndEvent, Dict[str, Any]]
    ) -> Optional[Union[BlockStartEvent, BlockDeltaEvent, ContentBlock]]:
        """
        Apply a streaming event and return the result.
        
        Args:
            event: A block event (start, delta, or end)
            
        Returns:
            - BlockStartEvent for start events
            - BlockDeltaEvent for delta events  
            - ContentBlock for end events (the completed block)
        """
        # Handle dict input
        if isinstance(event, dict):
            event_type = event.get("event")
            if event_type == "block_start":
                return self.start_block(event["block_id"], event["block_type"])
            elif event_type == "block_delta":
                return self.apply_delta(event["block_id"], event["path"], event["value"])
            elif event_type == "block_end":
                return self.end_block(event["block_id"], event.get("partial", False))
            return None
        
        # Handle typed events
        if isinstance(event, BlockStartEvent):
            return self.start_block(event.block_id, event.block_type)
        elif isinstance(event, BlockDeltaEvent):
            return self.apply_delta(event.block_id, event.path, event.value)
        elif isinstance(event, BlockEndEvent):
            return self.end_block(event.block_id, event.partial)
        
        return None
    
    def close_all_partial(self, reason: str = "Stream interrupted") -> List[ContentBlock]:
        """
        Close all open blocks as partial (for stream interruption).
        
        Args:
            reason: Reason for interruption
            
        Returns:
            List of partial blocks that were closed
        """
        partial_blocks = []
        for block_id in list(self.blocks.keys()):
            block = self.end_block(block_id, partial=True)
            if block:
                partial_blocks.append(block)
        return partial_blocks
    
    def get_in_progress_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state of an in-progress block."""
        return self.blocks.get(block_id)
    
    def get_all_blocks(self) -> List[ContentBlock]:
        """Get all completed blocks in order."""
        return self.completed_blocks.copy()
    
    def has_open_blocks(self) -> bool:
        """Check if there are any blocks still being streamed."""
        return len(self.blocks) > 0
