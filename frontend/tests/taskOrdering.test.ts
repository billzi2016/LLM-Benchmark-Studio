import { describe, expect, it } from 'vitest'

import { sortedTasks } from '../src/utils/taskOrdering'
import type { StudioTask } from '../src/types/studio'

function task(id: string, model: string, modelOrder: number, datasetOrder: number, sampleOrder: number): StudioTask {
  return {
    id,
    run_group_id: 'run-1',
    model_name: model,
    dataset_name: `dataset-${datasetOrder}`,
    sample_label: `sample-${sampleOrder}`,
    model_group_order: modelOrder,
    dataset_order: datasetOrder,
    sample_order: sampleOrder,
    progress_percent: 0
  }
}

describe('task ordering', () => {
  it('sorts benchmark tasks by model before dataset and sample', () => {
    const tasks = [
      task('b-2', 'model-b', 1, 0, 1),
      task('a-2', 'model-a', 0, 1, 0),
      task('b-1', 'model-b', 1, 0, 0),
      task('a-1', 'model-a', 0, 0, 0)
    ]

    expect(sortedTasks(tasks).map((item) => item.id)).toEqual(['a-1', 'a-2', 'b-1', 'b-2'])
  })
})
