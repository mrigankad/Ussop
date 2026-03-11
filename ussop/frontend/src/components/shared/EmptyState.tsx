import { Tray } from '@phosphor-icons/react'

export function EmptyState({ title = 'No data', description = '' }: { title?: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <div className="w-16 h-16 rounded-xl flex items-center justify-center border shadow-inner mb-2"
           style={{ background: 'var(--surface-2)', borderColor: 'var(--border-subtle)' }}>
        <Tray size={32} weight="duotone" style={{ color: 'var(--muted)' }} />
      </div>
      <p className="font-bold tracking-tight" style={{ color: 'var(--text)' }}>{title}</p>
      {description && <p className="text-sm font-medium text-center max-w-sm" style={{ color: 'var(--muted)' }}>{description}</p>}
    </div>
  )
}
