/**
 * BlockRenderer: Renders content blocks with type-specific components.
 * 
 * This component handles progressive rendering of streaming blocks,
 * with support for all block types including text, code, tables, lists, etc.
 * 
 * @example
 * ```tsx
 * <BlockRenderer 
 *   blocks={blocks} 
 *   citations={citations}
 *   onCitationClick={(citation) => openCitation(citation)}
 *   streaming={true}
 * />
 * ```
 */

import React from 'react'
import type { ContentBlock, Citation } from './useStreamingQuery'

export interface BlockRendererProps {
  blocks: ContentBlock[]
  citations?: Citation[]
  onCitationClick?: (citation: Citation) => void
  streaming?: boolean
}

export function BlockRenderer({ 
  blocks, 
  citations = [], 
  onCitationClick,
  streaming = false 
}: BlockRendererProps) {
  return (
    <div className="blocks-container">
      {blocks.map((block, index) => {
        const key = block.data.id || `block-${index}`
        
        switch (block.type) {
          case 'text':
            return <TextBlock key={key} block={block} citations={citations} onCitationClick={onCitationClick} />
          case 'markdown':
            return <MarkdownBlock key={key} block={block} citations={citations} onCitationClick={onCitationClick} />
          case 'code':
            return <CodeBlock key={key} block={block} />
          case 'table':
            return <TableBlock key={key} block={block} />
          case 'list':
            return <ListBlock key={key} block={block} />
          case 'steps':
            return <StepsBlock key={key} block={block} />
          case 'callout':
            return <CalloutBlock key={key} block={block} />
          case 'quote':
            return <QuoteBlock key={key} block={block} />
          case 'divider':
            return <DividerBlock key={key} />
          case 'metric':
            return <MetricBlock key={key} block={block} />
          case 'key_value':
            return <KeyValueBlock key={key} block={block} />
          case 'json':
            return <JSONBlock key={key} block={block} />
          case 'error':
            return <ErrorBlock key={key} block={block} />
          default:
            return <UnknownBlock key={key} block={block} />
        }
      })}
      {streaming && (
        <span className="inline-block w-2 h-4 ml-1 bg-blue-400 animate-pulse" />
      )}
    </div>
  )
}

// Block Components

function TextBlock({ 
  block, 
  citations, 
  onCitationClick 
}: { 
  block: ContentBlock
  citations: Citation[]
  onCitationClick?: (citation: Citation) => void
}) {
  const content = block.data.content as string || ''
  const citationMap = new Map(citations.map(c => [c.citation_number, c]))
  
  // Parse inline citations [1], [2]
  const parts = content.split(/(\[\d+\])/g)
  
  return (
    <div className="text-block">
      {parts.map((part, i) => {
        const citationMatch = part.match(/\[(\d+)\]/)
        if (citationMatch) {
          const citeNum = parseInt(citationMatch[1])
          const citation = citationMap.get(citeNum)
          return (
            <button
              key={i}
              onClick={() => citation && onCitationClick?.(citation)}
              className="inline-flex items-center justify-center min-w-[1.5rem] h-5 px-1 text-xs font-semibold border rounded text-blue-600 bg-blue-50 border-blue-200 hover:bg-blue-100 cursor-pointer"
            >
              {citeNum}
            </button>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </div>
  )
}

function MarkdownBlock({ 
  block, 
  citations, 
  onCitationClick 
}: { 
  block: ContentBlock
  citations: Citation[]
  onCitationClick?: (citation: Citation) => void
}) {
  // In a real implementation, use a markdown renderer like react-markdown
  return <div className="markdown-block">{block.data.content as string}</div>
}

function CodeBlock({ block }: { block: ContentBlock }) {
  const code = block.data.code as string || ''
  const language = block.data.language as string || ''
  
  return (
    <pre className="bg-gray-900 text-white p-4 rounded-lg overflow-x-auto">
      <code className={`language-${language}`}>{code}</code>
    </pre>
  )
}

function TableBlock({ block }: { block: ContentBlock }) {
  const headers = block.data.headers as string[] || []
  const rows = block.data.rows as string[][] || []
  
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse">
        <thead>
          <tr>
            {headers.map((header, i) => (
              <th key={i} className="px-4 py-2 border border-gray-300">{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2 border border-gray-300">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ListBlock({ block }: { block: ContentBlock }) {
  const items = block.data.items as string[] || []
  const ordered = block.data.ordered as boolean || false
  
  const ListTag = ordered ? 'ol' : 'ul'
  
  return (
    <ListTag className={ordered ? 'list-decimal' : 'list-disc'}>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ListTag>
  )
}

function StepsBlock({ block }: { block: ContentBlock }) {
  const steps = block.data.steps as string[] || []
  
  return (
    <ol className="list-decimal">
      {steps.map((step, i) => (
        <li key={i}>{step}</li>
      ))}
    </ol>
  )
}

function CalloutBlock({ block }: { block: ContentBlock }) {
  const variant = block.data.variant as string || 'info'
  const content = block.data.content as string || ''
  const title = block.data.title as string
  
  const variants = {
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    success: 'bg-green-50 border-green-200 text-green-800',
  }
  
  return (
    <div className={`border-l-4 p-4 rounded ${variants[variant as keyof typeof variants] || variants.info}`}>
      {title && <div className="font-semibold mb-2">{title}</div>}
      <div>{content}</div>
    </div>
  )
}

function QuoteBlock({ block }: { block: ContentBlock }) {
  const content = block.data.content as string || ''
  const source = block.data.source as string
  
  return (
    <blockquote className="border-l-4 border-gray-300 pl-4 italic">
      <div>{content}</div>
      {source && <div className="mt-2 text-sm">— {source}</div>}
    </blockquote>
  )
}

function DividerBlock() {
  return <hr className="my-4 border-gray-300" />
}

function MetricBlock({ block }: { block: ContentBlock }) {
  const label = block.data.label as string || ''
  const value = block.data.value as string | number
  const delta = block.data.delta as number
  
  return (
    <div className="metric-block">
      <div className="text-sm text-gray-600">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      {delta !== undefined && (
        <div className={`text-sm ${delta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {delta >= 0 ? '+' : ''}{delta}%
        </div>
      )}
    </div>
  )
}

function KeyValueBlock({ block }: { block: ContentBlock }) {
  const items = block.data.items as Record<string, any> || {}
  
  return (
    <dl className="key-value-block">
      {Object.entries(items).map(([key, value]) => (
        <div key={key} className="flex">
          <dt className="font-semibold mr-2">{key}:</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

function JSONBlock({ block }: { block: ContentBlock }) {
  const data = block.data.data as object || {}
  
  return (
    <pre className="bg-gray-100 p-4 rounded overflow-x-auto">
      <code>{JSON.stringify(data, null, 2)}</code>
    </pre>
  )
}

function ErrorBlock({ block }: { block: ContentBlock }) {
  const message = block.data.message as string || ''
  const details = block.data.details as string
  
  return (
    <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded">
      <div className="font-semibold">Error: {message}</div>
      {details && <div className="mt-2 text-sm">{details}</div>}
    </div>
  )
}

function UnknownBlock({ block }: { block: ContentBlock }) {
  const raw = block.data.raw as Record<string, any> || {}
  const originalType = raw.original_type as string || 'unknown'
  
  return (
    <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 p-4 rounded">
      <div className="font-semibold">Unknown block type: {originalType}</div>
      <pre className="mt-2 text-xs overflow-auto">
        {JSON.stringify(raw, null, 2)}
      </pre>
    </div>
  )
}
