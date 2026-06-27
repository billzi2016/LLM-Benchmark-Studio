export interface SystemStatus {
  service: string
  status: string
  services: SystemService[]
  providers: {
    default_provider: string
    judge_provider: string
    judge_model: string
    translate_provider: string
    translate_model: string
  }
  contexts: {
    think: number
    no_think: number
  }
  counts: Record<string, number>
}

export interface SystemService {
  name: string
  label: string
  status: string
  detail: string
}

export interface ProviderInfo {
  provider: string
  protocol: string
  base_url: string
  enabled: boolean
  api_key_configured: boolean
}

export interface LlmModel {
  name: string
  provider: string
  family: string
  supports_think: boolean
  context_length: number
  activate: boolean
  installed: boolean
  metadata: Record<string, unknown>
}

export interface DatasetSummary {
  dataset_name: string
  display_name: string
  subset: string
  source_language: string
  task_type: string
  activate: boolean
  question_count: number
  path: string
}

export interface Language {
  code: string
  name: string
  native_name: string
  activate: boolean
  metadata: Record<string, unknown>
}

export interface StudioTask {
  id: string
  run_group_id: string
  language_code: string
  needs_translation: boolean
  model_name: string
  dataset_name: string
  dataset_display_name: string
  total_questions: number
  completed_questions: number
  model_group_order: number
  dataset_order: number
  progress_percent: number
}
