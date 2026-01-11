# Frontend Integration

React hooks and components for streaming chat interfaces.

## Overview

This module provides:
- **useStreamingQuery hook** - React hook for streaming queries
- **BlockRenderer component** - Renders content blocks
- **RequestAnimationFrame batching** - Smooth UI updates
- **Confidence tracking** - Real-time confidence scores

## Usage

### Basic Streaming Query

```tsx
import { useStreamingQuery } from './useStreamingQuery'
import { BlockRenderer } from './BlockRenderer'

function ChatComponent() {
  const { streamQuery, stopStreaming, confidence } = useStreamingQuery()
  const [message, setMessage] = useState<Message>({
    content: '',
    blocks: [],
    citations: [],
    streaming: false
  })

  const handleSubmit = async (query: string) => {
    await streamQuery(query, {
      token: 'your-token',
      onMessageUpdate: (updates) => {
        setMessage(prev => ({ ...prev, ...updates }))
      },
      onError: (error) => console.error(error),
    })
  }

  return (
    <div>
      <BlockRenderer 
        blocks={message.blocks || []}
        citations={message.citations || []}
        streaming={message.streaming}
      />
      <ConfidenceIndicator score={confidence} />
    </div>
  )
}
```

### Block Rendering

```tsx
import { BlockRenderer } from './BlockRenderer'

<BlockRenderer
  blocks={blocks}
  citations={citations}
  onCitationClick={(citation) => {
    // Open citation modal
    openCitationModal(citation)
  }}
  streaming={isStreaming}
/>
```

## API Reference

### useStreamingQuery

React hook for streaming chat queries.

**Returns:**
- `streamQuery(query, options)` - Function to start streaming query
- `stopStreaming()` - Function to stop streaming
- `confidence` - Current confidence score (0-1)

**Options:**
- `token: string` - Authentication token
- `conversationId?: string` - Conversation ID
- `folderId?: string` - Folder ID for filtering
- `onError: (error: string) => void` - Error handler
- `onMessageUpdate: (updates: Partial<Message>) => void` - Message update handler
- `onConversationIdChange?: (id: string) => void` - Conversation ID change handler

### BlockRenderer

Renders content blocks with type-specific components.

**Props:**
- `blocks: ContentBlock[]` - Array of content blocks
- `citations?: Citation[]` - Array of citations
- `onCitationClick?: (citation: Citation) => void` - Citation click handler
- `streaming?: boolean` - Whether currently streaming

## Block Types

The BlockRenderer supports all block types:
- `text` - Text with inline citations
- `markdown` - Markdown content
- `code` - Code blocks
- `table` - Tables
- `list` - Lists
- `steps` - Step-by-step instructions
- `callout` - Info/warning/error/success callouts
- `quote` - Blockquotes
- `divider` - Horizontal dividers
- `metric` - Metrics
- `key_value` - Key-value pairs
- `json` - JSON data
- `error` - Error messages
- `unknown` - Unknown block types (fallback)

## Best Practices

1. **Use RAF batching** - Already implemented in useStreamingQuery
2. **Incremental updates** - Update only changed blocks, not entire tree
3. **Error boundaries** - Wrap block renderers in error boundaries
4. **Loading states** - Show loading indicators for streaming blocks
5. **Accessibility** - Ensure block content is accessible (ARIA labels, keyboard navigation)

## Performance

- **RAF batching**: Reduces renders by 10-20x
- **Incremental updates**: Only updates changed blocks
- **Lazy rendering**: Blocks render as they complete
