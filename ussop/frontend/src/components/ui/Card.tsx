import { cn } from '@/lib/cn'
import React from 'react'

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn(
      'glass-card rounded-xl text-slate-800 transition-all duration-300 relative overflow-hidden group',
      className
    )} {...props}>
      {/* Subtle top highlight */}
      <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-indigo-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      {children}
    </div>
  )
}

export function CardHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex items-center justify-between px-6 py-4 border-b border-slate-100 relative z-10', className)} {...props}>
      {children}
    </div>
  )
}

export function CardContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-6 relative z-10', className)} {...props}>{children}</div>
}
