import { defineStore } from 'pinia'

import { fetchDatasets, fetchLanguages, fetchModels, fetchProviders, fetchSystemStatus } from '../api/studio'
import type { DatasetSummary, Language, LlmModel, ProviderInfo, StudioTask, SystemStatus } from '../types/studio'

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

export const useStudioStore = defineStore('studio', {
  state: () => ({
    systemStatus: null as SystemStatus | null,
    providers: [] as ProviderInfo[],
    models: [] as LlmModel[],
    datasets: [] as DatasetSummary[],
    languages: [] as Language[],
    tasks: [] as StudioTask[],
    selectedModelNames: [] as string[],
    selectedDatasetNames: [] as string[],
    selectedLanguage: 'en',
    loadError: '',
    loading: false
  }),
  actions: {
    async loadInitialData() {
      this.loading = true
      this.loadError = ''
      try {
        const [systemStatus, providers, models, datasets, languages] = await Promise.allSettled([
          fetchSystemStatus(),
          fetchProviders(),
          fetchModels(),
          fetchDatasets(),
          fetchLanguages()
        ])
        if (systemStatus.status === 'fulfilled') {
          this.systemStatus = systemStatus.value
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
        const failed = [systemStatus, providers, models, datasets, languages].filter(
          (result) => result.status === 'rejected'
        )
        if (failed.length) {
          this.loadError = `${failed.length} API request${failed.length === 1 ? '' : 's'} failed`
        }
        if (!this.selectedModelNames.length) {
          this.selectedModelNames = this.models.filter((model) => model.activate).slice(0, 2).map((model) => model.name)
        }
        if (!this.selectedDatasetNames.length) {
          this.selectedDatasetNames = this.datasets.slice(0, 3).map((dataset) => dataset.dataset_name)
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
    createPreviewTasks() {
      const runGroupId = `preview-${Date.now()}`
      const selectedDatasets = this.datasets.filter((dataset) => this.selectedDatasetNames.includes(dataset.dataset_name))
      this.tasks = this.selectedModelNames.flatMap((modelName, modelIndex) =>
        selectedDatasets.flatMap((dataset, datasetIndex) =>
          [0, 1, 2].map((sampleIndex) => ({
            id: `${runGroupId}-${modelIndex}-${datasetIndex}-${sampleIndex}`,
            run_group_id: runGroupId,
            model_name: modelName,
            dataset_name: dataset.dataset_name,
            sample_label: `sample ${sampleIndex + 1}`,
            model_group_order: modelIndex,
            dataset_order: datasetIndex,
            sample_order: sampleIndex,
            progress_percent: 0
          }))
        )
      )
    }
  }
})
