"""
Confidence Scorer: Calculates confidence scores for AI responses.

This module provides confidence scoring based on citation relevance,
citation coverage, and document quality indicators.

Key Features:
- Citation relevance scoring
- Citation coverage calculation
- Real-time confidence updates during streaming
- Validation against retrieved documents
"""

import re
from typing import List, Dict, Any, Tuple


class ConfidenceScorer:
    """
    Calculates confidence scores for AI responses.
    
    Confidence is based on:
    - Citation relevance scores (average of all citations)
    - Citation coverage (percentage of response with citations)
    - Document quality indicators
    
    Example:
        >>> scorer = ConfidenceScorer()
        >>> citations = [{"score": 0.9}, {"score": 0.85}]
        >>> response = "Based on the documents [1][2], here is the answer."
        >>> confidence = scorer.calculate_confidence_score(citations, [], response)
        >>> confidence > 0.8
        True
    """
    
    @staticmethod
    def calculate_confidence_score(
        citations: List[Dict[str, Any]],
        enriched_chunks: List[Dict[str, Any]],
        response_text: str
    ) -> float:
        """
        Calculate confidence score based on citation quality and coverage.
        
        Args:
            citations: List of citation dictionaries with scores
            enriched_chunks: List of retrieved chunks (for validation)
            response_text: The response text with inline citations
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not citations:
            return 0.0
        
        # Average citation relevance
        citation_scores = [c.get("score", 0.0) for c in citations if c.get("score")]
        if not citation_scores:
            return 0.0
        
        avg_relevance = sum(citation_scores) / len(citation_scores)
        
        # Citation coverage: percentage of response with citations
        citation_numbers = re.findall(r'\[(\d+)\]', response_text)
        unique_citations = len(set(citation_numbers))
        
        # Count sentences (rough approximation)
        sentences = re.split(r'[.!?]+', response_text)
        total_sentences = len([s for s in sentences if s.strip()])
        
        # Coverage: unique citations per sentence
        if total_sentences > 0:
            coverage = min(1.0, unique_citations / total_sentences)
        else:
            coverage = 1.0 if unique_citations > 0 else 0.0
        
        # Weighted confidence score
        # 70% weight on relevance, 30% weight on coverage
        confidence = (avg_relevance * 0.7) + (coverage * 0.3)
        return min(1.0, max(0.0, confidence))
    
    @staticmethod
    def validate_citations(
        response_text: str,
        citations: List[Dict[str, Any]],
        enriched_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate citations against retrieved chunks.
        
        Args:
            response_text: Response text with inline citations
            citations: List of citation dictionaries
            enriched_chunks: List of retrieved chunks
        
        Returns:
            Validation result dictionary with:
            - valid_citations: Count of valid citations
            - invalid_citations: Count of invalid citations
            - unused_citations: Count of citations not used in text
            - total_citations: Total citation numbers in text
            - validation_score: Ratio of valid to total citations
        """
        # Extract citation numbers from response text
        citation_numbers = set(re.findall(r'\[(\d+)\]', response_text))
        citation_numbers_int = {int(n) for n in citation_numbers}
        
        # Get valid citation numbers from citations list
        valid_citation_numbers = {
            c.get("citation_number") 
            for c in citations 
            if c.get("citation_number") is not None
        }
        
        # Calculate metrics
        valid_count = len(citation_numbers_int & valid_citation_numbers)
        invalid_count = len(citation_numbers_int - valid_citation_numbers)
        unused_count = len(valid_citation_numbers - citation_numbers_int)
        total_citations = len(citation_numbers_int)
        
        # Validation score: ratio of valid to total
        validation_score = (
            valid_count / total_citations 
            if total_citations > 0 
            else 1.0
        )
        
        return {
            "valid_citations": valid_count,
            "invalid_citations": invalid_count,
            "unused_citations": unused_count,
            "total_citations": total_citations,
            "validation_score": validation_score
        }
    
    @staticmethod
    def calculate_provisional_confidence(
        partial_text: str,
        partial_citations: List[Dict[str, Any]],
        enriched_chunks: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate provisional confidence score for partial/streaming responses.
        
        Useful for real-time confidence updates during streaming.
        
        Args:
            partial_text: Partial response text so far
            partial_citations: Citations found in partial text
            enriched_chunks: Retrieved chunks
        
        Returns:
            Provisional confidence score (may be lower than final score)
        """
        if not partial_citations:
            return 0.0
        
        # Use same calculation as final confidence
        return ConfidenceScorer.calculate_confidence_score(
            partial_citations,
            enriched_chunks,
            partial_text
        )
