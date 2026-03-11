import { cn } from '@/lib/cn'
import React from 'react'
import { CircleNotch } from '@phosphor-icons/react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

const variantClasses: Record<string, string> = {
  primary: 'bg-olive-600 text-white hover:bg-olive-700 active:bg-olive-800 border border-transparent shadow-sm',
  secondary: 'border hover:bg-slate-50 active:bg-slate-100',
  ghost: 'bg-transparent hover:bg-slate-50 active:bg-slate-100 border border-transparent',
  danger: 'bg-red-500 text-white hover:bg-red-600 active:bg-red-700 border border-transparent',
}

const sizeClasses: Record<string, string> = {
  sm: 'px-3.5 py-1.5 text-xs tracking-wide',
  md: 'px-4 py-2 text-sm tracking-wide',
  lg: 'px-5 py-2.5 text-[15px] tracking-wide',
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'secondary', size = 'md', loading, className, disabled, children, ...props }, ref) => {
    const isDisabled = disabled || loading
    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          'inline-flex items-center justify-center gap-2 font-bold rounded transition-all duration-200 cursor-pointer',
          'disabled:opacity-50 disabled:cursor-not-allowed outline-none select-none group',
          'focus-visible:ring-2 focus-visible:ring-olive-500/40 focus-visible:ring-offset-2',
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        style={
          variant === 'secondary'
            ? { background: 'var(--surface)', color: 'var(--text-2)', borderColor: 'var(--border)' }
            : variant === 'ghost'
            ? { color: 'var(--text-2)' }
            : undefined
        }
        {...props}
      >
        {loading && <CircleNotch size={16} weight="bold" className="animate-spin" aria-hidden="true" />}
        {children}
      </button>
    )
  }
)
Button.displayName = 'Button'
