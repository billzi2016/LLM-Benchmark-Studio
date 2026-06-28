import type { StudioTask } from '../types/studio'

export function compareTasksByModelFirst(left: StudioTask, right: StudioTask): number {
  const leftRunCreatedAt = left.run_created_at ? new Date(left.run_created_at).getTime() : 0
  const rightRunCreatedAt = right.run_created_at ? new Date(right.run_created_at).getTime() : 0
  return (
    rightRunCreatedAt - leftRunCreatedAt ||
    left.run_group_id.localeCompare(right.run_group_id) ||
    Number(right.needs_translation) - Number(left.needs_translation) ||
    left.model_group_order - right.model_group_order ||
    left.dataset_order - right.dataset_order ||
    left.language_code.localeCompare(right.language_code) ||
    left.id.localeCompare(right.id)
  )
}

export function sortedTasks(tasks: StudioTask[]): StudioTask[] {
  return [...tasks].sort(compareTasksByModelFirst)
}
