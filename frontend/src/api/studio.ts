import { getJson, getProfilerJson, openProfilerStream, postJson } from './client'
import type {
  BenchmarkRun,
  DatasetSummary,
  Language,
  LlmModel,
  SystemProfilerHistory,
  SystemStatus
} from '../types/studio'

export function fetchSystemStatus() {
  return getJson<SystemStatus>('/api/system/status')
}

export function openSystemStream(intervalSeconds = 2) {
  return new EventSource(`/api/system/stream?interval=${intervalSeconds}`)
}

export function fetchProfilerSnapshot() {
  return getProfilerJson<SystemStatus['metrics']>('/snapshot')
}

export function fetchProfilerHistory() {
  return getProfilerJson<SystemProfilerHistory>('/history')
}

export function openProfilerSystemStream() {
  return openProfilerStream('/stream')
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

export function fetchRuns() {
  return getJson<BenchmarkRun[]>('/api/tasks/runs')
}

export function fetchRun(runId: string) {
  return getJson<BenchmarkRun>(`/api/tasks/runs/${runId}`)
}

export function createRun(payload: { model_names: string[]; dataset_names: string[]; language_codes: string[] }) {
  return postJson<BenchmarkRun>('/api/tasks/runs', payload)
}

export function playRun(runId: string, payload: { task_ids: string[] }) {
  return postJson<BenchmarkRun>(`/api/tasks/runs/${runId}/play`, payload)
}

export function pauseRun(runId: string) {
  return postJson<BenchmarkRun>(`/api/tasks/runs/${runId}/pause`)
}

export function stopRun(runId: string) {
  return postJson<BenchmarkRun>(`/api/tasks/runs/${runId}/stop`)
}

export function deleteRunTasks(runId: string, payload: { task_ids: string[] }) {
  return postJson<BenchmarkRun | null>(`/api/tasks/runs/${runId}/delete`, payload)
}
