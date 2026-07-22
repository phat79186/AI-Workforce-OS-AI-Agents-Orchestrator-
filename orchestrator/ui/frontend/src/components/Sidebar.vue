<template>
  <aside
    class="w-full lg:w-80 lg:min-w-80 bg-slate-900 border-b lg:border-b-0 lg:border-r border-slate-700/60 overflow-y-auto flex-shrink-0"
  >
    <div class="p-4 space-y-5">

      <!-- Task Input -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Task Description
          </label>
          <div v-if="store.canFollowUp" class="flex items-center space-x-2">
            <label class="flex items-center space-x-1.5 cursor-pointer group">
              <div class="relative">
                <input
                  v-model="conversationMode"
                  type="checkbox"
                  class="sr-only peer"
                />
                <div class="w-8 h-4 bg-slate-700 peer-checked:bg-violet-600 rounded-full transition-colors duration-200 cursor-pointer"></div>
                <div class="absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform duration-200 peer-checked:translate-x-4"></div>
              </div>
              <span class="text-xs text-slate-400 group-hover:text-slate-300 transition-colors">Chat mode</span>
            </label>
          </div>
        </div>
        <textarea
          v-model="store.task"
          rows="4"
          class="w-full px-3 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/60 resize-none transition-all duration-150 font-mono"
          :placeholder="conversationMode && store.canFollowUp ? 'Continue the conversation...' : 'Describe what you want to build...'"
          :disabled="store.isRunning"
          @keydown.enter.ctrl="handleExecute"
        ></textarea>
        <p v-if="conversationMode && store.canFollowUp" class="mt-1.5 text-xs text-emerald-400/80 flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span>
          Messages continue from previous task
        </p>
      </div>

      <!-- Workflow Selection -->
      <div>
        <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
          Workflow
        </label>
        <select
          v-model="store.workflow"
          class="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/60 transition-all cursor-pointer"
          :disabled="store.isRunning"
        >
          <option
            v-for="wf in workflowOptions"
            :key="wf.name"
            :value="wf.name"
            class="bg-slate-800"
          >
            {{ wf.label }}
          </option>
        </select>
      </div>

      <!-- Max Iterations -->
      <div>
        <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
          Max Iterations
        </label>
        <input
          type="number"
          v-model.number="store.maxIterations"
          min="1"
          max="10"
          class="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/60 transition-all"
          :disabled="store.isRunning"
        />
      </div>

      <!-- Execute / Cancel Buttons -->
      <div class="space-y-2">
        <button
          v-if="!store.isRunning"
          @click="handleExecute"
          :disabled="!store.task.trim()"
          class="w-full px-4 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30 focus:outline-none focus:ring-2 focus:ring-violet-500/50 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none transition-all duration-150 active:scale-[0.98]"
        >
          {{ conversationMode && store.canFollowUp ? 'Send Message' : 'Execute Task' }}
        </button>
        <button
          v-else
          @click="handleCancel"
          class="w-full px-4 py-2.5 bg-red-600/20 hover:bg-red-600/30 border border-red-500/50 hover:border-red-500/70 text-red-400 hover:text-red-300 text-sm font-semibold rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/40 transition-all duration-150 active:scale-[0.98] flex items-center justify-center gap-2"
        >
          <span class="w-2 h-2 rounded-sm bg-red-500 inline-block"></span>
          Cancel Execution
        </button>
        <p v-if="!store.isRunning && !conversationMode" class="text-xs text-slate-500 text-center">
          Ctrl+Enter to execute
        </p>
      </div>

      <!-- Follow-up Section -->
      <div v-if="store.canFollowUp && !store.isRunning" class="pt-4 border-t border-slate-700/60">
        <div class="flex items-center justify-between mb-2">
          <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Follow-up
          </label>
          <span class="text-xs text-emerald-400 flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span>
            Ready
          </span>
        </div>
        <p class="text-xs text-slate-500 mb-2 truncate">
          Last: "{{ store.lastTask.slice(0, 45) }}..."
        </p>
        <div class="flex gap-2">
          <input
            v-model="followUpInput"
            type="text"
            placeholder="Add error handling..."
            class="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500/40 transition-all"
            @keyup.enter="handleFollowUp"
          />
          <button
            @click="handleFollowUp"
            :disabled="!followUpInput.trim()"
            class="px-3 py-2 text-xs bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 hover:border-emerald-500/60 text-emerald-400 hover:text-emerald-300 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            Go
          </button>
        </div>
      </div>

      <!-- Agents Status -->
      <div class="pt-4 border-t border-slate-700/60">
        <h3 class="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">Agents</h3>
        <div class="space-y-1.5">
          <div
            v-for="agent in store.agents"
            :key="agent.name"
            class="flex items-center justify-between py-1.5 px-2.5 rounded-md bg-slate-800/50 hover:bg-slate-800 transition-colors"
          >
            <span class="text-xs text-slate-300 capitalize font-mono">{{ agent.name }}</span>
            <div class="flex items-center gap-1.5">
              <span
                :class="agent.available ? 'bg-emerald-400 shadow-emerald-400/50' : 'bg-slate-600'"
                class="w-1.5 h-1.5 rounded-full shadow-sm"
              ></span>
              <span :class="agent.available ? 'text-emerald-400' : 'text-slate-500'" class="text-xs">
                {{ agent.available ? 'ready' : 'off' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Local Models Status -->
      <div class="pt-4 border-t border-slate-700/60">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Local Models</h3>
          <button
            @click="store.loadLocalModelStatus()"
            class="text-xs px-2 py-1 rounded-md border border-slate-600 text-slate-400 hover:text-slate-200 hover:border-slate-500 hover:bg-slate-700/50 transition-all"
            :disabled="store.isRunning"
          >
            Refresh
          </button>
        </div>
        <p class="text-xs text-amber-300/90">
          Limitation: local adapters return text output only and do not directly edit files.
        </p>
        <p class="text-xs text-slate-500 mt-1.5">
          Best use: offline drafting, review feedback, and cloud-to-local fallback.
        </p>

        <div v-if="store.hasLocalModelStatus" class="space-y-2.5">
          <div
            v-for="backend in localBackends"
            :key="`${backend.backend_type}-${backend.endpoint}`"
            class="rounded-lg border border-slate-700/60 bg-slate-800/60 p-2.5 space-y-1.5"
          >
            <div class="flex items-center justify-between text-xs">
              <span class="font-semibold text-slate-200 font-mono">{{ backend.backend_type }}</span>
              <span
                :class="backend.online ? 'text-emerald-400' : 'text-red-400'"
                class="flex items-center gap-1"
              >
                <span :class="backend.online ? 'bg-emerald-400' : 'bg-red-400'" class="w-1.5 h-1.5 rounded-full inline-block"></span>
                {{ backend.online ? 'Online' : 'Offline' }}
              </span>
            </div>
            <div class="text-xs text-slate-500 break-all font-mono">{{ backend.endpoint }}</div>
            <div class="text-xs text-slate-400">Agents: {{ backend.agents.join(', ') }}</div>
            <div class="text-xs text-slate-400">Models: {{ backend.model_count }}</div>
            <div v-if="backend.models_detailed?.length" class="flex flex-wrap gap-1 pt-1">
              <span
                v-for="model in backend.models_detailed.slice(0, 6)"
                :key="model.name || model.id"
                class="text-[10px] px-2 py-0.5 rounded-full bg-slate-700/80 text-slate-300 border border-slate-600/60"
              >
                {{ formatModelLabel(model) }}
              </span>
            </div>
            <div v-else-if="backend.models?.length" class="text-[10px] text-slate-500 break-words font-mono">
              {{ backend.models.slice(0, 6).join(', ') }}
            </div>
            <div v-if="backend.probe_error" class="text-[10px] text-amber-400/80">
              {{ backend.probe_error }}
            </div>
          </div>

          <div class="space-y-1">
            <div
              v-for="agent in localAgents"
              :key="agent.name"
              class="text-xs flex items-center justify-between gap-2 px-2 py-1 rounded bg-slate-800/40"
            >
              <span class="text-slate-300 truncate font-mono">{{ agent.name }}</span>
              <span :class="agent.available_for_execution ? 'text-emerald-400' : 'text-slate-500'">
                {{ agent.available_for_execution ? 'ready' : 'not-ready' }}
              </span>
            </div>
          </div>
        </div>
        <p v-else class="text-xs text-slate-500 italic">
          No local model backends configured.
        </p>
      </div>

      <!-- Live Progress Logs -->
      <div v-if="store.isRunning" class="pt-4 border-t border-slate-700/60">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Live Progress</h3>
          <span class="text-xs text-amber-400 flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse inline-block"></span>
            Running
          </span>
        </div>
        <div
          v-if="store.hasLogs"
          class="bg-slate-950 rounded-lg p-3 max-h-40 overflow-y-auto font-mono text-xs border border-slate-700/50"
        >
          <div
            v-for="log in store.logs.slice(-5)"
            :key="log.id"
            :class="{
              'text-blue-400': log.level === 'info',
              'text-emerald-400': log.level === 'success',
              'text-amber-400': log.level === 'warn' || log.level === 'warning',
              'text-red-400': log.level === 'error',
              'text-slate-400': !['info', 'success', 'warn', 'warning', 'error'].includes(log.level)
            }"
            class="mb-1 leading-relaxed truncate"
          >
            {{ log.message }}
          </div>
        </div>
        <p v-if="store.hasLogs" class="mt-1.5 text-xs text-slate-500 text-center">
          See Logs tab for full output
        </p>
        <p v-else class="mt-1.5 text-xs text-slate-500 text-center italic">
          Waiting for execution logs...
        </p>
      </div>

      <!-- Files Created -->
      <div v-if="store.hasFiles" class="pt-4 border-t border-slate-700/60">
        <h3 class="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
          Generated Files
          <span class="ml-1 text-violet-400">({{ store.files.filter(f => !f.includes('__pycache__')).length }})</span>
        </h3>
        <p class="text-xs text-slate-500 mb-2">Open in Code Editor tab</p>
        <div class="space-y-1 max-h-28 overflow-y-auto">
          <div
            v-for="file in store.files.filter(f => !f.includes('__pycache__') && !f.endsWith('.pyc')).slice(0, 5)"
            :key="file"
            class="text-xs text-slate-400 truncate flex items-center gap-1.5 py-0.5"
          >
            <span class="text-slate-500">{{ fileIcon(file.split('/').pop()) }}</span>
            <span class="truncate font-mono">{{ file.split('/').pop() }}</span>
          </div>
        </div>
      </div>

    </div>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useOrchestratorStore } from '../stores/orchestrator'

const store = useOrchestratorStore()
const followUpInput = ref('')
const conversationMode = ref(false)
const localBackends = computed(() => store.localModelStatus?.backends || [])
const localAgents = computed(() => store.localModelStatus?.agents || [])

const workflowOptions = computed(() => {
  if (store.workflows.length > 0) {
    return store.workflows.map((wf) => ({
      name: wf.name,
      label: wf.description ? `${wf.name} (${wf.description})` : wf.name
    }))
  }

  return [
    { name: 'default', label: 'default (Codex → Gemini → Claude)' },
    { name: 'quick', label: 'quick (Codex only)' },
    { name: 'thorough', label: 'thorough (multi-review)' },
    { name: 'review-only', label: 'review-only' },
    { name: 'document', label: 'document' }
  ]
})

const fileIcon = (name) => {
  const ext = name?.split('.').pop()?.toLowerCase()
  const icons = {
    py: '🐍', js: '📜', ts: '📘', json: '📋', yaml: '⚙️', yml: '⚙️',
    md: '📝', html: '🌐', css: '🎨', sh: '🔧', txt: '📄',
  }
  return icons[ext] || '📄'
}

const formatBytes = (bytes) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return ''
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let unitIdx = 0
  while (size >= 1024 && unitIdx < units.length - 1) {
    size /= 1024
    unitIdx += 1
  }
  return `${size.toFixed(size >= 100 || unitIdx === 0 ? 0 : 1)}${units[unitIdx]}`
}

const formatModelLabel = (model) => {
  if (!model || typeof model !== 'object') return String(model || '')
  const name = model.name || model.id || 'unknown-model'
  const size = model.size_bytes ? ` (${formatBytes(Number(model.size_bytes))})` : ''
  return `${name}${size}`
}

watch(() => store.canFollowUp, (canFollowUp) => {
  if (canFollowUp && !conversationMode.value) {
    // Don't auto-enable, let user choose
  }
})

const handleExecute = () => {
  if (conversationMode.value && store.canFollowUp) {
    store.executeFollowUp(store.task)
  } else {
    store.executeTask()
    conversationMode.value = false
  }
}

const handleFollowUp = () => {
  if (followUpInput.value.trim()) {
    store.executeFollowUp(followUpInput.value)
    followUpInput.value = ''
  }
}

const handleCancel = async () => {
  try {
    const axios = (await import('axios')).default
    await axios.post('/api/cancel', { client_id: store.clientId })
  } catch (e) {
    console.error('Cancel failed:', e)
  }
}
</script>
