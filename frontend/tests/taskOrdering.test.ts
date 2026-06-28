import { describe, expect, it } from 'vitest'

import { sortedTasks } from '../src/utils/taskOrdering'
import type { StudioTask } from '../src/types/studio'

function task(id: string, model: string, modelOrder: number, datasetOrder: number, languageCode = 'en'): StudioTask {
  return {
    id,
    run_group_id: 'run-1',
    run_created_at: '2026-06-27T23:30:00Z',
    language_code: languageCode,
    needs_translation: false,
    task_kind: 'benchmark',
    status: 'pending',
    eta_seconds: 0,
    model_name: model,
    dataset_name: `dataset-${datasetOrder}`,
    dataset_display_name: `Dataset ${datasetOrder}`,
    total_questions: 100,
    completed_questions: 0,
    model_group_order: modelOrder,
    dataset_order: datasetOrder,
    progress_percent: 0,
    started_at: null,
    finished_at: null,
    elapsed_seconds: 0,
    walltime_seconds: 0
  }
}

describe('task ordering', () => {
  it('sorts tasks by model before dataset and language', () => {
    const tasks = [
      task('b-2', 'model-b', 1, 0, 'fr'),
      task('a-2', 'model-a', 0, 1, 'en'),
      task('b-1', 'model-b', 1, 0, 'en'),
      task('a-1', 'model-a', 0, 0, 'en')
    ]

    expect(sortedTasks(tasks).map((item) => item.id)).toEqual(['a-1', 'a-2', 'b-1', 'b-2'])
  })

  it('puts translation tasks before benchmark tasks', () => {
    const translationTask: StudioTask = {
      ...task('translate-1', 'model-a', 0, 1, 'fr'),
      needs_translation: true,
      task_kind: 'translation'
    }
    const benchmarkTask = task('benchmark-1', 'model-a', 0, 0, 'en')

    expect(sortedTasks([benchmarkTask, translationTask]).map((item) => item.id)).toEqual([
      'translate-1',
      'benchmark-1'
    ])
  })

  it('accepts starting status for immediate UI feedback', () => {
    const startingTask: StudioTask = {
      ...task('starting-1', 'model-a', 0, 0, 'en'),
      status: 'starting'
    }

    expect(sortedTasks([startingTask])[0].status).toBe('starting')
  })
})
