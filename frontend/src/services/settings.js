import api from './api'
export const settingsApi = {
  async get(config = {}) { const { data } = await api.get('/settings', config); return data },
  async update(payload, config = {}) { const { data } = await api.put('/settings', payload, config); return data },
}
