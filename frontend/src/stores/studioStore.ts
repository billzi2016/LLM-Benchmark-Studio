import { defineStore } from 'pinia'

import {
  createRun,
  fetchDatasets,
  fetchLanguages,
  fetchModels,
  fetchProfilerHistory,
  fetchProfilerSnapshot,
  fetchRun,
  fetchRuns,
  fetchSystemStatus,
  openProfilerSystemStream,
  deleteRunTasks,
  pauseRun,
  playRun,
  stopRun
} from '../api/studio'
import type {
  BenchmarkRun,
  DatasetSummary,
  Language,
  LlmModel,
  ProviderInfo,
  SystemMetrics,
  SystemProfilerHistory,
  StudioTask,
  SystemStatus
} from '../types/studio'

function makeProfilerService(status: 'error' | 'loading' | 'ok', detail: string) {
  return {
    name: 'system_profiler',
    label: 'System Profiler',
    status,
    detail
  }
}

function isGenerationModel(model: LlmModel): boolean {
  const modelType = String(model.metadata.type ?? 'generation').toLowerCase()
  const modelRole = String(model.metadata.role ?? '').toLowerCase()
  const modality = String(model.metadata.modality ?? 'text').toLowerCase()
  const name = model.name.toLowerCase()
  const family = model.family.toLowerCase()
  const blockedTypes = new Set(['embedding', 'translation', 'rerank', 'reranker', 'classifier'])
  const blockedRoles = new Set(['translation'])
  const blockedModalities = new Set(['vision', 'ocr', 'audio', 'image'])
  const blockedTerms = ['embed', 'translate', 'coder', 'vision', 'ocr', 'rerank']
  return (
    !blockedTypes.has(modelType) &&
    !blockedRoles.has(modelRole) &&
    !blockedModalities.has(modality) &&
    !blockedTerms.some((term) => name.includes(term) || family.includes(term))
  )
}

let pollTimer: ReturnType<typeof setInterval> | null = null
let systemStream: EventSource | null = null
let profilerHistoryTimer: ReturnType<typeof setInterval> | null = null

export const useStudioStore = defineStore('studio', {
  getters: {
    visibleProviders(state) {
      return state.providers
    },
    visibleModels(state) {
      return state.models.filter((model) => model.provider === state.selectedProviderName)
    },
    serviceHealth(state) {
      const services = [...(state.systemStatus?.services ?? [])]
      if (state.profilerSnapshot && state.profilerHistory) {
        services.push(makeProfilerService('ok', 'direct Vue connection'))
      } else if (state.profilerSnapshot || state.profilerHistory) {
        services.push(makeProfilerService('loading', 'partial profiler data'))
      } else {
        services.push(makeProfilerService('error', 'direct Vue connection failed'))
      }
      return services
    }
  },
  state: () => ({
    systemStatus: null as SystemStatus | null,
    providers: [] as ProviderInfo[],
    profilerSnapshot: null as SystemMetrics | null,
    profilerHistory: null as SystemProfilerHistory | null,
    models: [] as LlmModel[],
    datasets: [] as DatasetSummary[],
    languages: [] as Language[],
    recentRuns: [] as BenchmarkRun[],
    currentRun: null as BenchmarkRun | null,
    tasks: [] as StudioTask[],
    selectedTaskIds: [] as string[],
    selectedProviderName: 'ollama',
    selectedModelNames: [] as string[],
    selectedDatasetNames: [] as string[],
    selectedLanguageCodes: ['en'] as string[],
    panelWidths: {
      system: 0.95,
      llms: 1.25,
      datasets: 1.45,
      queue: 1.2
    } as Record<string, number>,
    profilerErrors: [] as string[],
    loadError: '',
    loading: false
  }),
  actions: {
    rebuildTaskList() {
      const allTasks = this.recentRuns.flatMap((run) => run.tasks)
      this.tasks = allTasks
    },
    applyRuns(runs: BenchmarkRun[]) {
      this.recentRuns = runs
      this.currentRun = runs[0] ?? null
      this.rebuildTaskList()
      this.syncSelectedTasks()
    },
    syncSelectedProvider() {
      const availableProviders = this.providers.map((provider) => provider.provider)
      if (!availableProviders.length) {
        return
      }
      if (availableProviders.includes(this.selectedProviderName)) {
        return
      }
      this.selectedProviderName =
        this.systemStatus?.providers.default_provider && availableProviders.includes(this.systemStatus.providers.default_provider)
          ? this.systemStatus.providers.default_provider
          : availableProviders[0]
    },
    upsertRun(run: BenchmarkRun | null) {
      if (!run) {
        return
      }
      const existingIndex = this.recentRuns.findIndex((item) => item.id === run.id)
      if (existingIndex >= 0) {
        this.recentRuns.splice(existingIndex, 1, run)
      } else {
        this.recentRuns.unshift(run)
      }
      this.currentRun = run
      this.rebuildTaskList()
      this.syncSelectedTasks()
    },
    syncSelectedTasks() {
      const available = new Set(this.tasks.map((task) => task.id))
      this.selectedTaskIds = this.selectedTaskIds.filter((id) => available.has(id))
    },
    removeRun(runId: string) {
      this.recentRuns = this.recentRuns.filter((run) => run.id !== runId)
      this.currentRun = this.recentRuns[0] ?? null
      this.rebuildTaskList()
      this.syncSelectedTasks()
    },
    ensurePolling() {
      if (pollTimer || !this.currentRun) {
        return
      }
      pollTimer = setInterval(async () => {
        if (!this.currentRun) {
          return
        }
        try {
          const run = await fetchRun(this.currentRun.id)
          this.upsertRun(run)
          if (!['running', 'pending', 'paused'].includes(run.status)) {
            this.stopPolling()
          }
        } catch (error) {
          this.loadError = error instanceof Error ? error.message : 'Task polling failed'
          this.stopPolling()
        }
      }, 1500)
    },
    stopPolling() {
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
    },
    ensureSystemStream() {
      if (systemStream) {
        return
      }
      systemStream = openProfilerSystemStream()
      systemStream.addEventListener('profiler-snapshot', (event) => {
        const payload = JSON.parse((event as MessageEvent).data) as {
          ok: boolean
          data: SystemMetrics
        }
        this.profilerSnapshot = payload.data
        this.profilerErrors = this.profilerErrors.filter((item) => item !== 'profiler stream')
      })
      systemStream.onerror = () => {
        if (!this.profilerErrors.includes('profiler stream')) {
          this.profilerErrors = [...this.profilerErrors, 'profiler stream']
        }
        if (systemStream) {
          systemStream.close()
          systemStream = null
        }
      }
    },
    ensureProfilerHistoryPolling() {
      if (profilerHistoryTimer) {
        return
      }
      profilerHistoryTimer = setInterval(async () => {
        try {
          this.profilerHistory = await fetchProfilerHistory()
          this.profilerErrors = this.profilerErrors.filter((item) => item !== 'profiler history')
        } catch {
          if (!this.profilerErrors.includes('profiler history')) {
            this.profilerErrors = [...this.profilerErrors, 'profiler history']
          }
          return
        }
      }, 10000)
    },
    async loadInitialData() {
      this.loading = true
      this.loadError = ''
      this.profilerErrors = []
      try {
        const [systemStatus, profilerSnapshot, profilerHistory, models, datasets, languages, runs] =
          await Promise.allSettled([
          fetchSystemStatus(),
          fetchProfilerSnapshot(),
          fetchProfilerHistory(),
          fetchModels(),
          fetchDatasets(),
          fetchLanguages(),
          fetchRuns()
          ])
        if (systemStatus.status === 'fulfilled') {
          this.systemStatus = systemStatus.value
          this.providers = systemStatus.value.providers.available
          this.syncSelectedProvider()
        }
        if (profilerSnapshot.status === 'fulfilled') {
          this.profilerSnapshot = profilerSnapshot.value
          this.ensureSystemStream()
        } else {
          this.profilerErrors.push('profiler snapshot')
        }
        if (profilerHistory.status === 'fulfilled') {
          this.profilerHistory = profilerHistory.value
          this.ensureProfilerHistoryPolling()
        } else {
          this.profilerErrors.push('profiler history')
        }
        if (models.status === 'fulfilled') {
          this.models = models.value.filter(isGenerationModel)
        }
        if (datasets.status === 'fulfilled') {
          this.datasets = datasets.value
        }
        if (languages.status === 'fulfilled') {
          this.languages = languages.value
        }
        if (runs.status === 'fulfilled' && runs.value.length > 0) {
          this.applyRuns(runs.value)
          if (['running', 'pending', 'paused'].includes(runs.value[0].status)) {
            this.ensurePolling()
          }
        }
        const resultPairs = [
          ['system status', systemStatus],
          ['profiler snapshot', profilerSnapshot],
          ['profiler history', profilerHistory],
          ['models', models],
          ['datasets', datasets],
          ['languages', languages],
          ['runs', runs]
        ] as const
        const failed = resultPairs.filter(([, result]) => result.status === 'rejected')
        if (failed.length) {
          const failedNames = failed.map(([name]) => name).filter((name) => !String(name).startsWith('profiler '))
          this.loadError = failedNames.join(', ')
        }
        if (!this.selectedModelNames.length) {
          this.selectedModelNames = this.visibleModels.slice(0, 2).map((model) => model.name)
        }
        if (!this.selectedDatasetNames.length) {
          this.selectedDatasetNames = this.datasets.slice(0, 3).map((dataset) => dataset.dataset_name)
        }
        if (!this.selectedLanguageCodes.length && this.languages.length) {
          this.selectedLanguageCodes = ['en']
        }
      } finally {
        this.loading = false
      }
    },
    toggleModel(modelName: string) {
      if (this.selectedModelNames.includes(modelName)) {
        this.selectedModelNames = this.selectedModelNames.filter((item) => item !== modelName)
      } else {
        this.selectedModelNames.push(modelName)
      }
    },
    selectProvider(providerName: string) {
      if (this.selectedProviderName === providerName) {
        return
      }
      this.selectedProviderName = providerName
      this.selectedModelNames = this.selectedModelNames.filter((modelName) =>
        this.models.some((model) => model.name === modelName && model.provider === providerName)
      )
      if (!this.selectedModelNames.length) {
        this.selectedModelNames = this.visibleModels.slice(0, 2).map((model) => model.name)
      }
    },
    toggleDataset(datasetName: string) {
      if (this.selectedDatasetNames.includes(datasetName)) {
        this.selectedDatasetNames = this.selectedDatasetNames.filter((item) => item !== datasetName)
      } else {
        this.selectedDatasetNames.push(datasetName)
      }
    },
    toggleTask(taskId: string) {
      if (this.selectedTaskIds.includes(taskId)) {
        this.selectedTaskIds = this.selectedTaskIds.filter((item) => item !== taskId)
      } else {
        this.selectedTaskIds.push(taskId)
      }
    },
    selectAllTasks() {
      this.selectedTaskIds = this.tasks.map((task) => task.id)
    },
    invertTaskSelection() {
      const allTaskIds = this.tasks.map((task) => task.id)
      const selected = new Set(this.selectedTaskIds)
      this.selectedTaskIds = allTaskIds.filter((id) => !selected.has(id))
    },
    async deleteSelectedTasks() {
      if (!this.selectedTaskIds.length) {
        return
      }
      const taskIdsByRun = this.selectedTaskIds.reduce<Record<string, string[]>>((accumulator, taskId) => {
        const task = this.tasks.find((item) => item.id === taskId)
        if (!task) {
          return accumulator
        }
        accumulator[task.run_group_id] ??= []
        accumulator[task.run_group_id].push(taskId)
        return accumulator
      }, {})
      for (const [runId, taskIds] of Object.entries(taskIdsByRun)) {
        const run = await deleteRunTasks(runId, { task_ids: taskIds })
        if (!run) {
          this.removeRun(runId)
          continue
        }
        this.upsertRun(run)
      }
      this.selectedTaskIds = []
      this.syncSelectedTasks()
    },
    setPanelWidth(panel: string, width: number) {
      const clamped = Math.min(2.2, Math.max(0.72, width))
      this.panelWidths = {
        ...this.panelWidths,
        [panel]: clamped
      }
    },
    async createPreviewTasks() {
      const run = await createRun({
        model_names: this.selectedModelNames,
        dataset_names: this.selectedDatasetNames,
        language_codes: this.selectedLanguageCodes
      })
      this.upsertRun(run)
    },
    toggleLanguage(languageCode: string) {
      if (this.selectedLanguageCodes.includes(languageCode)) {
        const next = this.selectedLanguageCodes.filter((item) => item !== languageCode)
        this.selectedLanguageCodes = next.length ? next : ['en']
        return
      }
      this.selectedLanguageCodes.push(languageCode)
    },
    async playQueue() {
      if (!this.currentRun) {
        return
      }
      const activeTaskIds = this.selectedTaskIds.length
        ? this.selectedTaskIds.filter((taskId) => this.currentRun?.tasks.some((task) => task.id === taskId))
        : (this.currentRun?.tasks ?? [])
            .filter((task) => !['completed', 'error'].includes(task.status))
            .map((task) => task.id)
      if (!activeTaskIds.length) {
        return
      }
      const startingRun: BenchmarkRun = {
        ...this.currentRun,
        status: 'starting',
        tasks: this.currentRun.tasks.map((task) => {
          if (activeTaskIds.includes(task.id) && (task.status === 'pending' || task.status === 'paused' || task.status === 'stopped')) {
            return { ...task, status: 'starting' }
          }
          return task
        })
      }
      this.upsertRun(startingRun)
      const run = await playRun(this.currentRun.id, { task_ids: activeTaskIds })
      this.upsertRun(run)
      this.ensurePolling()
    },
    async pauseQueue() {
      if (!this.currentRun) {
        return
      }
      const run = await pauseRun(this.currentRun.id)
      this.upsertRun(run)
      this.ensurePolling()
    },
    async stopQueue() {
      if (!this.currentRun) {
        return
      }
      const run = await stopRun(this.currentRun.id)
      this.upsertRun(run)
      this.stopPolling()
    }
  }
})
