import * as AlertDialogPrimitive from '@radix-ui/react-alert-dialog'
import { cn } from '@/lib/cn'
import React from 'react'

export const AlertDialog = AlertDialogPrimitive.Root
export const AlertDialogTrigger = AlertDialogPrimitive.Trigger

export function AlertDialogContent({
  title, description, confirmLabel = 'Confirm', cancelLabel = 'Cancel',
  onConfirm, variant = 'default', children
}: {
  title: string; description?: string; confirmLabel?: string; cancelLabel?: string;
  onConfirm: () => void; variant?: 'default' | 'danger'; children?: React.ReactNode
}) {
  return (
    <AlertDialogPrimitive.Portal>
      <AlertDialogPrimitive.Overlay className="fixed inset-0 bg-black/50 z-40 animate-in fade-in-0" />
      <AlertDialogPrimitive.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-white rounded-xl shadow-2xl p-6 w-full max-w-md animate-in fade-in-0 zoom-in-95">
        <AlertDialogPrimitive.Title className={cn('text-lg font-semibold mb-2', variant === 'danger' && 'text-red-600')}>
          {title}
        </AlertDialogPrimitive.Title>
        {description && <AlertDialogPrimitive.Description className="text-sm text-zinc-500 mb-4">{description}</AlertDialogPrimitive.Description>}
        {children}
        <div className="flex justify-end gap-3 mt-6">
          <AlertDialogPrimitive.Cancel className="px-4 py-2 text-sm font-medium bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 cursor-pointer">
            {cancelLabel}
          </AlertDialogPrimitive.Cancel>
          <AlertDialogPrimitive.Action
            onClick={onConfirm}
            className={cn('px-4 py-2 text-sm font-medium text-white rounded-lg cursor-pointer', variant === 'danger' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700')}
          >
            {confirmLabel}
          </AlertDialogPrimitive.Action>
        </div>
      </AlertDialogPrimitive.Content>
    </AlertDialogPrimitive.Portal>
  )
}
