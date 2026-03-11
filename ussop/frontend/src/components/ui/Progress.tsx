import * as ProgressPrimitive from '@radix-ui/react-progress'
import { cn } from '@/lib/cn'

export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <ProgressPrimitive.Root className={cn('relative h-2 w-full overflow-hidden rounded-full bg-zinc-200', className)}>
      <ProgressPrimitive.Indicator
        className="h-full bg-blue-600 transition-all duration-500 ease-out"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </ProgressPrimitive.Root>
  )
}
