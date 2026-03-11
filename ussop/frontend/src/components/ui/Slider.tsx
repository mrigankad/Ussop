import * as SliderPrimitive from '@radix-ui/react-slider'
import { cn } from '@/lib/cn'

interface SliderProps { value: number; onValueChange: (v: number) => void; min?: number; max?: number; step?: number; className?: string }

export function Slider({ value, onValueChange, min = 0, max = 1, step = 0.05, className }: SliderProps) {
  return (
    <SliderPrimitive.Root
      value={[value]}
      onValueChange={([v]) => onValueChange(v)}
      min={min} max={max} step={step}
      className={cn('relative flex items-center select-none touch-none w-full h-5', className)}
    >
      <SliderPrimitive.Track className="relative grow rounded-full h-2 bg-zinc-200">
        <SliderPrimitive.Range className="absolute rounded-full h-full bg-blue-600" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb className="block w-5 h-5 bg-white border-2 border-blue-600 rounded-full shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 cursor-grab active:cursor-grabbing" />
    </SliderPrimitive.Root>
  )
}
