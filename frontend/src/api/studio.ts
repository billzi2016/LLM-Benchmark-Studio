import { getJson } from './client'
import type { DatasetSummary, Language, LlmModel, ProviderInfo, SystemStatus } from '../types/studio'

export function fetchSystemStatus() {
  return getJson<SystemStatus>('/api/system/status')
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
