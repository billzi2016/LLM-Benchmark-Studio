import type { StudioTask } from '../types/studio'

export function compareTasksByModelFirst(left: StudioTask, right: StudioTask): number {
  return (
    left.run_group_id.localeCompare(right.run_group_id) ||
    left.model_group_order - right.model_group_order ||
    left.dataset_order - right.dataset_order ||
    left.sample_order - right.sample_order ||
    left.id.localeCompare(right.id)
  )
}

export function sortedTasks(tasks: StudioTask[]): StudioTask[] {
  return [...tasks].sort(compareTasksByModelFirst)
}
