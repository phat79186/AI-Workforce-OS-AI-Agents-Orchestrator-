<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <!-- Header -->
    <header class="sticky top-0 z-50 bg-gradient-to-r from-slate-900 to-slate-800 border-b border-slate-700/60 shadow-xl shadow-black/40">
      <div class="px-4 sm:px-6 py-3">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-center gap-3">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/30">
                <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347A3 3 0 0112 15a3 3 0 01-2.121-.879l-.347-.347z" />
                </svg>
              </div>
              <h1 class="text-lg font-bold tracking-tight">
                <span class="text-white drop-shadow-[0_0_12px_rgba(139,92,246,0.6)]">AI Orchestrator</span>
              </h1>
            </div>
            <span class="hidden sm:inline text-xs text-slate-400 font-mono border border-slate-700 rounded px-2 py-0.5">
              Collaborative AI Dev
            </span>
          </div>
          <div class="flex items-center gap-2.5">
            <div
              v-if="orchestratorStore.isRunning"
              class="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 whitespace-nowrap"
            >
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
              Running &bull; {{ orchestratorStore.logs.length }} events
            </div>
            <StatusBadge :status="orchestratorStore.status" />
            <button
              @click="clearAll"
              class="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 rounded-md transition-all duration-150 border border-transparent hover:border-slate-600"
            >
              Clear
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Error Banner -->
    <div v-if="orchestratorStore.hasError" class="px-4 sm:px-6 pt-3 pb-3">
      <div class="bg-red-950/60 border border-red-500/40 text-red-300 px-4 py-3 rounded-lg flex items-start justify-between backdrop-blur-sm">
        <div class="pr-4">
          <p class="text-sm font-semibold text-red-200">Connection issue</p>
          <p class="text-xs mt-1 text-red-300/80">{{ orchestratorStore.errorMessage }}</p>
        </div>
        <button
          @click="orchestratorStore.clearError()"
          class="text-xs text-red-400 hover:text-red-200 ml-4 mt-0.5 transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>

    <!-- Main Layout -->
    <div class="flex flex-col lg:flex-row min-h-[calc(100vh-3.5rem)]">
      <Sidebar />
      <main class="flex-1 overflow-auto min-w-0">
        <MainContent />
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useOrchestratorStore } from './stores/orchestrator'
import Sidebar from './components/Sidebar.vue'
import MainContent from './components/MainContent.vue'
import StatusBadge from './components/StatusBadge.vue'

const orchestratorStore = useOrchestratorStore()

onMounted(() => {
  orchestratorStore.init()
})

const clearAll = () => {
  orchestratorStore.clear()
}
</script>
