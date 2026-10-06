import { createContext, useContext, useState, useCallback } from 'react'
import { documentsApi } from '@/services/documents'
import { useAsyncScope } from '@/hooks/useAsyncScope'
const UploadContext = createContext(null)
export function UploadProvider({ children }) {
  const [uploads, setUploads] = useState([])
  const begin = useAsyncScope()
  const uploadFile = useCallback(async (file, onProgressOrOptions, maybeOptions = {}) => {
    const onProgress = typeof onProgressOrOptions === 'function' ? onProgressOrOptions : null
    const options = typeof onProgressOrOptions === 'function' ? maybeOptions : (onProgressOrOptions || {})
    const task = begin(file)
    if (!task) return null
    try {
      const data = await documentsApi.upload(file, (progress) => { if (task.active()) onProgress?.(progress) }, options, { signal: task.signal })
      if (!task.active()) return null
      setUploads((items) => [...items, data])
      return data
    } finally { task.done() }
  }, [begin])
  const removeUpload = useCallback((uploadId) => setUploads((items) => items.filter((item) => item.id !== uploadId)), [])
  const clearUploads = useCallback(() => setUploads([]), [])
  const getUploadById = useCallback((uploadId) => uploads.find((item) => item.id === uploadId), [uploads])
  const getUploadsByStatus = useCallback((status) => uploads.filter((item) => item.status === status), [uploads])
  return <UploadContext.Provider value={{ uploads, loading: false, error: null, uploadFile, removeUpload, clearUploads, getUploadById, getUploadsByStatus, clearError: () => {} }}>{children}</UploadContext.Provider>
}
export const useUpload = () => useContext(UploadContext)
