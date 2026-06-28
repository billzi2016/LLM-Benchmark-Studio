<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Activity, Database, Download, Languages, Pause, Play, RefreshCw, Square, Workflow } from 'lucide-vue-next'

import { useStudioStore } from './stores/studioStore'
import ExportResultsButton from './components/results/ExportResultsButton.vue'
import StatusBadge from './components/shared/StatusBadge.vue'
import { sortedTasks } from './utils/taskOrdering'

const store = useStudioStore()
const activeResize = ref<null | { panel: string; startX: number; startWidth: number }>(null)
const visibleModels = computed(() => store.visibleModels)
const visibleProviders = computed(() => store.visibleProviders)

function formatEta(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`
}

function formatElapsed(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`
  }
  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`
}

function formatTaskKind(taskKind: string): string {
  return taskKind === 'translation' ? 'translation' : 'benchmark'
}

function formatBytesToGiB(value: number): string {
  return `${(value / 1024 / 1024 / 1024).toFixed(1)} GiB`
}

function formatMetricPercent(value: number | null | undefined): string {
  return value == null ? 'Unavailable' : `${value}%`
}

function formatLanguageName(code: string): string {
  const language = store.languages.find((item) => item.code === code)
  return language?.name ?? code
}

function formatProviderDetail(provider: { detail?: string; protocol: string; base_url: string }): string {
  return provider.detail ?? `${provider.protocol} · ${provider.base_url}`
}

function metricSeries(metric: 'cpu' | 'gpu' | 'memory' | 'disk'): number[] {
  const snapshots = store.profilerHistory?.snapshots ?? []
  if (!snapshots.length) {
    return []
  }
  if (metric === 'cpu') {
    return snapshots.map((item) => item.cpu.percent ?? 0)
  }
  if (metric === 'gpu') {
    return snapshots.map((item) => item.gpu.utilization_percent ?? 0)
  }
  if (metric === 'memory') {
    return snapshots.map((item) => (item.memory.total_bytes > 0 ? (item.memory.used_bytes / item.memory.total_bytes) * 100 : 0))
  }
  return snapshots.map((item) => item.disk.percent ?? 0)
}

function sparklinePoints(metric: 'cpu' | 'gpu' | 'memory' | 'disk'): string {
  const snapshots = store.profilerHistory?.snapshots ?? []
  if (!snapshots.length) {
    return ''
  }
  const windowSeconds = 600
  const latestTimestamp = new Date(snapshots[snapshots.length - 1].timestamp).getTime()
  if (!Number.isFinite(latestTimestamp)) {
    return ''
  }
  return snapshots
    .map((snapshot) => {
      const value =
        metric === 'cpu'
          ? snapshot.cpu.percent ?? 0
          : metric === 'gpu'
            ? snapshot.gpu.utilization_percent ?? 0
            : metric === 'memory'
              ? snapshot.memory.total_bytes > 0
                ? (snapshot.memory.used_bytes / snapshot.memory.total_bytes) * 100
                : 0
              : snapshot.disk.percent ?? 0
      const pointTimestamp = new Date(snapshot.timestamp).getTime()
      const ageSeconds = Math.max(0, (latestTimestamp - pointTimestamp) / 1000)
      const x = Math.max(0, 100 - (ageSeconds / windowSeconds) * 100)
      const y = 100 - Math.max(0, Math.min(100, value))
      return `${x},${y}`
    })
    .join(' ')
}

function profilerMetricPercent(metric: 'cpu' | 'gpu' | 'disk'): string {
  const snapshot = store.profilerSnapshot
  if (!snapshot) {
    return 'Unavailable'
  }
  if (metric === 'cpu') {
    return formatMetricPercent(snapshot.cpu.percent)
  }
  if (metric === 'gpu') {
    return formatMetricPercent(snapshot.gpu.utilization_percent)
  }
  return formatMetricPercent(snapshot.disk.percent)
}

onMounted(() => {
  void store.loadInitialData()
})

function beginResize(panel: string, event: MouseEvent) {
  activeResize.value = {
    panel,
    startX: event.clientX,
    startWidth: store.panelWidths[panel]
  }
  window.addEventListener('mousemove', handleResize)
  window.addEventListener('mouseup', stopResize)
}

function handleResize(event: MouseEvent) {
  if (!activeResize.value) {
    return
  }
  const delta = (event.clientX - activeResize.value.startX) / window.innerWidth
  store.setPanelWidth(activeResize.value.panel, activeResize.value.startWidth + delta * 4)
}

function stopResize() {
  activeResize.value = null
  window.removeEventListener('mousemove', handleResize)
  window.removeEventListener('mouseup', stopResize)
}
</script>

<template>
  <main class="studio-shell">
    <header class="topbar">
      <div class="brand">
        <Workflow :size="20" />
        <div>
          <h1>LLM Benchmark Studio</h1>
          <p>Model-first benchmark queue</p>
        </div>
      </div>
      <div class="topbar-actions">
        <StatusBadge :status="store.systemStatus?.status ?? 'loading'" />
        <button class="icon-button" type="button" title="Refresh" @click="store.loadInitialData">
          <RefreshCw :size="17" />
        </button>
        <ExportResultsButton />
      </div>
    </header>

    <section
      class="workspace-grid"
      :style="{
        gridTemplateColumns: `${store.panelWidths.system}fr 6px ${store.panelWidths.llms}fr 6px ${store.panelWidths.datasets}fr 6px ${store.panelWidths.queue}fr`
      }"
    >
      <aside class="panel system-panel">
        <div class="panel-heading">
          <Activity :size="18" />
          <h2>System</h2>
        </div>
        <p v-if="store.loadError" class="inline-error">{{ store.loadError }}</p>
        <div class="metric-grid">
          <div class="metric">
            <span>Backend</span>
            <strong>{{ store.systemStatus?.service ?? 'django' }}</strong>
          </div>
          <div class="metric">
            <span>Provider</span>
            <strong>{{ store.systemStatus?.providers.default_provider ?? '-' }}</strong>
          </div>
          <div class="metric">
            <span>Judge</span>
            <strong>{{ store.systemStatus?.providers.judge_model ?? '-' }}</strong>
          </div>
          <div class="metric">
            <span>Think ctx</span>
            <strong>{{ store.systemStatus?.contexts.think ?? '-' }}</strong>
          </div>
          <div class="metric metric-chart">
            <svg class="metric-sparkline" viewBox="0 0 100 100" preserveAspectRatio="none">
              <polyline :points="sparklinePoints('cpu')" />
            </svg>
            <span>CPU</span>
            <strong>{{ profilerMetricPercent('cpu') }}</strong>
          </div>
          <div class="metric metric-chart">
            <svg class="metric-sparkline" viewBox="0 0 100 100" preserveAspectRatio="none">
              <polyline :points="sparklinePoints('gpu')" />
            </svg>
            <span>GPU</span>
            <strong>{{ profilerMetricPercent('gpu') }}</strong>
          </div>
          <div class="metric metric-chart">
            <svg class="metric-sparkline" viewBox="0 0 100 100" preserveAspectRatio="none">
              <polyline :points="sparklinePoints('memory')" />
            </svg>
            <span>Memory</span>
            <strong>{{
              store.profilerSnapshot && store.profilerSnapshot.memory.total_bytes > 0
                ? `${formatBytesToGiB(store.profilerSnapshot.memory.used_bytes)} / ${formatBytesToGiB(store.profilerSnapshot.memory.total_bytes)}`
                : 'Unavailable'
            }}</strong>
          </div>
          <div class="metric metric-chart">
            <svg class="metric-sparkline" viewBox="0 0 100 100" preserveAspectRatio="none">
              <polyline :points="sparklinePoints('disk')" />
            </svg>
            <span>Disk</span>
            <strong>{{ profilerMetricPercent('disk') }}</strong>
          </div>
        </div>
        <div class="list-section">
          <h3>Service Health</h3>
          <div
            v-for="service in store.systemStatus?.services ?? []"
            :key="service.name"
            class="row-item health-row"
          >
            <div>
              <strong>{{ service.label }}</strong>
              <span>{{ service.detail }}</span>
            </div>
            <StatusBadge :status="service.status" />
          </div>
        </div>
        <div class="list-section">
          <h3>Providers</h3>
          <button
            v-for="provider in visibleProviders"
            :key="provider.provider"
            type="button"
            class="row-item provider-row"
            :class="{ selected: store.selectedProviderName === provider.provider }"
            @click="store.selectProvider(provider.provider)"
          >
            <div class="provider-copy">
              <strong>{{ provider.provider }}</strong>
              <span>{{ formatProviderDetail(provider) }}</span>
            </div>
            <StatusBadge :status="provider.status ?? (provider.enabled ? 'on' : 'off')" />
          </button>
        </div>
      </aside>
      <div class="panel-resizer" @mousedown="beginResize('system', $event)"></div>

      <aside class="panel">
        <div class="panel-heading">
          <Database :size="18" />
          <h2>LLMs</h2>
        </div>
        <div class="scroll-list">
          <button
            v-for="model in visibleModels"
            :key="model.name"
            class="model-row"
            :class="{ selected: store.selectedModelNames.includes(model.name) }"
            type="button"
            @click="store.toggleModel(model.name)"
          >
            <span class="model-name">{{ model.name }}</span>
            <span class="model-meta">{{ model.provider }} · {{ model.supports_think ? 'Think' : 'Direct' }}</span>
          </button>
          <div v-if="!visibleModels.length" class="row-item empty-row">
            <strong>No models</strong>
            <span>No installed generation model for {{ store.selectedProviderName }}.</span>
          </div>
        </div>
      </aside>
      <div class="panel-resizer" @mousedown="beginResize('llms', $event)"></div>

      <section class="panel datasets-panel">
        <div class="panel-heading">
          <Languages :size="18" />
          <h2>Datasets</h2>
        </div>
        <div class="dataset-table">
          <button
            v-for="dataset in store.datasets"
            :key="dataset.dataset_name"
            type="button"
            class="dataset-row"
            :class="{ selected: store.selectedDatasetNames.includes(dataset.dataset_name) }"
            @click="store.toggleDataset(dataset.dataset_name)"
          >
            <span>{{ dataset.display_name }}</span>
            <strong>{{ dataset.question_count.toLocaleString() }}</strong>
          </button>
        </div>
        <div class="language-strip">
          <button
            v-for="language in store.languages.filter((item) => item.activate)"
            :key="language.code"
            type="button"
            :class="{ selected: store.selectedLanguageCodes.includes(language.code) }"
            @click="store.toggleLanguage(language.code)"
          >
            {{ language.name }}
          </button>
        </div>
        <button class="primary-action" type="button" @click="store.createPreviewTasks">
          <Play :size="16" />
          Create Model-First Queue
        </button>
      </section>
      <div class="panel-resizer" @mousedown="beginResize('datasets', $event)"></div>

      <aside class="panel tasks-panel">
        <div class="panel-heading">
          <Workflow :size="18" />
          <h2>Task Queue</h2>
        </div>
        <div class="task-controls">
          <button type="button" title="Play" @click="store.playQueue"><Play :size="16" /></button>
          <button type="button" title="Pause" @click="store.pauseQueue"><Pause :size="16" /></button>
          <button type="button" title="Stop" @click="store.stopQueue"><Square :size="16" /></button>
          <button type="button" title="Select all tasks" @click="store.selectAllTasks()">All</button>
          <button type="button" title="Invert task selection" @click="store.invertTaskSelection()">Invert</button>
          <button type="button" title="Delete selected tasks" @click="store.deleteSelectedTasks()">Delete</button>
        </div>
        <div class="scroll-list task-list">
          <div
            v-for="task in sortedTasks(store.tasks)"
            :key="task.id"
            class="task-row"
            :class="{
              'task-row-running': task.status === 'running' || task.status === 'starting',
              'task-row-completed': task.status === 'completed'
            }"
          >
            <label class="task-select-row">
              <input
                type="checkbox"
                :checked="store.selectedTaskIds.includes(task.id)"
                @change="store.toggleTask(task.id)"
              />
              <span>Select</span>
            </label>
            <strong class="task-title">
              {{ task.model_name }} · {{ formatLanguageName(task.language_code) }} · {{ task.dataset_display_name }} · {{ formatTaskKind(task.task_kind) }}
            </strong>
            <div class="task-progress-row">
              <span class="task-progress-meta">
                {{ task.status === 'starting' ? 'starting...' : task.status }} · ETA {{ formatEta(task.eta_seconds) }} ·
                elapsed {{ formatElapsed(task.elapsed_seconds) }} ·
                {{ task.completed_questions.toLocaleString() }} / {{ task.total_questions.toLocaleString() }}
              </span>
              <div class="progress-track">
                <div class="progress-fill" :style="{ width: `${task.progress_percent}%` }"></div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </section>
  </main>
</template>
