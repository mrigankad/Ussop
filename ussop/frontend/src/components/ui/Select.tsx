import * as SelectPrimitive from '@radix-ui/react-select'
import { CaretDown, Check } from '@phosphor-icons/react'
import { cn } from '@/lib/cn'

interface SelectProps {
  value: string
  onValueChange: (v: string) => void
  options: { value: string; label: string }[]
  placeholder?: string
  className?: string
}

export function Select({ value, onValueChange, options, placeholder, className }: SelectProps) {
  return (
    <SelectPrimitive.Root value={value} onValueChange={onValueChange}>
      <SelectPrimitive.Trigger className={cn(
        'flex items-center justify-between w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg bg-white',
        'hover:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 data-[placeholder]:text-zinc-400',
        className
      )}>
        <SelectPrimitive.Value placeholder={placeholder} />
        <SelectPrimitive.Icon><CaretDown size={14} className="text-zinc-400" /></SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content className="overflow-hidden bg-white rounded-lg shadow-lg border border-zinc-200 z-50">
          <SelectPrimitive.Viewport className="p-1">
            {options.map(opt => (
              <SelectPrimitive.Item key={opt.value} value={opt.value} className="flex items-center gap-2 px-3 py-2 text-sm rounded cursor-pointer outline-none hover:bg-zinc-100 data-[highlighted]:bg-blue-50 data-[highlighted]:text-blue-700">
                <SelectPrimitive.ItemIndicator><Check size={14} /></SelectPrimitive.ItemIndicator>
                <SelectPrimitive.ItemText>{opt.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  )
}
