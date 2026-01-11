"""
Citation Validator: Validates citations against retrieved documents.

This module provides citation extraction and validation logic,
ensuring citations in responses match retrieved document chunks.

Key Features:
- Citation extraction from response text
- Citation-to-chunk mapping
- Relevance score filtering
- Top-tier citation filtering
"""

import re
from typing import List, Dict, Any, Set, Tuple


class CitationValidator:
    """
    Validates citations against retrieved chunks.
    
    Ensures citations in responses are valid and relevant to the query.
    """
    
    @staticmethod
    def extract_citation_numbers(response_text: str) -> Set[int]:
        """
        Extract citation numbers from response text.
        
        Args:
            response_text: Response text with inline citations like [1], [2], [1][2]
        
        Returns:
            Set of citation numbers found in text
            
        Example:
            >>> CitationValidator.extract_citation_numbers("Based on [1][2], here is the answer.")
            {1, 2}
        """
        citation_numbers = re.findall(r'\[(\d+)\]', response_text)
        return {int(n) for n in citation_numbers}
    
    @staticmethod
    def map_citations_to_chunks(
        citation_numbers: Set[int],
        enriched_chunks: List[Dict[str, Any]],
        selected_chunks: List[Dict[str, Any]]
    ) -> Dict[int, Dict[str, Any]]:
        """
        Map citation numbers to chunk dictionaries.
        
        Args:
            citation_numbers: Set of citation numbers to map
            enriched_chunks: All enriched chunks
            selected_chunks: Chunks that were selected and sent to LLM
        
        Returns:
            Dictionary mapping citation numbers to chunks
        """
        citation_map = {}
        
        # Create index of chunks by citation number
        # Citation numbers typically start at 1, chunks are 0-indexed
        for i, chunk in enumerate(selected_chunks, start=1):
            if i in citation_numbers:
                citation_map[i] = chunk
        
        return citation_map
    
    @staticmethod
    def filter_by_relevance(
        citations: List[Dict[str, Any]],
        min_relevance_score: float = 0.2
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Filter citations by relevance score.
        
        Args:
            citations: List of citation dictionaries
            min_relevance_score: Minimum relevance score threshold
        
        Returns:
            Tuple of (filtered_citations, filtered_count)
        """
        filtered = []
        filtered_count = 0
        
        for citation in citations:
            score = citation.get("score", 0.0)
            if score >= min_relevance_score:
                filtered.append(citation)
            else:
                filtered_count += 1
        
        return filtered, filtered_count
    
    @staticmethod
    def filter_top_tier_citations(
        citations: List[Dict[str, Any]],
        selected_chunks: List[Dict[str, Any]],
        top_tier_threshold: float = 0.98
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Filter citations to only the top tier by relevance score.
        
        Only keeps citations to chunks within a percentage of the top score.
        This prevents citing less relevant documents.
        
        Args:
            citations: List of citation dictionaries
            selected_chunks: Chunks that were selected
            top_tier_threshold: Percentage of top score (0.98 = 98%)
        
        Returns:
            Tuple of (filtered_citations, filtered_count)
        """
        if not selected_chunks:
            return citations, 0
        
        # Get top score
        scores = sorted([c.get("score", 0.0) for c in selected_chunks], reverse=True)
        top_score = scores[0] if scores else 0.0
        
        if top_score == 0:
            return citations, 0
        
        # Calculate threshold
        min_top_tier_score = top_score * top_tier_threshold
        
        filtered = []
        filtered_count = 0
        
        for citation in citations:
            score = citation.get("score", 0.0)
            if score >= min_top_tier_score:
                filtered.append(citation)
            else:
                filtered_count += 1
        
        return filtered, filtered_count
    
    @staticmethod
    def extract_citations(
        response_text: str,
        enriched_chunks: List[Dict[str, Any]],
        selected_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract and validate citations from response text.
        
        Args:
            response_text: Response text with inline citations
            enriched_chunks: All enriched chunks
            selected_chunks: Chunks that were selected and sent to LLM
        
        Returns:
            List of citation dictionaries with citation_number, content, score, etc.
        """
        citation_numbers = CitationValidator.extract_citation_numbers(response_text)
        citation_map = CitationValidator.map_citations_to_chunks(
            citation_numbers,
            enriched_chunks,
            selected_chunks
        )
        
        citations = []
        for cite_num in sorted(citation_numbers):
            chunk = citation_map.get(cite_num)
            if chunk:
                citations.append({
                    "citation_number": cite_num,
                    "content": chunk.get("content", ""),
                    "score": chunk.get("score", 0.0),
                    "document": chunk.get("document", {}),
                    "document_id": chunk.get("metadata", {}).get("document_id"),
                    "chunk_id": chunk.get("id"),
                    "metadata": chunk.get("metadata", {})
                })
        
        return citations
