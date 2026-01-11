"""
Block Utilities: Helper functions for block processing.
"""

from typing import List, Dict, Any, Union
import sys
from pathlib import Path

# Add examples directory to path for imports
examples_dir = Path(__file__).parent.parent / "examples"
sys.path.insert(0, str(examples_dir))

from pydantic_blocks.block_schema import ContentBlock, blocks_to_markdown


def extract_citations_from_text(text: str) -> List[int]:
    """
    Extract citation numbers from text.
    
    Args:
        text: Text with inline citations like [1], [2], [1][2]
        
    Returns:
        List of citation numbers found in text
    """
    import re
    citation_numbers = re.findall(r'\[(\d+)\]', text)
    return [int(n) for n in citation_numbers]


def blocks_to_text(blocks: List[Union[ContentBlock, Dict[str, Any]]]) -> str:
    """
    Convert blocks to plain text (fallback rendering).
    
    Args:
        blocks: List of ContentBlock instances or dicts
        
    Returns:
        Plain text representation
    """
    return blocks_to_markdown(blocks)


def merge_adjacent_text_blocks(blocks: List[ContentBlock]) -> List[ContentBlock]:
    """
    Merge adjacent text blocks into single blocks.
    
    Args:
        blocks: List of content blocks
        
    Returns:
        List with adjacent text blocks merged
    """
    if not blocks:
        return blocks
    
    merged = []
    current_text = ""
    
    for block in blocks:
        if block.type == "text":
            content = block.data.get("content", "")
            if content:
                current_text += content + "\n\n"
        else:
            # Flush accumulated text
            if current_text:
                merged.append(ContentBlock(
                    type="text",
                    data={"content": current_text.strip()}
                ))
                current_text = ""
            merged.append(block)
    
    # Flush remaining text
    if current_text:
        merged.append(ContentBlock(
            type="text",
            data={"content": current_text.strip()}
        ))
    
    return merged
