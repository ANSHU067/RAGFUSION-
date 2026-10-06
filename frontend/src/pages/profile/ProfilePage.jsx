import { useRef, useState } from 'react'
import { toast } from 'sonner'
import { useAuth } from '@/context/AuthContext'
import { useAsyncScope } from '@/hooks/useAsyncScope'
import { getApiError, isCanceled } from '@/services/api'
import { avatarColorClass, initials } from '@/lib/profile'
import { Button } from '@/components/ui/button'

export default function ProfilePage() {
  const { user, updateProfile } = useAuth()
  if (!user) return null
  return <ProfileForm key={user.id} user={user} updateProfile={updateProfile} />
}

function ProfileForm({ user, updateProfile }) {
  const [form, setForm] = useState(() => ({ display_name: user.display_name || '', bio: user.bio || '', workspace: user.workspace || '', avatar_color: user.avatar_color || 'slate' }))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const busy = useRef(false)
  const begin = useAsyncScope()
  const change = (event) => setForm((previous) => ({ ...previous, [event.target.name]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    if (busy.current) return
    const task = begin('profile')
    if (!task) return
    busy.current = true; setSaving(true); setError('')
    try {
      const updated = await updateProfile({ ...form, display_name: form.display_name.trim() }, { signal: task.signal })
      if (task.active()) {
        setForm({ display_name: updated.display_name, bio: updated.bio || '', workspace: updated.workspace || '', avatar_color: updated.avatar_color })
        toast.success('Profile updated')
      }
    } catch (err) {
      if (task.active() && !isCanceled(err)) {
        const message = getApiError(err, 'Unable to update your profile.')
        setError(message); toast.error(message)
      }
    } finally { task.done(); if (task.active()) { busy.current = false; setSaving(false) } }
  }
  const inputClass = 'mt-2 w-full rounded-lg border bg-background px-3 py-2'
  return <div className="mx-auto max-w-3xl space-y-6">
    <header><p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Your account</p><h1 className="mt-2 text-3xl font-bold">Profile</h1><p className="mt-2 text-sm text-muted-foreground">Manage how you appear in your RAGFUSION workspace.</p></header>
    <form onSubmit={submit} className="rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
      <div className="mb-7 flex items-center gap-4"><span aria-label="Avatar preview" className={'flex h-16 w-16 items-center justify-center rounded-full text-xl font-semibold ' + avatarColorClass(form.avatar_color)}>{initials(form.display_name)}</span><div><p className="font-medium">{user.email}</p><p className="mt-1 text-sm text-muted-foreground">Email is linked to your sign-in identity.</p></div></div>
      <fieldset disabled={saving} className="space-y-5">
        <div><label htmlFor="display-name" className="text-sm font-medium">Display name</label><input id="display-name" name="display_name" required maxLength={120} autoComplete="name" value={form.display_name} onChange={change} className={inputClass} /></div>
        <div><label htmlFor="profile-workspace" className="text-sm font-medium">Workspace label</label><input id="profile-workspace" name="workspace" maxLength={120} value={form.workspace} onChange={change} className={inputClass} /><p className="mt-1 text-xs text-muted-foreground">A personal label; this does not change workspace membership or access.</p></div>
        <div><label htmlFor="profile-bio" className="text-sm font-medium">Bio</label><textarea id="profile-bio" name="bio" rows={4} maxLength={1000} value={form.bio} onChange={change} className={inputClass} /></div>
        <div><label htmlFor="avatar-color" className="text-sm font-medium">Avatar color</label><select id="avatar-color" name="avatar_color" value={form.avatar_color} onChange={change} className={inputClass}>{['slate', 'indigo', 'emerald', 'rose', 'amber'].map((color) => <option key={color} value={color}>{color[0].toUpperCase() + color.slice(1)}</option>)}</select></div>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <Button type="submit" disabled={saving || !form.display_name.trim()}>{saving ? 'Saving…' : 'Save profile'}</Button>
      </fieldset>
    </form>
  </div>
}
