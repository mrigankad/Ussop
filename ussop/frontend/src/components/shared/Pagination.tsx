import { Button } from '@/components/ui/Button'
import { CaretLeft, CaretRight } from '@phosphor-icons/react'
import { cn } from '@/lib/cn'

interface PaginationProps { page: number; totalPages: number; onPageChange: (p: number) => void }

export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null

  const range: (number | '...')[] = []
  const delta = 2
  for (let i = 0; i < totalPages; i++) {
    if (i === 0 || i === totalPages - 1 || (i >= page - delta && i <= page + delta)) {
      range.push(i)
    } else if (range[range.length - 1] !== '...') {
      range.push('...')
    }
  }

  return (
    <div className="flex items-center justify-center gap-1 py-4">
      <Button variant="ghost" size="sm" disabled={page === 0} onClick={() => onPageChange(page - 1)}
              aria-label="Previous page">
        <CaretLeft size={14} />
      </Button>
      {range.map((item, i) =>
        item === '...' ? (
          <span key={`ellipsis-${i}`} className="px-2 text-sm" style={{ color: 'var(--muted)' }}>…</span>
        ) : (
          <button
            key={item}
            onClick={() => onPageChange(item)}
            aria-label={`Page ${item + 1}`}
            aria-current={item === page ? 'page' : undefined}
            className={cn(
              'w-8 h-8 text-sm rounded-lg font-medium transition-colors',
              item === page ? 'bg-olive-600 text-white' : 'hover:bg-slate-100'
            )}
            style={item !== page ? { color: 'var(--text-2)' } : undefined}
          >
            {item + 1}
          </button>
        )
      )}
      <Button variant="ghost" size="sm" disabled={page >= totalPages - 1} onClick={() => onPageChange(page + 1)}
              aria-label="Next page">
        <CaretRight size={14} />
      </Button>
    </div>
  )
}
