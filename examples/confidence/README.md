# Confidence Scoring

Real-time confidence scoring and citation validation for AI responses.

## Overview

This module provides:
- **Confidence score calculation** based on citation relevance and coverage
- **Citation validation** against retrieved documents
- **Provisional confidence** for streaming responses
- **Citation extraction and mapping**

## Usage

### Confidence Scoring

```python
from examples.confidence.confidence_scorer import ConfidenceScorer

scorer = ConfidenceScorer()

# Calculate confidence score
confidence = scorer.calculate_confidence_score(
    citations=citations,
    enriched_chunks=chunks,
    response_text=response_text
)
# Returns float between 0.0 and 1.0
```

### Citation Validation

```python
from examples.confidence.citation_validator import CitationValidator

validator = CitationValidator()

# Extract citations from response
citations = validator.extract_citations(
    response_text=response_text,
    enriched_chunks=chunks,
    selected_chunks=selected_chunks
)

# Validate citations
validation_result = scorer.validate_citations(
    response_text=response_text,
    citations=citations,
    enriched_chunks=chunks
)
# Returns dict with valid_citations, invalid_citations, etc.
```

### Provisional Confidence (Streaming)

```python
# Calculate provisional confidence during streaming
provisional_confidence = scorer.calculate_provisional_confidence(
    partial_text=partial_text,
    partial_citations=partial_citations,
    enriched_chunks=chunks
)
```

### Citation Filtering

```python
# Filter by relevance score
filtered_citations, filtered_count = validator.filter_by_relevance(
    citations=citations,
    min_relevance_score=0.2
)

# Filter to top tier only
top_tier_citations, filtered_count = validator.filter_top_tier_citations(
    citations=citations,
    selected_chunks=selected_chunks,
    top_tier_threshold=0.98  # 98% of top score
)
```

## Confidence Calculation

Confidence score is calculated as:

```
confidence = (avg_relevance * 0.7) + (coverage * 0.3)
```

Where:
- `avg_relevance`: Average citation relevance score
- `coverage`: Percentage of response with citations (unique citations / sentences)

## API Reference

### ConfidenceScorer

Calculates confidence scores for AI responses.

**Methods:**
- `calculate_confidence_score(citations, enriched_chunks, response_text)` - Calculate final confidence
- `validate_citations(response_text, citations, enriched_chunks)` - Validate citations
- `calculate_provisional_confidence(partial_text, partial_citations, enriched_chunks)` - Provisional confidence

### CitationValidator

Validates citations against retrieved documents.

**Methods:**
- `extract_citation_numbers(response_text)` - Extract citation numbers from text
- `map_citations_to_chunks(citation_numbers, enriched_chunks, selected_chunks)` - Map citations to chunks
- `filter_by_relevance(citations, min_relevance_score)` - Filter by relevance
- `filter_top_tier_citations(citations, selected_chunks, top_tier_threshold)` - Filter to top tier
- `extract_citations(response_text, enriched_chunks, selected_chunks)` - Extract and validate citations

## Best Practices

1. **Calculate during streaming** - Provide provisional confidence for real-time feedback
2. **Validate citations** - Ensure citations match retrieved documents
3. **Filter low relevance** - Remove citations below relevance threshold
4. **Top tier filtering** - Only cite most relevant documents (within 98% of top score)
5. **Show in UI** - Display confidence scores to users (progress bars, badges)
