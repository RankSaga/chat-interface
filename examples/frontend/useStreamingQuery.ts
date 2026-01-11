/**
 * useStreamingQuery: React hook for streaming chat queries with block support.
 * 
 * This hook handles:
 * - Server-Sent Events (SSE) streaming
 * - Block-based progressive rendering
 * - RequestAnimationFrame batching for smooth UI updates
 * - Confidence score tracking
 * - Error handling and recovery
 * 
 * @example
 * ```tsx
 * function ChatComponent() {
 *   const { streamQuery, stopStreaming, confidence, blocks } = useStreamingQuery();
 *   
 *   const handleSubmit = async (query: string) => {
 *     await streamQuery(query, {
 *       onMessageUpdate: (updates) => {
 *         setMessage(prev => ({ ...prev, ...updates }));
 *       },
 *       onError: (error) => console.error(error),
 *     });
 *   };
 *   
 *   return (
 *     <div>
 *       <BlockRenderer blocks={blocks} />
 *       <ConfidenceIndicator score={confidence} />
 *     </div>
 *   );
 * }
 * ```
 */

import { useRef, useCallback, useState } from 'react'

// Types
export type BlockType = 
  | 'text' | 'table' | 'list' | 'code' | 'markdown' 
  | 'quote' | 'divider' | 'callout' | 'key_value' 
  | 'json' | 'metric' | 'steps' | 'media' | 'error' | 'unknown'

export interface ContentBlock {
  type: BlockType
  data: {
    id?: string
    [key: string]: any
  }
}

export interface StreamingBlockState {
  block_id: string
  block_type: BlockType
  data: Record<string, unknown>
  streaming: boolean
  partial: boolean
}

export interface Citation {
  citation_number: number
  content: string
  score: number
  document?: {
    filename?: string
    page?: number
  }
  document_id?: string
  chunk_id?: string
  metadata?: Record<string, any>
}

export interface Message {
  content: string
  blocks?: ContentBlock[]
  citations?: Citation[]
  streaming?: boolean
  confidence?: number
}

type UseStreamingQueryOptions = {
  token: string
  conversationId?: string | null
  folderId?: string
  onError: (error: string) => void
  onAuthError?: () => void
  onConversationIdChange?: (conversationId: string) => void
  onMessageUpdate: (updates: Partial<Message>) => void
  onUserMessageId?: (messageId: string) => void
  onAssistantMessageId?: (messageId: string) => void
}

const STREAM_TIMEOUT = 60000 // 60 seconds

export function useStreamingQuery() {
  const streamReaderRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null)
  const stopStreamingRef = useRef<boolean>(false)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [confidence, setConfidence] = useState<number>(0)

  const streamQuery = useCallback(
    async (query: string, options: UseStreamingQueryOptions) => {
      const {
        token,
        conversationId,
        folderId,
        onError,
        onAuthError,
        onConversationIdChange,
        onMessageUpdate,
        onUserMessageId,
        onAssistantMessageId,
      } = options

      stopStreamingRef.current = false

      try {
        const streamUrl = '/api/queries/stream' // Adjust to your API endpoint

        const response = await fetch(streamUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            query,
            top_k: 5,
            use_streaming: true,
            citation_format: 'inline',
            conversation_id: conversationId || null,
            filters: folderId ? { folder_id: folderId } : undefined,
          }),
        })

        if (!response.ok) {
          if (response.status === 401 && onAuthError) {
            onAuthError()
            return
          }
          const errorText = `HTTP error! status: ${response.status}`
          onError(errorText)
          throw new Error(errorText)
        }

        const reader = response.body?.getReader()
        streamReaderRef.current = reader || null

        if (!reader) {
          const errorMsg = 'No response body received from server'
          onMessageUpdate({ content: errorMsg, streaming: false })
          onError(errorMsg)
          throw new Error(errorMsg)
        }

        const decoder = new TextDecoder()
        let buffer = ''
        let fullResponse = ''
        let citations: Citation[] = []
        let receivedDoneEvent = false
        
        // Streaming blocks state
        const streamingBlocks = new Map<string, StreamingBlockState>()
        const completedBlocks: ContentBlock[] = []
        
        // RAF batching for smooth UI updates
        let pendingUpdate = false
        let rafId: number | null = null
        
        // Batched update function - coalesces multiple deltas into single render
        const scheduleUpdate = () => {
          if (pendingUpdate) return // Already scheduled
          pendingUpdate = true
          
          rafId = requestAnimationFrame(() => {
            pendingUpdate = false
            rafId = null
            
            // Build current state and update UI
            const currentBlocks = buildBlocksFromState(completedBlocks, streamingBlocks)
            fullResponse = blocksToTextFallback(currentBlocks)
            onMessageUpdate({
              content: fullResponse,
              blocks: currentBlocks,
              streaming: true
            })
          })
        }
        
        // Cleanup RAF on stream end
        const cancelScheduledUpdate = () => {
          if (rafId !== null) {
            cancelAnimationFrame(rafId)
            rafId = null
          }
          pendingUpdate = false
        }

        // Single timeout check
        timeoutRef.current = setTimeout(() => {
          if (!stopStreamingRef.current) {
            reader.cancel()
            const timeoutMsg = 'The server did not respond in time. Please try again.'
            onMessageUpdate({ content: timeoutMsg, streaming: false })
            onError(timeoutMsg)
            stopStreamingRef.current = true
          }
        }, STREAM_TIMEOUT)

        while (true) {
          if (stopStreamingRef.current) {
            try {
              await reader.cancel()
            } catch {
              // ignore
            }
            break
          }

          const { done, value } = await reader.read()
          if (done) break

          // Clear timeout on first data received
          if (timeoutRef.current && fullResponse === '' && value) {
            clearTimeout(timeoutRef.current)
            timeoutRef.current = null
          }

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          // Parse SSE events
          for (const line of lines) {
            if (stopStreamingRef.current) break

            if (!line.startsWith('data: ')) continue
            
            try {
              const data = JSON.parse(line.slice(6)) // Remove "data: " prefix
              
              if (data.type === 'conversation_id') {
                if (data.conversation_id && typeof data.conversation_id === 'string') {
                  onConversationIdChange?.(data.conversation_id)
                }
              } else if (data.type === 'user_message_id') {
                if (data.message_id && typeof data.message_id === 'string') {
                  onUserMessageId?.(data.message_id)
                }
              } else if (data.type === 'start') {
                onMessageUpdate({ content: 'Retrieving relevant documents...', streaming: true })
              } else if (data.type === 'progress') {
                const progressMessage = data.message || 'Processing...'
                if (!fullResponse) {
                  onMessageUpdate({ content: progressMessage, streaming: true })
                }
              } else if (data.type === 'block_start') {
                const blockId = data.block_id as string
                const blockType = (data.block_type || 'text') as BlockType
                
                streamingBlocks.set(blockId, {
                  block_id: blockId,
                  block_type: blockType,
                  data: {},
                  streaming: true,
                  partial: false
                })
                
                scheduleUpdate()
                
              } else if (data.type === 'block_delta') {
                const blockId = data.block_id as string
                const path = data.path as string
                const value = data.value as string
                
                // Auto-create block if it doesn't exist
                if (!streamingBlocks.has(blockId)) {
                  streamingBlocks.set(blockId, {
                    block_id: blockId,
                    block_type: 'text',
                    data: {},
                    streaming: true,
                    partial: false
                  })
                }
                
                const blockState = streamingBlocks.get(blockId)
                if (blockState) {
                  applyBlockDelta(blockState, path, value)
                  scheduleUpdate()
                }
                
              } else if (data.type === 'block_end') {
                const blockId = data.block_id as string
                const partial = data.partial as boolean || false
                
                const blockState = streamingBlocks.get(blockId)
                if (blockState) {
                  blockState.streaming = false
                  blockState.partial = partial
                  
                  const completedBlock = stateToContentBlock(blockState)
                  completedBlocks.push(completedBlock)
                  streamingBlocks.delete(blockId)
                  
                  scheduleUpdate()
                }
                
              } else if (data.type === 'response') {
                if (typeof data.data === 'string') {
                  fullResponse = data.data
                  onMessageUpdate({ content: fullResponse, streaming: true })
                }
              } else if (data.type === 'citations') {
                if (data.data && Array.isArray(data.data)) {
                  citations = data.data.map((cit: any, idx: number) => ({
                    citation_number: cit.citation_number ?? idx + 1,
                    content: cit.content || '',
                    score: cit.score,
                    document: cit.document || {},
                    document_id: cit.document_id,
                    chunk_id: cit.chunk_id,
                    metadata: cit.metadata || {},
                  }))
                  onMessageUpdate({ citations, streaming: true })
                }
              } else if (data.type === 'confidence_update') {
                if (typeof data.confidence_score === 'number') {
                  setConfidence(data.confidence_score)
                }
              } else if (data.type === 'done') {
                receivedDoneEvent = true
                
                cancelScheduledUpdate()
                
                if (timeoutRef.current) {
                  clearTimeout(timeoutRef.current)
                  timeoutRef.current = null
                }

                const finalBlocks = buildBlocksFromState(completedBlocks, streamingBlocks)
                const finalContent = blocksToTextFallback(finalBlocks) || fullResponse || 'No response received.'
                
                if (data.metadata?.assistant_message_id) {
                  onAssistantMessageId?.(data.metadata.assistant_message_id)
                }
                
                const finalConfidence = data.confidence_score ?? confidence
                setConfidence(finalConfidence)
                
                onMessageUpdate({
                  content: finalContent,
                  blocks: finalBlocks.length > 0 ? finalBlocks : undefined,
                  citations,
                  streaming: false,
                  confidence: finalConfidence,
                })

                stopStreamingRef.current = true
              } else if (data.type === 'error') {
                cancelScheduledUpdate()
                
                const errorMessage =
                  (typeof data.error === 'string' && data.error) ||
                  (typeof data.data === 'string' && data.data) ||
                  (typeof data.message === 'string' && data.message) ||
                  'Stream error occurred'

                onMessageUpdate({
                  content: fullResponse || errorMessage,
                  streaming: false,
                })

                onError(errorMessage)
                stopStreamingRef.current = true
                break
              }
            } catch (err) {
              // Ignore JSON parse errors for malformed events
              console.warn('Failed to parse SSE event:', err)
            }
          }
        }

        cancelScheduledUpdate()

        // If stream ended without a "done" event
        if (!receivedDoneEvent) {
          const finalBlocks = buildBlocksFromState(completedBlocks, streamingBlocks)
          
          if (fullResponse || citations.length > 0 || finalBlocks.length > 0) {
            const finalContent = blocksToTextFallback(finalBlocks) || fullResponse || 'Response stream ended unexpectedly.'
            onMessageUpdate({
              content: finalContent,
              blocks: finalBlocks.length > 0 ? finalBlocks : undefined,
              citations,
              streaming: false,
            })
          } else if (!stopStreamingRef.current) {
            onMessageUpdate({
              content: 'No response received from the server. The stream ended without data.',
              streaming: false,
            })
            onError('No response received from the server. The stream ended without data.')
          }
        }

        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
          timeoutRef.current = null
        }
      } catch (err: any) {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
          timeoutRef.current = null
        }

        let errorMessage = 'An error occurred while processing your query'

        if (err.name === 'TypeError' && (err.message?.includes('Failed to fetch') || err.message?.includes('ERR_NETWORK'))) {
          errorMessage = 'Cannot connect to API server. Please check your network connection.'
        } else if (err.name === 'AbortError') {
          errorMessage = 'Request was cancelled. Please try again.'
        } else if (err.message) {
          errorMessage = err.message
        }

        onError(errorMessage)
        onMessageUpdate({ content: errorMessage, streaming: false })
      } finally {
        streamReaderRef.current = null
        stopStreamingRef.current = false
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
          timeoutRef.current = null
        }
      }
    },
    [confidence]
  )

  const stopStreaming = useCallback(async () => {
    if (streamReaderRef.current) {
      stopStreamingRef.current = true
      try {
        await streamReaderRef.current.cancel()
      } catch {
        // ignore
      }
      streamReaderRef.current = null
    }

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }, [])

  return { streamQuery, stopStreaming, confidence }
}

// Helper Functions

function applyBlockDelta(state: StreamingBlockState, path: string, value: string): void {
  const data = state.data as Record<string, unknown>
  
  if (path === 'rows' || path === 'items' || path === 'steps') {
    if (!data[path]) {
      data[path] = []
    }
    const arr = data[path] as unknown[]
    
    if (path === 'rows') {
      arr.push(value.split('|').map(s => s.trim()))
    } else {
      arr.push(value)
    }
  } else if (path === 'headers') {
    data[path] = value.split('|').map(s => s.trim())
  } else {
    const existing = data[path]
    if (typeof existing === 'string') {
      data[path] = existing + value
    } else {
      data[path] = value
    }
  }
}

function stateToContentBlock(state: StreamingBlockState): ContentBlock {
  return {
    type: state.block_type,
    data: {
      id: state.block_id,
      ...state.data
    }
  } as ContentBlock
}

function buildBlocksFromState(
  completed: ContentBlock[],
  streaming: Map<string, StreamingBlockState>
): ContentBlock[] {
  const blocks = [...completed]
  
  for (const state of streaming.values()) {
    blocks.push(stateToContentBlock(state))
  }
  
  return blocks
}

function blocksToTextFallback(blocks: ContentBlock[]): string {
  return blocks.map((block: ContentBlock) => {
    const data = block.data as Record<string, unknown>
    
    switch (block.type) {
      case 'text':
      case 'markdown':
        return (data.content as string) || ''
      case 'list':
        return ((data.items as string[]) || []).join('\n')
      case 'steps':
        return ((data.steps as string[]) || []).map((s, i) => `${i + 1}. ${s}`).join('\n')
      case 'table':
        return `[Table: ${((data.headers as string[]) || []).join(', ')}]`
      case 'code':
        return `\`\`\`${(data.language as string) || ''}\n${(data.code as string) || ''}\`\`\``
      default:
        return ''
    }
  }).filter(Boolean).join('\n\n')
}
