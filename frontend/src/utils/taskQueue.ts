import type { DatasetSummary, StudioTask } from '../types/studio'

export function buildPreviewTasks(
  selectedModelNames: string[],
  selectedDatasets: DatasetSummary[],
  selectedLanguage: string,
  runGroupId: string
): StudioTask[] {
  return selectedModelNames.flatMap((modelName, modelIndex) =>
    selectedDatasets.map((dataset, datasetIndex) => ({
      id: `${runGroupId}-${modelIndex}-${datasetIndex}`,
      run_group_id: runGroupId,
      language_code: selectedLanguage,
      needs_translation: dataset.source_language !== selectedLanguage,
      task_kind: dataset.source_language !== selectedLanguage ? 'translation' : 'benchmark',
      status: 'pending',
      eta_seconds: 0,
      model_name: modelName,
      dataset_name: dataset.dataset_name,
      dataset_display_name: dataset.display_name,
      total_questions: dataset.question_count,
      completed_questions: 0,
      model_group_order: modelIndex,
      dataset_order: datasetIndex,
      progress_percent: 0,
      started_at: null,
      finished_at: null,
      elapsed_seconds: 0,
      walltime_seconds: 0
    }))
  )
}
