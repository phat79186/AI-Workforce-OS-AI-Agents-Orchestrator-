<template>
  <div class="h-full flex flex-col">
    <!-- Tab Bar - Cyan/Teal theme -->
    <div class="bg-slate-900 border-b border-cyan-500/20 px-4 pt-3 flex-shrink-0">
      <nav class="flex gap-0.5 overflow-x-auto">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'px-4 py-2 text-xs font-medium transition-all duration-150 whitespace-nowrap rounded-t-md relative',
            activeTab === tab.id
              ? 'bg-slate-800 text-cyan-300 border border-b-0 border-cyan-500/30 after:absolute after:bottom-0 after:left-0 after:right-0 after:h-px after:bg-slate-800'
              : 'text-slate-500 hover:text-cyan-300 hover:bg-cyan-500/10 border border-transparent'
          ]"
        >
          <span v-if="tab.icon" class="mr-1.5">{{ tab.icon }}</span>
          {{ tab.label }}
          <span
            v-if="tab.id === 'logs' && store.hasLogs"
            class="ml-1.5 px-1.5 py-0.5 rounded-full text-[9px] bg-slate-700 text-slate-400"
          >{{ store.logs.length }}</span>
          <span
            v-if="tab.id === 'editor' && store.hasFiles"
            class="ml-1.5 px-1.5 py-0.5 rounded-full text-[9px] bg-cyan-500/20 text-cyan-400"
          >{{ store.files.filter(f => !f.includes('__pycache__') && !f.endsWith('.pyc')).length }}</span>
        </button>
      </nav>
    </div>

    <!-- Tab Content -->
    <div class="flex-1 overflow-auto bg-slate-950">

      <!-- Output Tab with Agent Graph -->
      <div v-show="activeTab === 'output'" class="p-4 h-full">
        <!-- Agent Graph - Real-time D3 Visualization -->
        <div class="mb-4 h-1/2">
          <AgentGraph />
        </div>

        <!-- Running state -->
        <div v-if="store.isRunning" class="mb-4 border border-cyan-500/20 bg-cyan-500/5 rounded-xl p-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-cyan-300 flex items-center gap-2">
              <span class="relative flex h-2.5 w-2.5">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
              </span>
              Team Collaboration In Progress
            </h3>
          </div>
          <div
            v-if="store.hasLogs"
            class="bg-slate-950 rounded-lg p-3 max-h-44 overflow-y-auto font-mono text-xs border border-cyan-500/10"
          >
            <div
              v-for="log in store.logs.slice(-8)"
              :key="log.id"
              :class="{
                'text-cyan-400': log.level === 'info',
                'text-teal-400': log.level === 'success',
                'text-amber-400': log.level === 'warn' || log.level === 'warning',
                'text-rose-400': log.level === 'error',
                'text-slate-400': !['info', 'success', 'warn', 'warning', 'error'].includes(log.level)
              }"
              class="mb-1 leading-relaxed"
            >
              <span class="text-slate-600 mr-1">[{{ log.time }}]</span>{{ log.message }}
            </div>
          </div>
          <div v-else class="text-xs text-cyan-400/60 italic">
            Waiting for agent activity...
          </div>
        </div>

        <div v-if="store.hasOutput">
          <div class="rounded-xl overflow-hidden border border-cyan-500/20">
            <div class="flex items-center justify-between px-4 py-2.5 bg-gradient-to-r from-slate-800 to-cyan-950/30 border-b border-cyan-500/20">
              <span class="text-xs font-semibold text-cyan-300/80 uppercase tracking-wider">Team Output</span>
              <button
                @click="copyOutput"
                class="text-xs text-slate-500 hover:text-cyan-300 transition-colors"
              >Copy</button>
            </div>
            <div class="p-4 overflow-x-auto text-sm text-slate-300 leading-relaxed bg-slate-900 max-h-[60vh] overflow-y-auto prose prose-invert prose-sm max-w-none prose-pre:bg-slate-950 prose-pre:border prose-pre:border-cyan-500/20 prose-code:text-teal-400 prose-a:text-cyan-400 prose-headings:text-slate-200" v-html="renderedOutput"></div>
          </div>
        </div>
        <div v-else-if="!store.isRunning" class="flex flex-col items-center justify-center py-16 text-center">
          <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-teal-500/10 border border-cyan-500/20 flex items-center justify-center mb-4">
            <svg class="w-8 h-8 text-cyan-500/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <p class="text-sm text-slate-400 font-medium">Ready to collaborate</p>
          <p class="text-xs text-slate-600 mt-1">Assign a task to see your AI team in action</p>
        </div>
      </div>

      <!-- Editor Tab -->
      <div v-show="activeTab === 'editor'" class="h-full flex" style="min-height: 500px;">
        <!-- File Tree Panel -->
        <div class="w-56 flex-shrink-0 border-r border-cyan-500/20 bg-slate-900 overflow-y-auto flex flex-col">
          <div class="px-3 py-2.5 text-xs font-semibold text-cyan-400/60 uppercase tracking-widest border-b border-cyan-500/20 bg-slate-900/80 sticky top-0">
            Explorer
          </div>
          <div v-if="fileTree.length > 0" class="py-1 flex-1">
            <template v-for="node in fileTree" :key="node.path">
              <!-- Directory -->
              <div v-if="node.isDir">
                <button
                  @click="node.open = !node.open"
                  class="w-full text-left px-2.5 py-1.5 text-xs text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 flex items-center gap-1.5 transition-colors"
                >
                  <span class="text-slate-600 text-[10px]">{{ node.open ? '▾' : '▸' }}</span>
                  <span class="text-teal-400/80">{{ node.open ? '📂' : '📁' }}</span>
                  <span class="truncate font-mono">{{ node.name }}</span>
                </button>
                <div v-show="node.open" class="ml-3 border-l border-cyan-500/20">
                  <button
                    v-for="child in node.children"
                    :key="child.path"
                    @click="selectFile(child.path)"
                    :class="[
                      'w-full text-left px-2.5 py-1.5 text-xs flex items-center gap-1.5 transition-colors',
                      selectedFilePath === child.path
                        ? 'bg-cyan-500/15 text-cyan-300 border-r-2 border-cyan-400'
                        : 'text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10'
                    ]"
                  >
                    <span>{{ fileIcon(child.name) }}</span>
                    <span class="truncate font-mono">{{ child.name }}</span>
                  </button>
                </div>
              </div>
              <!-- Root-level file -->
              <button
                v-else
                @click="selectFile(node.path)"
                :class="[
                  'w-full text-left px-2.5 py-1.5 text-xs flex items-center gap-1.5 transition-colors',
                  selectedFilePath === node.path
                    ? 'bg-cyan-500/15 text-cyan-300 border-r-2 border-cyan-400'
                    : 'text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10'
                ]"
              >
                <span>{{ fileIcon(node.name) }}</span>
                <span class="truncate font-mono">{{ node.name }}</span>
              </button>
            </template>
          </div>
          <div v-else class="px-3 py-8 text-xs text-slate-600 italic text-center">
            No files generated yet
          </div>
        </div>

        <!-- Editor Panel -->
        <div class="flex-1 flex flex-col min-w-0 bg-slate-900">
          <!-- Editor Tab bar -->
          <div class="flex items-center justify-between px-3 py-1.5 bg-gradient-to-r from-slate-800 to-cyan-950/20 border-b border-cyan-500/20">
            <div class="flex items-center gap-2 min-w-0">
              <span v-if="store.currentFile" class="text-xs text-slate-300 font-mono truncate flex items-center gap-1.5">
                <span>{{ fileIcon(store.currentFile.filename) }}</span>
                {{ store.currentFile.filename }}
              </span>
              <span v-else class="text-xs text-slate-600 italic">Select a file from the explorer</span>
            </div>
            <button
              v-if="store.currentFile"
              @click="downloadFile"
              class="px-2.5 py-1 text-xs bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/30 hover:border-cyan-500/50 text-cyan-400 hover:text-cyan-300 rounded transition-all flex-shrink-0"
            >
              Download
            </button>
          </div>
          <!-- Monaco -->
          <div class="flex-1">
            <MonacoEditor />
          </div>
        </div>
      </div>

      <!-- Iterations Tab -->
      <div v-show="activeTab === 'iterations'" class="p-4">
        <div v-if="store.iterations.length > 0" class="space-y-3">
          <div
            v-for="(iteration, i) in store.iterations"
            :key="i"
            class="rounded-lg border border-slate-700/60 bg-slate-900 overflow-hidden"
          >
            <div class="px-4 py-2.5 bg-slate-800/80 border-b border-slate-700/60 flex items-center justify-between">
              <h4 class="text-sm font-semibold text-slate-200">Iteration {{ i + 1 }}</h4>
              <span class="text-xs text-slate-500">{{ iteration.steps?.length || 0 }} steps</span>
            </div>
            <div class="p-4 space-y-2">
              <div
                v-for="(step, j) in iteration.steps"
                :key="j"
                class="flex items-start gap-3 py-2 px-3 rounded-md"
                :class="step.success ? 'bg-emerald-500/5 border border-emerald-500/15' : 'bg-red-500/5 border border-red-500/15'"
              >
                <span
                  :class="step.success ? 'text-emerald-400 bg-emerald-400/10' : 'text-red-400 bg-red-400/10'"
                  class="w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5"
                >
                  {{ step.success ? '✓' : '✗' }}
                </span>
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium text-slate-300">
                    <span class="text-violet-400">{{ step.agent }}</span>
                    <span class="text-slate-600 mx-1">/</span>
                    <span>{{ step.task }}</span>
                  </div>
                  <div v-if="step.suggestions" class="text-xs text-slate-500 mt-0.5">
                    {{ step.suggestions.length }} suggestion{{ step.suggestions.length !== 1 ? 's' : '' }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="flex flex-col items-center justify-center py-24 text-center">
          <div class="w-12 h-12 rounded-full bg-slate-800/60 border border-slate-700/60 flex items-center justify-center mb-3">
            <svg class="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <p class="text-sm text-slate-500 italic">Iteration details will appear here...</p>
        </div>
      </div>

      <!-- Logs Tab -->
      <div v-show="activeTab === 'logs'" class="p-4">
        <div class="flex justify-between items-center mb-3">
          <h3 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
            Execution Logs
            <span v-if="store.hasLogs" class="text-xs text-slate-500 font-normal font-mono">({{ store.logs.length }} entries)</span>
          </h3>
          <button
            v-if="store.hasLogs"
            @click="store.clearLogs()"
            class="px-3 py-1 text-xs text-slate-500 hover:text-red-400 border border-slate-700 hover:border-red-500/40 rounded-md transition-all"
          >
            Clear
          </button>
        </div>
        <div v-if="store.hasLogs" class="bg-slate-950 rounded-lg border border-slate-700/60 p-4 max-h-[65vh] overflow-y-auto font-mono text-xs">
          <div
            v-for="log in store.logs"
            :key="log.id"
            class="flex items-start gap-2 mb-1 leading-relaxed hover:bg-slate-800/30 px-1 rounded -mx-1"
          >
            <span class="text-slate-600 flex-shrink-0 select-none">{{ log.time }}</span>
            <span
              :class="{
                'text-slate-500': log.level === 'info',
                'text-emerald-500': log.level === 'success',
                'text-amber-500': log.level === 'warn' || log.level === 'warning',
                'text-red-500': log.level === 'error',
                'text-slate-600': !['info', 'success', 'warn', 'warning', 'error'].includes(log.level)
              }"
              class="flex-shrink-0 w-16 font-semibold text-[10px] uppercase pt-px"
            >[{{ log.level.toUpperCase().slice(0, 4) }}]</span>
            <span
              :class="{
                'text-blue-300': log.level === 'info',
                'text-emerald-300': log.level === 'success',
                'text-amber-300': log.level === 'warn' || log.level === 'warning',
                'text-red-300': log.level === 'error',
                'text-slate-400': !['info', 'success', 'warn', 'warning', 'error'].includes(log.level)
              }"
              class="flex-1 break-words"
            >{{ log.message }}</span>
          </div>
        </div>
        <div v-else class="flex flex-col items-center justify-center py-24 text-center">
          <div class="w-12 h-12 rounded-full bg-slate-800/60 border border-slate-700/60 flex items-center justify-center mb-3">
            <svg class="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <p class="text-sm text-slate-500 italic">Execution logs will stream here in real-time...</p>
        </div>
      </div>

      <!-- Config Editor Tab -->
      <div v-show="activeTab === 'config'" class="p-4">
        <GuidedConfigEditor />
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, watch } from 'vue'
import { marked } from 'marked'
import { useOrchestratorStore } from '../stores/orchestrator'
import MonacoEditor from './MonacoEditor.vue'
import GuidedConfigEditor from './GuidedConfigEditor.vue'
import AgentGraph from './AgentGraph.vue'

const store = useOrchestratorStore()

// Render output as markdown
const renderedOutput = computed(() => {
  if (!store.output) return ''
  try {
    return marked.parse(store.output, { breaks: true, gfm: true })
  } catch {
    return store.output
  }
})

const activeTab = ref('output')
const tabs = [
  { id: 'output', label: 'Output', icon: '▶' },
  { id: 'editor', label: 'Code Editor', icon: '{}' },
  { id: 'iterations', label: 'Iterations', icon: '↻' },
  { id: 'logs', label: 'Logs', icon: '≡' },
  { id: 'config', label: 'Config', icon: '⚙' }
]

const selectedFilePath = ref('')

const fileTree = computed(() => {
  const files = (store.files || []).filter(f =>
    !f.includes('__pycache__') && !f.endsWith('.pyc')
  )
  if (!files.length) return []

  const parts = files.map(f => f.split('/'))
  let prefixLen = 0
  if (parts.length > 1) {
    const first = parts[0]
    outer: for (let i = 0; i < first.length; i++) {
      for (const p of parts) {
        if (p[i] !== first[i]) break outer
      }
      prefixLen = i + 1
    }
  } else if (parts.length === 1 && parts[0].length > 1) {
    prefixLen = parts[0].length - 1
  }

  const dirs = reactive({})
  const rootFiles = []

  for (const fullPath of files) {
    const relative = fullPath.split('/').slice(prefixLen).join('/')
    const segments = relative.split('/')
    if (segments.length === 1) {
      rootFiles.push({ name: segments[0], path: fullPath, isDir: false })
    } else {
      const dirName = segments[0]
      if (!dirs[dirName]) {
        dirs[dirName] = { name: dirName, isDir: true, open: true, children: [], path: dirName }
      }
      dirs[dirName].children.push({ name: segments.slice(1).join('/'), path: fullPath })
    }
  }

  return [...Object.values(dirs), ...rootFiles]
})

const fileIcon = (name) => {
  const ext = name?.split('.').pop()?.toLowerCase()
  const icons = {
    py: '🐍', js: '📜', ts: '📘', json: '📋', yaml: '⚙️', yml: '⚙️',
    md: '📝', html: '🌐', css: '🎨', sh: '🔧', txt: '📄',
    vue: '💚', jsx: '⚛️', tsx: '⚛️', rs: '🦀', go: '🐹',
  }
  return icons[ext] || '📄'
}

const selectFile = (path) => {
  selectedFilePath.value = path
  store.loadFile(path)
  activeTab.value = 'editor'
}

watch(() => store.currentFile, (file) => {
  if (file) activeTab.value = 'editor'
})

const downloadFile = () => {
  if (store.currentFile) {
    store.downloadFile(store.currentFile.filename, store.fileContent)
  }
}

const copyOutput = async () => {
  if (store.output) {
    try {
      await navigator.clipboard.writeText(store.output)
    } catch {}
  }
}
</script>
