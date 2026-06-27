<script setup lang="ts">
import { ref } from 'vue'
import { Download } from 'lucide-vue-next'

import { downloadFile } from '../../api/client'

const loading = ref(false)

async function exportResults() {
  loading.value = true
  try {
    await downloadFile('/api/results/export', 'llm-benchmark-results.zip')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <button class="export-button" type="button" :disabled="loading" @click="exportResults">
    <Download :size="16" />
    {{ loading ? 'Exporting' : 'Export' }}
  </button>
</template>
