"""
Streaming Handler: Handles Server-Sent Events (SSE) streaming from LLM APIs.

This module provides utilities for processing streaming responses from LLM APIs,
handling SSE format, timeouts, and error recovery.

Key Features:
- SSE format parsing
- Timeout management (first chunk, between chunks, total duration)
- Error handling and recovery
- Buffer management
"""

import asyncio
import json
import time
from typing import AsyncIterator, Optional
import httpx


class StreamingHandler:
    """
    Handles streaming responses from LLM service (SSE format).
    
    Provides timeout protection and error handling for streaming responses.
    
    Example:
        >>> handler = StreamingHandler(
        ...     stream_timeout=30.0,
        ...     chunk_timeout=5.0,
        ...     max_duration=120.0
        ... )
        >>> async for chunk in handler.process_stream(response):
        ...     print(chunk)
    """
    
    def __init__(
        self,
        stream_timeout: float = 30.0,
        chunk_timeout: float = 5.0,
        max_duration: float = 120.0
    ):
        """
        Initialize streaming handler.
        
        Args:
            stream_timeout: Timeout for first chunk in seconds
            chunk_timeout: Timeout between chunks in seconds
            max_duration: Maximum total stream duration in seconds
        """
        self.stream_timeout = stream_timeout
        self.chunk_timeout = chunk_timeout
        self.max_duration = max_duration
    
    async def process_stream(
        self,
        response: httpx.Response
    ) -> AsyncIterator[str]:
        """
        Process streaming response from LLM service (SSE format).
        
        Args:
            response: httpx.Response with stream=True
            
        Yields:
            Response text chunks as they arrive
            
        Raises:
            TimeoutError: If stream times out
        """
        stream_start_time = time.time()
        buffer = ""
        received_first_chunk = False
        last_chunk_time = stream_start_time
        
        try:
            async for chunk in self._stream_with_timeout(response, stream_start_time):
                if chunk:
                    buffer += chunk
                    # Process complete lines (SSE format: "data: {...}\n\n")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        
                        # Skip empty lines and comments
                        if not line or line.startswith(":"):
                            continue
                        
                        # Parse SSE data line
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            
                            # Handle [DONE] marker
                            if data_str.strip() == "[DONE]":
                                return
                            
                            try:
                                data = json.loads(data_str)
                                
                                # Extract content from response format
                                choices = data.get("choices", [])
                                if choices and len(choices) > 0:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    finish_reason = choices[0].get("finish_reason")
                                    
                                    # Always yield content first
                                    if content:
                                        yield content
                                        received_first_chunk = True
                                        last_chunk_time = time.time()
                                    
                                    # Check for finish reason
                                    if finish_reason:
                                        return
                            except json.JSONDecodeError:
                                continue
                
                last_chunk_time = time.time()
            
            if not received_first_chunk:
                yield (
                    "Error: The LLM service did not send any response data. "
                    "The service may be overloaded or unresponsive. Please try again."
                )
        
        except (TimeoutError, asyncio.TimeoutError) as e:
            elapsed = time.time() - stream_start_time
            timeout_type = self._determine_timeout_type(str(e))
            error_msg = self._format_timeout_error(timeout_type, elapsed)
            yield f"Error: {error_msg}"
        
        except Exception as e:
            elapsed = time.time() - stream_start_time
            yield f"Error: Error generating response: {str(e)}"
    
    async def _stream_with_timeout(
        self,
        response: httpx.Response,
        stream_start_time: float
    ) -> AsyncIterator[str]:
        """
        Stream chunks with timeout protection.
        
        Args:
            response: httpx.Response with stream=True
            stream_start_time: Start time of the stream
            
        Yields:
            Text chunks from the stream
            
        Raises:
            TimeoutError: If stream times out
        """
        chunk_iter = response.aiter_text()
        last_chunk_time = stream_start_time
        received_first_chunk = False
        
        # Get first chunk with timeout
        try:
            first_chunk = await asyncio.wait_for(
                chunk_iter.__anext__(),
                timeout=self.stream_timeout
            )
            received_first_chunk = True
            last_chunk_time = time.time()
            yield first_chunk
        except asyncio.TimeoutError:
            elapsed = time.time() - stream_start_time
            raise TimeoutError(
                f"The request to the LLM service timed out after {elapsed:.1f} seconds. "
                f"Please try again."
            )
        except StopAsyncIteration:
            return
        
        # Continue with remaining chunks
        try:
            while True:
                # Check maximum stream duration
                current_time = time.time()
                total_elapsed = current_time - stream_start_time
                if total_elapsed > self.max_duration:
                    raise TimeoutError(
                        f"Stream exceeded maximum duration of {self.max_duration}s. "
                        f"Total elapsed: {total_elapsed:.1f}s"
                    )
                
                # Check gap between chunks
                time_since_last_chunk = current_time - last_chunk_time
                if time_since_last_chunk > self.chunk_timeout:
                    raise TimeoutError(
                        f"No chunk received for {self.chunk_timeout}s. "
                        f"The LLM service may have stopped responding. "
                        f"Total elapsed: {total_elapsed:.1f}s"
                    )
                
                # Get next chunk with timeout
                try:
                    chunk = await asyncio.wait_for(
                        chunk_iter.__anext__(),
                        timeout=self.chunk_timeout
                    )
                    last_chunk_time = time.time()
                    yield chunk
                except asyncio.TimeoutError:
                    elapsed = time.time() - stream_start_time
                    raise TimeoutError(
                        f"No chunk received for {self.chunk_timeout}s. "
                        f"The LLM service may have stopped responding. "
                        f"Total elapsed: {elapsed:.1f}s"
                    )
                except StopAsyncIteration:
                    # Stream ended normally
                    break
        except StopAsyncIteration:
            pass
    
    def _determine_timeout_type(self, error_message: str) -> str:
        """
        Determine the type of timeout from error message.
        
        Args:
            error_message: Error message string
            
        Returns:
            Timeout type: 'chunk', 'max_duration', or 'first_chunk'
        """
        error_lower = error_message.lower()
        if "chunk" in error_lower or "gap" in error_lower:
            return "chunk"
        elif "maximum duration" in error_lower or "exceeded" in error_lower:
            return "max_duration"
        else:
            return "first_chunk"
    
    def _format_timeout_error(self, timeout_type: str, elapsed: float) -> str:
        """Format timeout error message based on type."""
        if timeout_type == "chunk":
            return (
                f"No chunk received for {self.chunk_timeout}s. "
                f"The LLM service may have stopped responding. "
                f"Total elapsed: {elapsed:.1f}s"
            )
        elif timeout_type == "max_duration":
            return (
                f"Stream exceeded maximum duration of {self.max_duration}s. "
                f"Total elapsed: {elapsed:.1f}s"
            )
        else:
            return (
                f"The request to the LLM service timed out after {elapsed:.1f} seconds. "
                f"Please try again."
            )
