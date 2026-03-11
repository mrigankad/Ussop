import { CircleNotch } from '@phosphor-icons/react'

export function LoadingSpinner({ text = 'Loading...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <CircleNotch size={32} className="animate-spin text-olive-600" />
      <p className="text-sm font-medium" style={{ color: 'var(--muted)' }}>{text}</p>
    </div>
  )
}
