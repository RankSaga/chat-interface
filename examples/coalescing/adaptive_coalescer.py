"""
Adaptive Delta Coalescing: Human-feeling streaming UX.

This module implements adaptive coalescing that adjusts batching thresholds
based on block age, creating a natural streaming experience.

Key Features:
- Phase-based threshold adjustment (burst → flow → read)
- Block-type specific coalescing strategies
- Metrics tracking for optimization
- Sentence boundary detection for text
"""

import time
import re
from typing import List, Dict, Any, Optional


# =============================================================================
# Regex patterns for sentence detection
# =============================================================================

SENTENCE_END_PATTERN = re.compile(r'[.!?]\s*$')
NEWLINE_PATTERN = re.compile(r'\n$')


# =============================================================================
# Phase timing thresholds (in seconds)
# =============================================================================

BURST_PHASE_END = 0.8  # First 800ms
FLOW_PHASE_END = 3.0   # 0.8-3s
# Read phase: >3s


# =============================================================================
# Adaptive thresholds per phase
# =============================================================================

# Adaptive thresholds per phase for text content
ADAPTIVE_THRESHOLDS_TEXT = {
    "burst": {"max_chars": 20, "max_latency": 0.05, "sentence": False},
    "flow": {"max_chars": 120, "max_latency": 0.2, "sentence": True},
    "read": {"max_chars": 300, "max_latency": 0.4, "sentence": True},
}

# Adaptive thresholds per phase for code content (no sentence detection)
ADAPTIVE_THRESHOLDS_CODE = {
    "burst": {"max_chars": 10, "max_latency": 0.03, "sentence": False},
    "flow": {"max_chars": 60, "max_latency": 0.15, "sentence": False},
    "read": {"max_chars": 120, "max_latency": 0.3, "sentence": False},
}


# =============================================================================
# Base Delta Coalescer
# =============================================================================

class DeltaCoalescer:
    """
    Batches streaming tokens into sentence-level chunks.
    
    Emits on:
    - Sentence boundaries (. ! ?)
    - Newlines
    - Max buffer size (safety)
    - Timeout (latency cap)
    
    Example:
        >>> coalescer = DeltaCoalescer()
        >>> coalescer.push("Hello ")
        []
        >>> coalescer.push("world.")
        ['Hello world.']
    """
    
    def __init__(self, max_chars: int = 120, max_latency_ms: int = 200):
        self.buffer = ""
        self.last_emit = time.time()
        self.max_chars = max_chars
        self.max_latency = max_latency_ms / 1000  # Convert to seconds
        
        # Metrics
        self.tokens_received = 0
        self.deltas_emitted = 0
        self.total_chars_emitted = 0
    
    def push(self, token: str) -> List[str]:
        """
        Push a token and return any coalesced chunks ready to emit.
        
        Args:
            token: Raw token from LLM stream
            
        Returns:
            List of coalesced chunks (usually 0 or 1)
        """
        self.tokens_received += 1
        self.buffer += token
        now = time.time()
        
        should_emit = (
            SENTENCE_END_PATTERN.search(self.buffer)
            or NEWLINE_PATTERN.search(self.buffer)
            or len(self.buffer) >= self.max_chars
            or (now - self.last_emit) >= self.max_latency
        )
        
        if should_emit and self.buffer:
            out = self.buffer
            self.buffer = ""
            self.last_emit = now
            self.deltas_emitted += 1
            self.total_chars_emitted += len(out)
            return [out]
        
        return []
    
    def flush(self) -> List[str]:
        """
        Flush any remaining buffer content.
        
        Call at end of block or stream.
        
        Returns:
            List containing remaining buffer if any
        """
        if self.buffer:
            out = self.buffer
            self.buffer = ""
            self.deltas_emitted += 1
            self.total_chars_emitted += len(out)
            return [out]
        return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get coalescing metrics for logging."""
        avg_delta_size = self.total_chars_emitted / self.deltas_emitted if self.deltas_emitted > 0 else 0
        coalescing_ratio = self.deltas_emitted / self.tokens_received if self.tokens_received > 0 else 0
        
        return {
            "tokens_received": self.tokens_received,
            "deltas_emitted": self.deltas_emitted,
            "avg_delta_size": round(avg_delta_size, 1),
            "coalescing_ratio": round(coalescing_ratio, 3),
        }


# =============================================================================
# Adaptive Delta Coalescer
# =============================================================================

class AdaptiveDeltaCoalescer(DeltaCoalescer):
    """
    Adaptive coalescer that adjusts thresholds based on block age.
    
    Creates a human-feeling streaming experience:
    - First 800ms: Fast, tiny updates (typing feel)
    - 0.8-3s: Sentence-level batching (reading flow)
    - >3s: Larger batches (paragraph-level efficiency)
    
    Example:
        >>> coalescer = AdaptiveDeltaCoalescer(block_start_time=time.time())
        >>> # First few tokens - burst phase
        >>> coalescer.push("Hello")
        ['Hello']
        >>> time.sleep(1)  # Move to flow phase
        >>> coalescer.push(" world.")
        [' world.']
    """
    
    def __init__(self, block_start_time: Optional[float] = None):
        """
        Initialize adaptive coalescer.
        
        Args:
            block_start_time: When the block started streaming. If None, uses current time.
        """
        super().__init__()
        self.block_start = block_start_time if block_start_time is not None else time.time()
        self.emitted_chars = 0  # Track for observability
    
    def _phase(self) -> str:
        """Determine current phase based on block age."""
        age = time.time() - self.block_start
        if age < BURST_PHASE_END:
            return "burst"
        elif age < FLOW_PHASE_END:
            return "flow"
        else:
            return "read"
    
    def _thresholds(self) -> Dict[str, Any]:
        """Get thresholds for current phase."""
        phase = self._phase()
        return ADAPTIVE_THRESHOLDS_TEXT.get(phase, ADAPTIVE_THRESHOLDS_TEXT["flow"])
    
    def push(self, token: str) -> List[str]:
        """
        Push a token with adaptive threshold evaluation.
        
        Args:
            token: Raw token from LLM stream
            
        Returns:
            List of coalesced chunks (usually 0 or 1)
        """
        self.tokens_received += 1
        self.buffer += token
        now = time.time()
        t = self._thresholds()
        
        # Determine if we should emit based on current phase thresholds
        should_emit = (
            len(self.buffer) >= t["max_chars"]
            or (now - self.last_emit) >= t["max_latency"]
            or (t["sentence"] and (
                SENTENCE_END_PATTERN.search(self.buffer)
                or NEWLINE_PATTERN.search(self.buffer)
            ))
        )
        
        if should_emit and self.buffer:
            out = self.buffer
            self.buffer = ""
            self.last_emit = now
            self.deltas_emitted += 1
            self.total_chars_emitted += len(out)
            self.emitted_chars += len(out)
            return [out]
        
        return []
    
    def flush(self) -> List[str]:
        """Flush remaining buffer content."""
        if self.buffer:
            out = self.buffer
            self.buffer = ""
            self.deltas_emitted += 1
            self.total_chars_emitted += len(out)
            self.emitted_chars += len(out)
            return [out]
        return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get adaptive coalescing metrics for logging."""
        metrics = super().get_metrics()
        metrics["block_duration_ms"] = int((time.time() - self.block_start) * 1000)
        metrics["emitted_chars"] = self.emitted_chars
        metrics["final_phase"] = self._phase()
        return metrics


# =============================================================================
# Code-Specific Adaptive Coalescer
# =============================================================================

class AdaptiveDeltaCoalescerCode(AdaptiveDeltaCoalescer):
    """
    Adaptive coalescer for code blocks - never uses sentence detection.
    
    Code blocks use tighter thresholds and flush on newlines only,
    since periods are common in code syntax (e.g., method calls, floats).
    """
    
    def _thresholds(self) -> Dict[str, Any]:
        """Get code-specific thresholds for current phase."""
        phase = self._phase()
        return ADAPTIVE_THRESHOLDS_CODE.get(phase, ADAPTIVE_THRESHOLDS_CODE["flow"])
    
    def push(self, token: str) -> List[str]:
        """
        Push a token with code-specific adaptive threshold evaluation.
        
        Never uses sentence detection - only newlines, size, and latency.
        
        Args:
            token: Raw token from LLM stream
            
        Returns:
            List of coalesced chunks (usually 0 or 1)
        """
        self.tokens_received += 1
        self.buffer += token
        now = time.time()
        t = self._thresholds()
        
        # Code: flush on newline, size, or latency (never sentence)
        should_emit = (
            len(self.buffer) >= t["max_chars"]
            or (now - self.last_emit) >= t["max_latency"]
            or NEWLINE_PATTERN.search(self.buffer)
        )
        
        if should_emit and self.buffer:
            out = self.buffer
            self.buffer = ""
            self.last_emit = now
            self.deltas_emitted += 1
            self.total_chars_emitted += len(out)
            self.emitted_chars += len(out)
            return [out]
        
        return []


# =============================================================================
# Block-Type Specific Coalescers
# =============================================================================

class TableCoalescer(DeltaCoalescer):
    """
    Coalescer for table blocks - flushes per row instead of per sentence.
    
    Tables should emit complete rows, not partial content.
    """
    
    def push(self, token: str) -> List[str]:
        """Push token, flush on newline or pipe (row/cell boundary)."""
        self.tokens_received += 1
        self.buffer += token
        now = time.time()
        
        # Tables flush on newline (row boundary) or max size/latency
        should_emit = (
            "\n" in self.buffer
            or len(self.buffer) >= self.max_chars
            or (now - self.last_emit) >= self.max_latency
        )
        
        if should_emit and self.buffer:
            out = self.buffer
            self.buffer = ""
            self.last_emit = now
            self.deltas_emitted += 1
            self.total_chars_emitted += len(out)
            return [out]
        
        return []


class ListCoalescer(DeltaCoalescer):
    """
    Coalescer for list/steps blocks - flushes per item.
    
    List items should be emitted complete.
    """
    
    def push(self, token: str) -> List[str]:
        """Push token, flush on newline (item boundary)."""
        self.tokens_received += 1
        self.buffer += token
        now = time.time()
        
        # Lists flush on newline (item boundary) or max size/latency
        should_emit = (
            "\n" in self.buffer
            or len(self.buffer) >= self.max_chars
            or (now - self.last_emit) >= self.max_latency
        )
        
        if should_emit and self.buffer:
            out = self.buffer
            self.buffer = ""
            self.last_emit = now
            self.deltas_emitted += 1
            self.total_chars_emitted += len(out)
            return [out]
        
        return []


# =============================================================================
# Coalescer Factory
# =============================================================================

def get_coalescer_for_block_type(
    block_type: str,
    block_start_time: Optional[float] = None,
    use_adaptive: bool = True
) -> DeltaCoalescer:
    """
    Get the appropriate coalescer for a block type.
    
    Args:
        block_type: Block type string (text, code, table, etc.)
        block_start_time: When the block started streaming (for adaptive coalescing)
        use_adaptive: Whether to use adaptive coalescing (default True)
        
    Returns:
        Coalescer instance appropriate for the block type
        
    Example:
        >>> coalescer = get_coalescer_for_block_type("text", time.time())
        >>> isinstance(coalescer, AdaptiveDeltaCoalescer)
        True
        >>> code_coalescer = get_coalescer_for_block_type("code", time.time())
        >>> isinstance(code_coalescer, AdaptiveDeltaCoalescerCode)
        True
    """
    # Use adaptive coalescers by default for better UX
    if use_adaptive:
        if block_type == "code":
            return AdaptiveDeltaCoalescerCode(block_start_time=block_start_time)
        elif block_type == "table":
            # Tables still use row-based flushing but with adaptive timing
            return TableCoalescer()
        elif block_type in ("list", "steps"):
            # Lists still use item-based flushing but with adaptive timing
            return ListCoalescer()
        else:
            # Text, markdown, and other types use full adaptive coalescing
            return AdaptiveDeltaCoalescer(block_start_time=block_start_time)
    
    # Static coalescers for specific block types
    if block_type == "table":
        return TableCoalescer()
    elif block_type == "code":
        return DeltaCoalescer(max_chars=60, max_latency_ms=150)  # Code-specific defaults
    elif block_type in ("list", "steps"):
        return ListCoalescer()
    else:
        # Default sentence-based coalescing for text, markdown, etc.
        return DeltaCoalescer()
