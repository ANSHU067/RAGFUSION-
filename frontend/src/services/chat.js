import api from './api'
export const chatApi = {
  async listSources(config = {}) { const { data } = await api.get('/chat/sources', config); return data },
  async sendMessage(payload, config = {}) { const { data } = await api.post('/chat', payload, config); return data },
  async listSessions(params = {}, config = {}) { const { data } = await api.get('/chat/sessions', { ...config, params }); return data },
  async createSession(payload = {}, config = {}) { const { data } = await api.post('/chat/sessions', payload, config); return data },
  async getSession(id, config = {}) {
    const messages = []
    let session
    let total
    do {
      const { data } = await api.get(`/chat/sessions/${id}`, { ...config, params: { limit: 100, offset: messages.length } })
      session = data.session
      total ??= session.message_count ?? data.messages.length
      if (!data.messages.length) break
      messages.push(...data.messages)
    } while (messages.length < total)
    return { session, messages: messages.slice(0, total) }
  },
  async removeSession(id, config = {}) { await api.delete(`/chat/sessions/${id}`, config) },
}
