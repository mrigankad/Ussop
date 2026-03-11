import { Tray } from '@phosphor-icons/react'
export function EmptyState({ title = 'No data', description = '' }: { title?: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-500">
      <div className="w-16 h-16 rounded-2xl bg-slate-50 flex items-center justify-center border border-slate-100 shadow-inner mb-2">
        <Tray size={32} weight="duotone" className="text-slate-400" />
      </div>
      <p className="font-bold text-slate-800 tracking-tight">{title}</p>
      {description && <p className="text-sm text-slate-500 font-medium">{description}</p>}
    </div>
  )
}

