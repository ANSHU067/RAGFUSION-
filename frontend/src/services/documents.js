import api from './api'

const withProgress = (onProgress) => onProgress ? { onUploadProgress: ({ loaded, total }) => onProgress(Math.round((loaded * 100) / (total || 1))) } : {}

export const documentsApi = {
  async upload(file, onProgress, params = {}, config = {}) { const body = new FormData(); body.append('file', file); const { data } = await api.post('/documents/upload', body, { ...config, params, headers: { 'Content-Type': 'multipart/form-data' }, ...withProgress(onProgress) }); return data },
  async list(params = {}, config = {}) { const { data } = await api.get('/documents', { ...config, params }); return data },
  async get(documentId) { const { data } = await api.get(`/documents/${documentId}`); return data },
  async remove(documentId, config = {}) { const { data } = await api.delete(`/documents/${documentId}`, config); return data },
  async process(documentId, params = {}, config = {}) { const { data } = await api.post(`/documents/${documentId}/reprocess`, null, { ...config, params }); return data },
}

export const sourceApi = {
  async list(params = {}, config = {}) { const data = await documentsApi.list(params, config); return { ...data, sources: data.items || [] } },
  async get(sourceId) { return documentsApi.get(sourceId) },
  async delete(sourceId, config = {}) { return documentsApi.remove(sourceId, config) },
  async process(sourceId, params = {}, config = {}) { return documentsApi.process(sourceId, params, config) },
  async getStatus(sourceId) { return documentsApi.get(sourceId) },
}
