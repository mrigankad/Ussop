import * as SwitchPrimitive from '@radix-ui/react-switch'
import { cn } from '@/lib/cn'

interface SwitchProps { checked: boolean; onCheckedChange: (v: boolean) => void; id?: string }

export function Switch({ checked, onCheckedChange, id }: SwitchProps) {
  return (
    <SwitchPrimitive.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      className={cn(
        'w-11 h-6 rounded-full transition-colors cursor-pointer',
        'data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-zinc-300',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2'
      )}
    >
      <SwitchPrimitive.Thumb className="block w-5 h-5 bg-white rounded-full shadow-sm transition-transform translate-x-0.5 data-[state=checked]:translate-x-[22px]" />
    </SwitchPrimitive.Root>
  )
}
