import api from './api'

export const dashboardApi = {
  async overview(config = {}) { const { data } = await api.get('/dashboard', config); return data },
}
