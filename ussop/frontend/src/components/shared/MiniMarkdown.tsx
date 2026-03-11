import React from 'react'

/**
 * Renders a small subset of markdown commonly returned by VLMs:
 *   **bold**, *italic*, # headings, * / - bullet lists, blank-line paragraphs.
 */
export function MiniMarkdown({ text }: { text: string }) {
  const lines = text.split('\n')
  const nodes: React.ReactNode[] = []
  let listItems: React.ReactNode[] = []
  let key = 0

  function flushList() {
    if (listItems.length) {
      nodes.push(
        <ul key={key++} className="list-none space-y-1.5 my-2">
          {listItems}
        </ul>
      )
      listItems = []
    }
  }

  function renderInline(raw: string): React.ReactNode {
    // **bold** and *italic*
    const parts = raw.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
    return parts.map((p, i) => {
      if (p.startsWith('**') && p.endsWith('**'))
        return <strong key={i} className="font-semibold text-slate-800">{p.slice(2, -2)}</strong>
      if (p.startsWith('*') && p.endsWith('*'))
        return <em key={i} className="italic">{p.slice(1, -1)}</em>
      return p
    })
  }

  for (const raw of lines) {
    const line = raw.trim()

    // blank line
    if (!line) { flushList(); continue }

    // heading: ## or ###
    const hMatch = line.match(/^#{1,3}\s+(.+)/)
    if (hMatch) {
      flushList()
      nodes.push(
        <p key={key++} className="font-bold text-slate-800 text-sm mt-3 mb-1">
          {renderInline(hMatch[1])}
        </p>
      )
      continue
    }

    // bullet: * item or - item
    const bulletMatch = line.match(/^[*\-]\s+(.+)/)
    if (bulletMatch) {
      listItems.push(
        <li key={key++} className="flex items-start gap-2 text-sm text-slate-700">
          <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
          <span>{renderInline(bulletMatch[1])}</span>
        </li>
      )
      continue
    }

    // plain paragraph
    flushList()
    nodes.push(
      <p key={key++} className="text-sm text-slate-700 leading-relaxed">
        {renderInline(line)}
      </p>
    )
  }

  flushList()
  return <div className="space-y-1">{nodes}</div>
}
