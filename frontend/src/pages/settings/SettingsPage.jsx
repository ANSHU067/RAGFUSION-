import { useEffect, useState } from 'react'
import { settingsApi } from '@/services/settings'
import { getApiError } from '@/services/api'
import { useAsyncScope } from '@/hooks/useAsyncScope'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
const fields = [
  ['provider', 'Provider', 'text'], ['model_name', 'Model', 'text'],
  ['temperature', 'Temperature', 'number', 0, 2, 0.1],
  ['max_tokens', 'Maximum response tokens', 'number', 100, 32000, 1],
  ['top_k', 'Retrieved chunks', 'number', 1, 100, 1],
  ['chunk_size', 'Chunk size', 'number', 128, 4096, 1],
  ['chunk_overlap', 'Chunk overlap', 'number', 0, 1000, 1],
  ['similarity_threshold', 'Similarity threshold', 'number', 0, 1, 0.01],
]
export default function SettingsPage() {
  const [settings, setSettings] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const begin = useAsyncScope()
  useEffect(() => {
    const task = begin('load')
    if (!task) return
    settingsApi.get({ signal: task.signal }).then((data) => { if (task.active()) setSettings(data) })
      .catch((err) => { if (task.active()) setError(getApiError(err, 'Unable to load settings.')) }).finally(task.done)
  }, [begin])
  const save = async (event) => {
    event.preventDefault()
    if (Number(settings.chunk_overlap) >= Number(settings.chunk_size)) { setError('Chunk overlap must be less than chunk size.'); return }
    const task = begin('save')
    if (!task) return
    setSaving(true); setSaved(false); setError('')
    try {
      const payload = Object.fromEntries(fields.map(([key, , type]) => [key, type === 'number' ? Number(settings[key]) : settings[key]]))
      const data = await settingsApi.update(payload, { signal: task.signal })
      if (task.active()) { setSettings(data); setSaved(true) }
    } catch (err) { if (task.active()) setError(getApiError(err, 'Unable to save settings.')) }
    finally { task.done(); if (task.active()) setSaving(false) }
  }
  return <div className="mx-auto max-w-2xl space-y-6"><h1 className="text-2xl font-bold">AI settings</h1>{error && <p role="alert">{error}</p>}{saved && <p role="status">Settings saved.</p>}{!settings ? !error && <p role="status">Loading settings…</p> : <form onSubmit={save} className="space-y-4"><fieldset disabled={saving} className="grid gap-4 sm:grid-cols-2">{fields.map(([key, label, type, min, max, step]) => <div key={key} className="space-y-2"><Label htmlFor={key}>{label}</Label><Input id={key} type={type} required min={min} max={max} step={step} value={settings[key]} onChange={(event) => { setSaved(false); setSettings({ ...settings, [key]: event.target.value }) }} /></div>)}</fieldset><Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save settings'}</Button></form>}</div>
}
