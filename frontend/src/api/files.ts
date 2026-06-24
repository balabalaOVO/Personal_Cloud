/**
 * File management API calls
 */
import api from './client'

export interface FileItem {
  name: string
  is_dir: boolean
  size: number
  size_display: string
  mtime: number
  mtime_display: string
}

export interface FileListResponse {
  items: FileItem[]
  total: number
  page: number
  size: number
}

export async function fetchFiles(
  path: string = '/',
  page: number = 1,
  size: number = 50,
  sort: string = 'name',
): Promise<FileListResponse> {
  const { data } = await api.get('/files', { params: { path, page, size, sort } })
  return data
}

export async function uploadFile(
  file: File,
  path: string,
  sha256: string,
  onProgress?: (percent: number, speed: number) => void,
) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('path', path)
  formData.append('sha256', sha256)

  const startTime = Date.now()
  const { data } = await api.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 0, // no timeout for large uploads
    onUploadProgress: (event) => {
      if (event.total && onProgress) {
        const percent = Math.round((event.loaded / event.total) * 100)
        const elapsed = (Date.now() - startTime) / 1000
        const speed = elapsed > 0 ? event.loaded / elapsed : 0
        onProgress(percent, speed)
      }
    },
  })
  return data
}

export async function getDownloadToken(filePath: string): Promise<string> {
  const { data } = await api.post('/files/download-token', { path: filePath })
  return data.token
}

export function downloadFileDirect(filePath: string, filename: string, token: string) {
  // Direct browser download via URL — no fetch, no blob, no memory bloat.
  // The browser's native download manager handles it → immediate start.
  const url = `/api/files/download?path=${encodeURIComponent(filePath)}&token=${encodeURIComponent(token)}`

  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

export async function mkdir(path: string, name: string) {
  const { data } = await api.post('/files/mkdir', { path, name })
  return data
}

export async function renameFile(path: string, new_name: string) {
  const { data } = await api.put('/files/rename', { path, new_name })
  return data
}

export async function deleteFile(path: string) {
  const { data } = await api.delete('/files', { data: { path } })
  return data
}
