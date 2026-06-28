import { defineStore } from 'pinia'

import {
  createRun,
  fetchDatasets,
  fetchLanguages,
  fetchModels,
  fetchProfilerHistory,
  fetchProfilerSnapshot,
  fetchProviders,
  fetchRun,
  fetchRuns,
  fetchSystemStatus,
  openProfilerSystemStream,
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
    selectedModelNames: [] as string[],
    selectedDatasetNames: [] as string[],
    selectedLanguageCodes: ['en'] as string[],
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
      const available = new Set(
        this.tasks.filter((task) => !['completed', 'error'].includes(task.status)).map((task) => task.id)
      )
      this.selectedTaskIds = this.selectedTaskIds.filter((id) => available.has(id))
      if (!this.selectedTaskIds.length) {
        this.selectedTaskIds = this.tasks
          .filter((task) => !['completed', 'error'].includes(task.status))
          .map((task) => task.id)
      }
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
      })
      systemStream.onerror = () => {
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
        } catch {
          return
        }
      }, 10000)
    },
    async loadInitialData() {
      this.loading = true
      this.loadError = ''
      try {
        const [systemStatus, profilerSnapshot, profilerHistory, providers, models, datasets, languages, runs] =
          await Promise.allSettled([
          fetchSystemStatus(),
          fetchProfilerSnapshot(),
          fetchProfilerHistory(),
          fetchProviders(),
          fetchModels(),
          fetchDatasets(),
          fetchLanguages(),
          fetchRuns()
          ])
        if (systemStatus.status === 'fulfilled') {
          this.systemStatus = systemStatus.value
        }
        if (profilerSnapshot.status === 'fulfilled') {
          this.profilerSnapshot = profilerSnapshot.value
          this.ensureSystemStream()
        }
        if (profilerHistory.status === 'fulfilled') {
          this.profilerHistory = profilerHistory.value
          this.ensureProfilerHistoryPolling()
        }
        if (providers.status === 'fulfilled') {
          this.providers = providers.value
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
        const failed = [systemStatus, profilerSnapshot, profilerHistory, providers, models, datasets, languages, runs].filter(
          (result) => result.status === 'rejected'
        )
        if (failed.length) {
          this.loadError = `${failed.length} API request${failed.length === 1 ? '' : 's'} failed`
        }
        if (!this.selectedModelNames.length) {
          this.selectedModelNames = this.models.slice(0, 2).map((model) => model.name)
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
    selectAllUnfinishedTasks() {
      this.selectedTaskIds = this.tasks
        .filter((task) => !['completed', 'error'].includes(task.status))
        .map((task) => task.id)
    },
    invertUnfinishedTaskSelection() {
      const unfinished = this.tasks
        .filter((task) => !['completed', 'error'].includes(task.status))
        .map((task) => task.id)
      const selected = new Set(this.selectedTaskIds)
      this.selectedTaskIds = unfinished.filter((id) => !selected.has(id))
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
        ? this.selectedTaskIds
        : this.tasks.filter((task) => !['completed', 'error'].includes(task.status)).map((task) => task.id)
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
