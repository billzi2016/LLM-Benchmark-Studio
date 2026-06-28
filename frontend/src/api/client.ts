export interface ApiResponse<T> {
  ok: boolean
  data: T
  meta: Record<string, unknown>
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const SYSTEM_PROFILER_BASE_URL = import.meta.env.VITE_SYSTEM_PROFILER_BASE_URL ?? 'http://127.0.0.1:6346'

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    headers: { Accept: 'application/json' }
  })
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`)
  }
  const payload = (await response.json()) as ApiResponse<T>
  return payload.data
}

export async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  })
  if (!response.ok) {
    throw new Error(`POST ${path} failed: ${response.status}`)
  }
  const payload = (await response.json()) as ApiResponse<T>
  return payload.data
}

export async function getProfilerJson<T>(path: string): Promise<T> {
  const response = await fetch(`${SYSTEM_PROFILER_BASE_URL}${path}`, {
    headers: { Accept: 'application/json' }
  })
  if (!response.ok) {
    throw new Error(`GET profiler ${path} failed: ${response.status}`)
  }
  const payload = (await response.json()) as ApiResponse<T>
  return payload.data
}

export function openProfilerStream(path: string): EventSource {
  return new EventSource(`${SYSTEM_PROFILER_BASE_URL}${path}`)
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
