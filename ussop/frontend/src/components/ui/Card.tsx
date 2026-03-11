import { cn } from '@/lib/cn'
import React from 'react'

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded border transition-all duration-300 relative overflow-hidden group',
        className
      )}
      style={{ background: 'var(--surface)', borderColor: 'var(--border-subtle)' }}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex items-center justify-between px-6 sm:px-8 py-5 sm:py-6 border-b relative z-10', className)}
      style={{ borderColor: 'var(--border-subtle)' }}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-6 sm:p-8 relative z-10', className)} {...props}>{children}</div>
}
