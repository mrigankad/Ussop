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
      <Button variant="ghost" size="sm" disabled={page === 0} onClick={() => onPageChange(page - 1)}>
        <CaretLeft size={14} />
      </Button>
      {range.map((item, i) =>
        item === '...' ? (
          <span key={`ellipsis-${i}`} className="px-2 text-zinc-400 text-sm">…</span>
        ) : (
          <button
            key={item}
            onClick={() => onPageChange(item)}
            className={cn(
              'w-8 h-8 text-sm rounded-lg font-medium transition-colors',
              item === page ? 'bg-blue-600 text-white' : 'hover:bg-zinc-100 text-zinc-600'
            )}
          >
            {item + 1}
          </button>
        )
      )}
      <Button variant="ghost" size="sm" disabled={page >= totalPages - 1} onClick={() => onPageChange(page + 1)}>
        <CaretRight size={14} />
      </Button>
    </div>
  )
}
