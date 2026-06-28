import { describe, expect, it } from 'vitest'

import { buildPreviewTasks } from '../frontend/src/utils/taskQueue'
import type { DatasetSummary } from '../frontend/src/types/studio'

const datasets: DatasetSummary[] = [
  {
    dataset_name: 'mmlu',
    display_name: 'MMLU',
    subset: 'all',
    source_language: 'en',
    task_type: 'multiple_choice',
    activate: true,
    question_count: 14042,
    path: 'data/benchmark_datasets/mmlu.json'
  },
  {
    dataset_name: 'french_set',
    display_name: 'French Set',
    subset: 'all',
    source_language: 'fr',
    task_type: 'multiple_choice',
    activate: true,
    question_count: 500,
    path: 'data/benchmark_datasets/french_set.json'
  }
]

describe('overall task queue semantics', () => {
  it('creates one task per language-dataset-model tuple', () => {
    const tasks = buildPreviewTasks(['model-a', 'model-b'], [datasets[0]], ['fr'], 'run-1')
    expect(tasks).toHaveLength(3)
    expect(tasks.filter((task) => task.task_kind === 'translation')).toHaveLength(1)
    expect(tasks.filter((task) => task.task_kind === 'benchmark')).toHaveLength(2)
    expect(tasks.every((task) => task.total_questions === 14042)).toBe(true)
  })

  it('marks translation as required when target language differs from source language', () => {
    const tasks = buildPreviewTasks(['model-a'], datasets, ['fr'], 'run-1')
    expect(tasks[0].needs_translation).toBe(true)
    expect(tasks[0].task_kind).toBe('translation')
    const frenchBenchmarkTask = tasks.find((task) => task.dataset_name === 'french_set' && task.task_kind === 'benchmark')
    expect(frenchBenchmarkTask?.needs_translation).toBe(false)
  })

  it('initializes time tracking fields for each task', () => {
    const [task] = buildPreviewTasks(['model-a'], [datasets[0]], ['en'], 'run-1')
    expect(task.started_at).toBeNull()
    expect(task.finished_at).toBeNull()
    expect(task.elapsed_seconds).toBe(0)
    expect(task.walltime_seconds).toBe(0)
  })
})
