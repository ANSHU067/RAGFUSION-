import api from './api'
import { parseTimestamp } from '@/lib/dates'

export const historyApi = {
  async list(params = {}, config = {}) {
    const sessions = []
    let page = 1
    let pages
    do {
      const { data } = await api.get('/history', { ...config, params: { ...params, page, page_size: 100 } })
      pages ??= data.total_pages || 1
      sessions.push(...(data.sessions || []))
      if (!data.sessions?.length) break
    } while (++page <= pages)
    return sessions.map((session) => ({
      ...session,
      createdAt: parseTimestamp(session.created_at)?.getTime() ?? null,
      updatedAt: parseTimestamp(session.updated_at)?.getTime() ?? null,
      session: session.session_metadata?.source_type || 'Chat session',
      type: session.session_metadata?.source_type || 'chat',
      status: session.is_deleted ? 'deleted' : 'completed',
    }))
  },
  async search(query, params = {}) { const { data } = await api.get('/history/search', { params: { q: query, ...params } }); return data },
  async get(id) { const { data } = await api.get(`/history/${id}`); return data },
  async rename(id, title, config = {}) { const { data } = await api.patch(`/history/${id}`, { title }, config); return data },
  async remove(id, config = {}) { const { data } = await api.delete(`/history/${id}`, config); return data },
  async restore(id) { const { data } = await api.post(`/history/${id}/restore`); return data },
}
