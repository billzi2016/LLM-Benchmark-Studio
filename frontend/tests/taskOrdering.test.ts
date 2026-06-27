import { describe, expect, it } from 'vitest'

import { sortedTasks } from '../src/utils/taskOrdering'
import type { StudioTask } from '../src/types/studio'

function task(id: string, model: string, modelOrder: number, datasetOrder: number, languageCode = 'en'): StudioTask {
  return {
    id,
    run_group_id: 'run-1',
    language_code: languageCode,
    needs_translation: false,
    model_name: model,
    dataset_name: `dataset-${datasetOrder}`,
    dataset_display_name: `Dataset ${datasetOrder}`,
    total_questions: 100,
    completed_questions: 0,
    model_group_order: modelOrder,
    dataset_order: datasetOrder,
    progress_percent: 0
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
})
