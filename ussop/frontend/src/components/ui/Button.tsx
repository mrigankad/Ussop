import { cn } from '@/lib/cn'
import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

export function Button({ variant = 'secondary', size = 'md', className, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 font-bold rounded-xl transition-all duration-300 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed outline-none select-none group focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2',
        {
          'bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800 shadow-[0_2px_10px_rgba(79,70,229,0.3)] hover:shadow-[0_4px_15px_rgba(79,70,229,0.4)] border border-transparent': variant === 'primary',
          'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 hover:border-slate-300 hover:text-slate-900 active:bg-slate-100 shadow-[0_1px_3px_rgba(0,0,0,0.05)] hover:shadow-[0_2px_5px_rgba(0,0,0,0.08)]': variant === 'secondary',
          'bg-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-800 active:bg-slate-100': variant === 'ghost',
          'bg-red-500 text-white hover:bg-red-600 active:bg-red-700 shadow-[0_2px_10px_rgba(239,68,68,0.3)] hover:shadow-[0_4px_15px_rgba(239,68,68,0.4)] border border-transparent': variant === 'danger',
        },
        {
          'px-3.5 py-1.5 text-xs tracking-wide': size === 'sm',
          'px-4 py-2 text-sm tracking-wide': size === 'md',
          'px-5 py-2.5 text-[15px] tracking-wide': size === 'lg',
        },
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}
