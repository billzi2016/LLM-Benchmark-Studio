import { getJson, postJson } from './client'
import type { BenchmarkRun, DatasetSummary, Language, LlmModel, ProviderInfo, SystemStatus } from '../types/studio'

export function fetchSystemStatus() {
  return getJson<SystemStatus>('/api/system/status')
}

export function openSystemStream(intervalSeconds = 2) {
  return new EventSource(`/api/system/stream?interval=${intervalSeconds}`)
}

export function fetchModels() {
  return getJson<LlmModel[]>('/api/models')
}

export function fetchLanguages() {
  return getJson<Language[]>('/api/languages')
}

export function fetchDatasets() {
  return getJson<DatasetSummary[]>('/api/datasets')
}

export function fetchProviders() {
  return getJson<ProviderInfo[]>('/api/llms/providers')
}

export function fetchRuns() {
  return getJson<BenchmarkRun[]>('/api/tasks/runs')
}

export function fetchRun(runId: string) {
  return getJson<BenchmarkRun>(`/api/tasks/runs/${runId}`)
}

export function createRun(payload: { model_names: string[]; dataset_names: string[]; language_code: string }) {
  return postJson<BenchmarkRun>('/api/tasks/runs', payload)
}

export function playRun(runId: string) {
  return postJson<BenchmarkRun>(`/api/tasks/runs/${runId}/play`)
}

export function pauseRun(runId: string) {
  return postJson<BenchmarkRun>(`/api/tasks/runs/${runId}/pause`)
}

export function stopRun(runId: string) {
  return postJson<BenchmarkRun>(`/api/tasks/runs/${runId}/stop`)
}
