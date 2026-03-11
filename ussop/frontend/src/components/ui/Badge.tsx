import { cn } from '@/lib/cn'
import React from 'react'

interface BadgeProps { children: React.ReactNode; variant: 'pass' | 'fail' | 'uncertain' | 'default'; className?: string }

export function Badge({ children, variant, className }: BadgeProps) {
  const dot = {
    pass: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]',
    fail: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]',
    uncertain: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]',
    default: 'bg-slate-500',
  }[variant]

  const style = {
    pass: 'bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-sm',
    fail: 'bg-red-50 text-red-700 border border-red-200 shadow-sm',
    uncertain: 'bg-amber-50 text-amber-700 border border-amber-200 shadow-sm',
    default: 'bg-slate-50 text-slate-700 border border-slate-200 shadow-sm',
  }[variant]

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-bold capitalize',
      style,
      className
    )}>
      <span className={cn('w-1.5 h-1.5 rounded-full', dot)} />
      {children}
    </span>
  )
}
