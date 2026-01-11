# Adaptive Coalescing

Human-feeling streaming UX through adaptive batching thresholds.

## Overview

Adaptive coalescing reduces UI updates by 10-20x while maintaining perceived responsiveness by adjusting batching thresholds based on block age.

## The Three Phases

1. **Burst Phase (0-800ms)**: Fast, tiny updates (typing feel)
   - Max chars: 20
   - Max latency: 50ms
   - No sentence detection

2. **Flow Phase (0.8-3s)**: Sentence-level batching (reading flow)
   - Max chars: 120
   - Max latency: 200ms
   - Sentence detection enabled

3. **Read Phase (>3s)**: Larger batches (paragraph-level efficiency)
   - Max chars: 300
   - Max latency: 400ms
   - Sentence detection enabled

## Usage

### Basic Adaptive Coalescing

```python
from examples.coalescing.adaptive_coalescer import AdaptiveDeltaCoalescer
import time

coalescer = AdaptiveDeltaCoalescer(block_start_time=time.time())

# Push tokens - coalescing happens automatically
for token in token_stream:
    chunks = coalescer.push(token)
    for chunk in chunks:
        yield chunk  # Emit coalesced chunks

# Flush remaining buffer
for chunk in coalescer.flush():
    yield chunk
```

### Block-Type Specific Coalescing

```python
from examples.coalescing.adaptive_coalescer import get_coalescer_for_block_type

# Get appropriate coalescer for block type
coalescer = get_coalescer_for_block_type("text", block_start_time=time.time())
# Returns AdaptiveDeltaCoalescer

code_coalescer = get_coalescer_for_block_type("code", block_start_time=time.time())
# Returns AdaptiveDeltaCoalescerCode (no sentence detection)
```

### Metrics Tracking

```python
# Get coalescing metrics
metrics = coalescer.get_metrics()
# {
#   "tokens_received": 500,
#   "deltas_emitted": 25,
#   "avg_delta_size": 120.5,
#   "coalescing_ratio": 0.05,
#   "block_duration_ms": 2500,
#   "emitted_chars": 3012,
#   "final_phase": "flow"
# }
```

## Performance Impact

- **Without coalescing**: 500-1000 updates per response
- **With static coalescing**: 50-100 updates per response
- **With adaptive coalescing**: 20-50 updates per response (with better UX)

## API Reference

### AdaptiveDeltaCoalescer

Main adaptive coalescer class.

**Methods:**
- `push(token)` - Push token and return coalesced chunks
- `flush()` - Flush remaining buffer
- `get_metrics()` - Get coalescing metrics

### Block-Type Specific Coalescers

- `AdaptiveDeltaCoalescerCode` - For code blocks (no sentence detection)
- `TableCoalescer` - For table blocks (row-based flushing)
- `ListCoalescer` - For list blocks (item-based flushing)

### Factory Function

- `get_coalescer_for_block_type(block_type, block_start_time, use_adaptive)` - Get appropriate coalescer

## Best Practices

1. **Use adaptive by default** - Better UX than static thresholds
2. **Track metrics** - Monitor coalescing ratios to optimize thresholds
3. **Respect latency caps** - Always respect max_latency to prevent perceived lag
4. **Flush on end** - Always flush remaining buffer when blocks complete
5. **Block-type specific** - Use different coalescers for code vs text
