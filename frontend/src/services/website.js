import api from './api'

export const websiteApi = {
  async list(config = {}) { const { data } = await api.get('/website', { ...config, params: { page_size: 100 } }); return data },
  async create(url, config = {}) { const { data } = await api.post('/website/ingest', { url }, config); return data },
  async process(id, config = {}) { const { data } = await api.post(`/website/${id}/process`, null, { timeout: 150000, ...config }); return data },
  async remove(id, config = {}) { await api.delete(`/website/${id}`, config) },
}
