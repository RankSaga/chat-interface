# Architecture Guide

System architecture and design decisions for chat interface best practices.

## Overview

The chat interface architecture is designed around:
1. **Type-safe structured outputs** (Pydantic blocks)
2. **Progressive rendering** (streaming blocks)
3. **Adaptive batching** (coalescing)
4. **Real-time quality indicators** (confidence scoring)

## System Architecture

```
┌─────────────────┐
│   LLM Service   │
│  (OpenRouter)   │
└────────┬────────┘
         │
         │ SSE Stream
         ▼
┌─────────────────┐
│ Streaming       │
│ Handler         │
│ - SSE parsing   │
│ - Timeouts      │
└────────┬────────┘
         │
         │ Text chunks
         ▼
┌─────────────────┐
│ Incremental     │
│ JSON Parser     │
│ - Partial JSON  │
│ - Salvage mode  │
└────────┬────────┘
         │
         │ Block events
         ▼
┌─────────────────┐
│ Adaptive        │
│ Coalescer       │
│ - Phase-based   │
│ - Block-type    │
└────────┬────────┘
         │
         │ Coalesced chunks
         ▼
┌─────────────────┐
│ Block           │
│ Assembler       │
│ - State mgmt    │
│ - Validation    │
└────────┬────────┘
         │
         │ Completed blocks
         ▼
┌─────────────────┐
│ Confidence      │
│ Scorer          │
│ - Real-time     │
│ - Validation    │
└────────┬────────┘
         │
         │ Blocks + Confidence
         ▼
┌─────────────────┐
│ Frontend        │
│ - React hooks   │
│ - RAF batching  │
│ - Block render  │
└─────────────────┘
```

## Key Components

### 1. Pydantic Blocks

**Purpose**: Type-safe structured outputs with forward-compatible validation

**Key Design Decisions**:
- Unknown block types become "unknown" blocks, not errors
- Original data preserved for debugging
- Self-documenting with field descriptions

**Files**:
- `examples/pydantic-blocks/block_schema.py`
- `examples/pydantic-blocks/streaming_assembler.py`

### 2. Streaming Handlers

**Purpose**: Handle SSE streaming with timeout protection

**Key Design Decisions**:
- Multiple timeout layers (first chunk, between chunks, total)
- Graceful error handling
- Buffer management

**Files**:
- `examples/streaming/streaming_handler.py`
- `examples/streaming/incremental_parser.py`

### 3. Adaptive Coalescing

**Purpose**: Reduce UI updates while maintaining perceived responsiveness

**Key Design Decisions**:
- Phase-based thresholds (burst → flow → read)
- Block-type specific strategies
- Metrics tracking for optimization

**Files**:
- `examples/coalescing/adaptive_coalescer.py`

### 4. Confidence Scoring

**Purpose**: Real-time quality indicators for AI responses

**Key Design Decisions**:
- Weighted scoring (70% relevance, 30% coverage)
- Provisional confidence during streaming
- Citation validation

**Files**:
- `examples/confidence/confidence_scorer.py`
- `examples/confidence/citation_validator.py`

### 5. Frontend Integration

**Purpose**: React hooks and components for streaming UI

**Key Design Decisions**:
- RequestAnimationFrame batching
- Incremental block updates
- Error boundaries

**Files**:
- `examples/frontend/useStreamingQuery.ts`
- `examples/frontend/BlockRenderer.tsx`

## Data Flow

### Streaming Flow

1. **LLM Service** → SSE stream with text chunks
2. **Streaming Handler** → Parses SSE, handles timeouts
3. **Incremental Parser** → Parses JSON events from chunks
4. **Coalescer** → Batches tokens into semantic chunks
5. **Block Assembler** → Assembles blocks from events
6. **Confidence Scorer** → Calculates confidence scores
7. **Frontend** → Renders blocks with RAF batching

### Block Lifecycle

1. **block_start** → Create new block state
2. **block_delta** → Apply incremental updates (coalesced)
3. **block_end** → Finalize block, validate, move to completed

### Confidence Updates

1. **Provisional** → Calculated during streaming (from partial text)
2. **Final** → Calculated at end (from complete response)

## Performance Optimizations

1. **Coalescing**: 10-20x reduction in UI updates
2. **RAF Batching**: Multiple deltas → single render
3. **Incremental Parsing**: Handle partial JSON gracefully
4. **Lazy Rendering**: Blocks render as they complete

## Error Handling

1. **Salvage Mode**: Buffer overflow → emit as text block
2. **Partial Blocks**: Stream interruption → mark as partial
3. **Unknown Blocks**: Invalid types → convert to unknown
4. **Timeout Layers**: Multiple timeouts for different failure modes

## Extension Points

1. **New Block Types**: Add to `BLOCK_DATA_MODELS` in `block_schema.py`
2. **Custom Coalescers**: Implement `DeltaCoalescer` subclass
3. **Confidence Metrics**: Extend `ConfidenceScorer` with new metrics
4. **Frontend Components**: Add block renderers to `BlockRenderer`

## Best Practices

1. **Always validate** - Use Pydantic for type safety
2. **Handle unknowns** - Forward-compatible error handling
3. **Track metrics** - Monitor coalescing ratios, confidence accuracy
4. **Test edge cases** - Partial JSON, timeouts, malformed blocks
5. **Optimize incrementally** - Start simple, add sophistication as needed
