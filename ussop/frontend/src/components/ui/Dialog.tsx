import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from '@phosphor-icons/react'
import { cn } from '@/lib/cn'
import React from 'react'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger

export function DialogContent({ children, className, title }: { children: React.ReactNode; className?: string; title?: string }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 bg-black/50 z-40 animate-in fade-in-0" />
      <DialogPrimitive.Content className={cn(
        'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50',
        'bg-white rounded-xl shadow-2xl p-6 w-full max-w-md',
        'animate-in fade-in-0 zoom-in-95 slide-in-from-top-4',
        className
      )}>
        {title && <DialogPrimitive.Title className="text-lg font-semibold mb-4">{title}</DialogPrimitive.Title>}
        {children}
        <DialogPrimitive.Close className="absolute top-4 right-4 p-1 rounded text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100">
          <X size={16} />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}
