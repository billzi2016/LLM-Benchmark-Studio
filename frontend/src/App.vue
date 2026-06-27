<script setup lang="ts">
import { onMounted } from 'vue'
import { Activity, Database, Download, Languages, Pause, Play, RefreshCw, Square, Workflow } from 'lucide-vue-next'

import { useStudioStore } from './stores/studioStore'
import ExportResultsButton from './components/results/ExportResultsButton.vue'
import StatusBadge from './components/shared/StatusBadge.vue'
import { sortedTasks } from './utils/taskOrdering'

const store = useStudioStore()

onMounted(() => {
  void store.loadInitialData()
})
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

    <section class="workspace-grid">
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
          <div v-for="provider in store.providers" :key="provider.provider" class="row-item">
            <div>
              <strong>{{ provider.provider }}</strong>
              <span>{{ provider.protocol }} · {{ provider.base_url }}</span>
            </div>
            <StatusBadge :status="provider.enabled ? 'on' : 'off'" />
          </div>
        </div>
      </aside>

      <aside class="panel">
        <div class="panel-heading">
          <Database :size="18" />
          <h2>LLMs</h2>
        </div>
        <div class="scroll-list">
          <button
            v-for="model in store.models"
            :key="model.name"
            class="model-row"
            :class="{ selected: store.selectedModelNames.includes(model.name), disabled: !model.activate }"
            type="button"
            @click="store.toggleModel(model.name)"
          >
            <span class="model-name">{{ model.name }}</span>
            <span class="model-meta">{{ model.provider }} · {{ model.supports_think ? 'Think' : 'Direct' }}</span>
          </button>
        </div>
      </aside>

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
            :class="{ selected: store.selectedLanguage === language.code }"
            @click="store.selectedLanguage = language.code"
          >
            {{ language.code }}
          </button>
        </div>
        <button class="primary-action" type="button" @click="store.createPreviewTasks">
          <Play :size="16" />
          Create Model-First Queue
        </button>
      </section>

      <aside class="panel tasks-panel">
        <div class="panel-heading">
          <Workflow :size="18" />
          <h2>Task Queue</h2>
        </div>
        <div class="task-controls">
          <button type="button" title="Play"><Play :size="16" /></button>
          <button type="button" title="Pause"><Pause :size="16" /></button>
          <button type="button" title="Stop"><Square :size="16" /></button>
        </div>
        <div class="scroll-list task-list">
          <div v-for="task in sortedTasks(store.tasks)" :key="task.id" class="task-row">
            <div>
              <strong>{{ task.model_name }}</strong>
              <span>{{ task.dataset_name }} · {{ task.sample_label }}</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${task.progress_percent}%` }"></div>
            </div>
          </div>
        </div>
      </aside>
    </section>
  </main>
</template>
