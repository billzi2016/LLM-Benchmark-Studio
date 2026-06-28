import type { DatasetSummary, StudioTask } from '../types/studio'

export function buildPreviewTasks(
  selectedModelNames: string[],
  selectedDatasets: DatasetSummary[],
  selectedLanguages: string[],
  runGroupId: string
): StudioTask[] {
  const translationTasks = selectedLanguages.flatMap((languageCode, languageIndex) =>
    selectedDatasets
      .filter((dataset) => dataset.source_language !== languageCode)
      .map((dataset, datasetIndex) => ({
        id: `${runGroupId}-translation-${languageIndex}-${datasetIndex}`,
        run_group_id: runGroupId,
        language_code: languageCode,
        needs_translation: true,
        task_kind: 'translation' as const,
        status: 'pending' as const,
        eta_seconds: 0,
        model_name: 'translation',
        dataset_name: dataset.dataset_name,
        dataset_display_name: dataset.display_name,
        total_questions: dataset.question_count,
        completed_questions: 0,
        model_group_order: 0,
        dataset_order: datasetIndex,
        progress_percent: 0,
        started_at: null,
        finished_at: null,
        elapsed_seconds: 0,
        walltime_seconds: 0
      }))
  )

  const benchmarkTasks = selectedLanguages.flatMap((languageCode) =>
    selectedModelNames.flatMap((modelName, modelIndex) =>
      selectedDatasets.map((dataset, datasetIndex) => ({
        id: `${runGroupId}-benchmark-${languageCode}-${modelIndex}-${datasetIndex}`,
        run_group_id: runGroupId,
        language_code: languageCode,
        needs_translation: dataset.source_language !== languageCode,
        task_kind: 'benchmark' as const,
        status: 'pending' as const,
        eta_seconds: 0,
        model_name: modelName,
        dataset_name: dataset.dataset_name,
        dataset_display_name: dataset.display_name,
        total_questions: dataset.question_count,
        completed_questions: 0,
        model_group_order: translationTasks.length + modelIndex + 1,
        dataset_order: datasetIndex,
        progress_percent: 0,
        started_at: null,
        finished_at: null,
        elapsed_seconds: 0,
        walltime_seconds: 0
      }))
    )
  )

  return [...translationTasks, ...benchmarkTasks]
}
