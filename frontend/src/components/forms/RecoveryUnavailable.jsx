import * as Dialog from '@radix-ui/react-dialog'
import { Button } from '@/components/ui/button'
export function RecoveryUnavailable() {
  return <Dialog.Root><Dialog.Trigger asChild><button type="button" className="link">Forgot password?</button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" /><Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[90vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-background p-6 shadow-xl"><Dialog.Title className="text-xl font-semibold">Password recovery unavailable</Dialog.Title><Dialog.Description className="my-4">Self-service password recovery is not available. Contact your deployment administrator for account access assistance.</Dialog.Description><Dialog.Close asChild><Button>Close</Button></Dialog.Close></Dialog.Content></Dialog.Portal></Dialog.Root>
}
