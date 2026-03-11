import { CircleNotch } from '@phosphor-icons/react'
export function LoadingSpinner({ text = 'Loading...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <CircleNotch size={32} className="animate-spin text-blue-600" />
      <p className="text-sm text-zinc-500">{text}</p>
    </div>
  )
}
