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
    available: ProviderInfo[]
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

export interface SystemMetrics {
  timestamp: string
  system: Record<string, unknown>
  cpu: {
    percent: number
    physical_cores: number
    logical_cores: number
    per_cpu_percent: number[]
    load_average: Record<string, number>
    times_percent: Record<string, number>
  }
  memory: {
    total_bytes: number
    used_bytes: number
    available_bytes: number
    free_bytes: number
    percent: number
    swap_total_bytes: number
    swap_used_bytes: number
    swap_percent: number
    active_bytes: number
    inactive_bytes: number
    wired_bytes: number
    compressed_bytes: number
  }
  gpu: {
    available: boolean
    vendor: string
    name: string
    utilization_percent: number | null
    renderer_utilization_percent: number | null
    tiler_utilization_percent: number | null
    ane_utilization_percent: number | null
  }
  disk: {
    path: string
    total_bytes: number
    used_bytes: number
    free_bytes: number
    percent: number
  }
  network: {
    bytes_sent: number
    bytes_recv: number
    packets_sent: number
    packets_recv: number
    errin: number
    errout: number
    dropin: number
    dropout: number
  }
  process: {
    pid: number
    cpu_percent: number
    memory_percent: number
    rss_bytes?: number
    vms_bytes?: number
    threads: number
    open_files?: number
  }
}

export interface SystemProfilerHistory {
  interval_seconds: number
  window_minutes: number
  snapshots: SystemMetrics[]
}

export interface ProviderInfo {
  provider: string
  protocol: string
  base_url: string
  enabled: boolean
  api_key_configured: boolean
  status?: string
  detail?: string
  model_count?: number | null
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
  run_created_at?: string | null
  language_code: string
  needs_translation: boolean
  task_kind: 'translation' | 'benchmark'
  status: 'pending' | 'starting' | 'running' | 'paused' | 'completed' | 'stopped' | 'error'
  eta_seconds: number
  model_name: string
  dataset_name: string
  dataset_display_name: string
  total_questions: number
  completed_questions: number
  model_group_order: number
  dataset_order: number
  progress_percent: number
  started_at: string | null
  finished_at: string | null
  elapsed_seconds: number
  walltime_seconds: number
  source_language?: string
  error_message?: string
}

export interface BenchmarkRun {
  id: string
  status: string
  language_code: string
  provider_name: string
  judge_provider: string
  judge_model: string
  translate_provider: string
  translate_model: string
  total_tasks: number
  completed_tasks: number
  started_at: string | null
  finished_at: string | null
  error_message: string
  tasks: StudioTask[]
}
