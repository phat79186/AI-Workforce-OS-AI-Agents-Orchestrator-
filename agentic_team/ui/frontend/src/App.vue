<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <!-- Header - Teal/Cyan theme for Agentic Team -->
    <header class="sticky top-0 z-50 bg-gradient-to-r from-slate-900 via-slate-800 to-cyan-950/40 border-b border-cyan-500/20 shadow-xl shadow-cyan-900/20">
      <div class="px-4 sm:px-6 py-3">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-center gap-3">
            <div class="flex items-center gap-2.5">
              <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-400 via-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/40 ring-2 ring-cyan-400/20">
                <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div>
                <h1 class="text-lg font-bold tracking-tight">
                  <span class="bg-gradient-to-r from-teal-300 via-cyan-300 to-blue-400 bg-clip-text text-transparent drop-shadow-[0_0_20px_rgba(34,211,238,0.5)]">Agentic Team</span>
                </h1>
                <p class="text-[10px] text-cyan-400/60 font-medium -mt-0.5 tracking-wide">Multi-Agent Collaboration</p>
              </div>
            </div>
            <div class="hidden sm:flex items-center gap-1.5 text-xs text-slate-400 font-mono border border-cyan-500/20 bg-cyan-500/5 rounded-lg px-2.5 py-1">
              <span class="w-1.5 h-1.5 rounded-full bg-cyan-400/60"></span>
              <span class="text-cyan-300/80">5 Agents</span>
            </div>
          </div>
          <div class="flex items-center gap-2.5">
            <div
              v-if="store.isRunning"
              class="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 whitespace-nowrap"
            >
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
              </span>
              Team Active &bull; {{ store.logs.length }} events
            </div>
            <StatusBadge :status="store.status" theme="cyan" />
            <button
              @click="clearAll"
              class="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded-md transition-all duration-150 border border-transparent hover:border-cyan-500/30"
            >
              Clear
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Error Banner - Styled for Agentic Team -->
    <div v-if="store.hasError" class="px-4 sm:px-6 pt-3 pb-3">
      <div class="bg-rose-950/60 border border-rose-500/40 text-rose-300 px-4 py-3 rounded-lg flex items-start justify-between backdrop-blur-sm">
        <div class="pr-4">
          <p class="text-sm font-semibold text-rose-200">Connection issue</p>
          <p class="text-xs mt-1 text-rose-300/80">{{ store.errorMessage }}</p>
        </div>
        <button
          @click="store.clearError()"
          class="text-xs text-rose-400 hover:text-rose-200 ml-4 mt-0.5 transition-colors"
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

const store = useOrchestratorStore()

onMounted(() => {
  store.init()
})

const clearAll = () => {
  store.clear()
}
</script>
