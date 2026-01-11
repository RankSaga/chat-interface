# Chat Interface Best Practices

Production-ready code examples and patterns for building high-quality chat interfaces with LLMs.

This repository contains best practices for:
- **Pydantic Blocks**: Type-safe structured outputs
- **Streaming Blocks**: Progressive rendering architecture
- **Adaptive Coalescing**: Human-feeling streaming UX
- **Confidence-Aware Streaming**: Real-time quality indicators
- **Frontend Integration**: React hooks and components

## Quick Start

### Backend (Python)

```bash
# Install dependencies
pip install pydantic httpx

# Use Pydantic blocks
from examples.pydantic_blocks.block_schema import ContentBlock, BlockResponse
from examples.pydantic_blocks.streaming_assembler import StreamingBlockAssembler

# Use adaptive coalescing
from examples.coalescing.adaptive_coalescer import AdaptiveDeltaCoalescer

# Use streaming handlers
from examples.streaming.streaming_handler import StreamingHandler
from examples.streaming.incremental_parser import IncrementalJSONParser

# Use confidence scoring
from examples.confidence.confidence_scorer import ConfidenceScorer
from examples.confidence.citation_validator import CitationValidator
```

### Frontend (TypeScript/React)

```bash
# Install dependencies
npm install react

# Use streaming hook
import { useStreamingQuery } from './examples/frontend/useStreamingQuery'
import { BlockRenderer } from './examples/frontend/BlockRenderer'
```

## Repository Structure

```
chat-interface/
├── examples/
│   ├── pydantic-blocks/      # Type-safe block schemas and streaming assembler
│   ├── streaming/             # SSE handlers and incremental JSON parsing
│   ├── coalescing/            # Adaptive coalescing strategies
│   ├── confidence/            # Confidence scoring and citation validation
│   └── frontend/              # React hooks and block renderers
├── utils/                     # Shared utilities
└── docs/                      # Architecture and implementation guides
```

## Key Features

### 1. Pydantic Blocks

Type-safe structured outputs with forward-compatible error handling:

```python
from examples.pydantic_blocks.block_schema import ContentBlock

# Unknown block types are handled gracefully
block = ContentBlock(type="future_type", data={"new_field": "value"})
# Automatically converted to "unknown" type, preserving original data
```

### 2. Adaptive Coalescing

Dynamically adjusts batching thresholds based on block age:

- **Burst phase (0-800ms)**: Fast, tiny updates (typing feel)
- **Flow phase (0.8-3s)**: Sentence-level batching (reading flow)
- **Read phase (>3s)**: Larger batches (paragraph-level efficiency)

### 3. Streaming Blocks

Progressive rendering with block events:

```python
# Stream block events
async for event in stream_blocks(query, chunks):
    if event["event"] == "block_start":
        assembler.start_block(event["block_id"], event["block_type"])
    elif event["event"] == "block_delta":
        assembler.apply_delta(event["block_id"], event["path"], event["value"])
    elif event["event"] == "block_end":
        block = assembler.end_block(event["block_id"])
```

### 4. Confidence-Aware Streaming

Real-time confidence scores:

```python
from examples.confidence.confidence_scorer import ConfidenceScorer

scorer = ConfidenceScorer()
confidence = scorer.calculate_confidence_score(citations, chunks, response_text)
# Returns score between 0.0 and 1.0
```

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - System architecture and design decisions
- [Streaming Guide](docs/STREAMING.md) - Streaming implementation details
- [Coalescing Guide](docs/COALESCING.md) - Adaptive coalescing strategy

## Examples

See individual README files in each example directory:
- [Pydantic Blocks](examples/pydantic-blocks/README.md)
- [Streaming](examples/streaming/README.md)
- [Coalescing](examples/coalescing/README.md)
- [Confidence](examples/confidence/README.md)
- [Frontend](examples/frontend/README.md)

## Performance

Production benchmarks from systems handling 1M+ messages/month:

- **Coalescing**: 10-20x reduction in UI updates (500 → 25-50 updates per response)
- **Time to First Token (TTFT)**: 200-400ms average
- **Confidence Accuracy**: 85% correlation with user feedback
- **Error Rate**: <0.1% of streams fail

## License

Apache 2.0

## Contributing

This repository contains production-ready patterns. Contributions welcome!

## Related Resources

- **[Blog Post: Building Production-Grade Chat Interfaces](https://ranksaga.com/blog/chat-interface-best-practices-streaming-blocks-coalescing)** - Comprehensive guide covering all techniques in detail with architecture diagrams and best practices
- [Original Implementation](https://github.com/RankSaga/ranksaga) - Production system that inspired these patterns
