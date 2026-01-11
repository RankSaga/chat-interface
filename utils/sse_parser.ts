/**
 * SSE Parser: Parses Server-Sent Events (SSE) format.
 * 
 * Handles both standard data-only events and named events:
 * - "data: {...}" - standard event
 * - "event: block\ndata: {...}" - named event
 */

const DATA_PREFIX_REGEX = /^data:\s*/g
const EVENT_PREFIX_REGEX = /^event:\s*/g

export type SSEParseResult = {
  eventName?: string  // Named event type (e.g., "block")
  data: any           // Parsed JSON data
} | null

export class SSEParser {
  private currentEventName: string | null = null
  
  /**
   * Parse an SSE line.
   * 
   * @param line Single line from SSE stream
   * @returns Parsed result or null if line doesn't complete an event
   */
  parseLine(line: string): SSEParseResult {
    // Handle event name line
    if (line.startsWith('event:')) {
      this.currentEventName = line.replace(EVENT_PREFIX_REGEX, '').trim()
      return null  // Wait for data line
    }
    
    // Handle data line
    if (line.startsWith('data:')) {
      const payload = line.replace(DATA_PREFIX_REGEX, '').trim()
      if (!payload) {
        this.currentEventName = null
        return null
      }
      
      try {
        const data = JSON.parse(payload)
        const result: SSEParseResult = {
          eventName: this.currentEventName || undefined,
          data
        }
        this.currentEventName = null  // Reset for next event
        return result
      } catch {
        this.currentEventName = null
        return null
      }
    }
    
    // Empty line resets state
    if (!line.trim()) {
      this.currentEventName = null
    }
    
    return null
  }
}

/**
 * Legacy function for backward compatibility.
 * Parses a single SSE data line (ignores event names).
 */
export function parseSSELine(line: string): any | null {
  if (!line.startsWith('data:')) return null
  const payload = line.replace(DATA_PREFIX_REGEX, '').trim()
  if (!payload) return null
  try {
    return JSON.parse(payload)
  } catch {
    return null
  }
}
