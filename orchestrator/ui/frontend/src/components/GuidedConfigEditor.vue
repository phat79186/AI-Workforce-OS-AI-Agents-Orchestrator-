<template>
  <div class="bg-slate-900 rounded-xl border border-slate-700/60 p-4 sm:p-6 space-y-6 overflow-x-hidden">
    <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
      <div class="min-w-0">
        <h3 class="text-base font-semibold text-slate-100">Config Editor</h3>
        <p class="text-xs text-slate-500 break-all font-mono mt-0.5">{{ store.configPath || "No config path loaded" }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          class="px-3 py-1.5 text-xs rounded-md border border-slate-600 text-slate-400 hover:text-slate-200 hover:border-slate-500 hover:bg-slate-700/50 transition-all disabled:opacity-40"
          :disabled="store.configLoading || store.configSaving"
          @click="store.loadConfig()"
        >
          Reload
        </button>
        <button
          class="px-3 py-1.5 text-xs rounded-md bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/40 hover:border-violet-500/60 text-violet-400 hover:text-violet-300 transition-all disabled:opacity-40"
          :disabled="store.configLoading || store.configSaving"
          @click="store.saveConfig()"
        >
          {{ store.configSaving ? "Saving..." : "Save Config" }}
        </button>
      </div>
    </div>

    <p class="text-xs text-slate-400 font-mono">{{ store.configStatus || "Ready" }}</p>

    <!-- Agents Section -->
    <section class="space-y-3 min-w-0">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <h4 class="text-sm font-semibold text-slate-200">Agents</h4>
        <div class="flex flex-col sm:flex-row gap-2">
          <input
            v-model="newAgentName"
            type="text"
            placeholder="new-agent-name"
            class="w-full sm:w-48 px-2 py-1.5 text-xs bg-slate-800 border border-slate-700 rounded-md text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all font-mono"
          />
          <button
            class="px-3 py-1.5 text-xs rounded-md bg-slate-700 hover:bg-slate-600 text-slate-200 transition-all"
            @click="addAgent"
          >Add</button>
        </div>
      </div>
      <div v-if="agentEntries.length" class="space-y-2">
        <div
          v-for="[name, agent] in agentEntries"
          :key="name"
          class="rounded-lg border border-slate-700/60 bg-slate-800/40 p-3 space-y-3 min-w-0"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium text-slate-200 break-all font-mono">{{ name }}</span>
            <button class="text-xs text-red-400 hover:text-red-300 transition-colors" @click="removeAgent(name)">Remove</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs min-w-0">
            <label class="space-y-1 min-w-0">
              <span class="text-slate-400">Type</span>
              <select v-model="agent.type" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all">
                <option v-for="option in optionsWithCurrent(agentTypeOptions, agent.type)" :key="option" :value="option" class="bg-slate-800">
                  {{ option }}
                </option>
              </select>
            </label>
            <label class="space-y-1 min-w-0">
              <span class="text-slate-400">Role</span>
              <select v-model="agent.role" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all">
                <option value="" class="bg-slate-800">(none)</option>
                <option v-for="option in optionsWithCurrent(agentRoleOptions, agent.role)" :key="option" :value="option" class="bg-slate-800">
                  {{ option }}
                </option>
              </select>
            </label>
            <label class="space-y-1 min-w-0">
              <span class="text-slate-400">Command</span>
              <input v-model="agent.command" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all" />
            </label>
            <label class="space-y-1 min-w-0">
              <span class="text-slate-400">Model</span>
              <input v-model="agent.model" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all" />
            </label>
            <label class="space-y-1 min-w-0">
              <span class="text-slate-400">Endpoint</span>
              <input v-model="agent.endpoint" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all" />
            </label>
            <label class="space-y-1 min-w-0">
              <span class="text-slate-400">Timeout (sec)</span>
              <input v-model.number="agent.timeout" type="number" min="1" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all" />
            </label>
            <label class="space-y-1 md:col-span-2 min-w-0">
              <span class="text-slate-400">Description</span>
              <input v-model="agent.description" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all" />
            </label>
            <label class="space-y-1 md:col-span-2 min-w-0">
              <span class="text-slate-400">Capabilities (comma separated)</span>
              <input
                :value="toCsv(agent.capabilities)"
                class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all font-mono"
                @input="agent.capabilities = parseCsv($event.target.value)"
              />
            </label>
          </div>
          <div class="flex flex-wrap gap-4 text-xs">
            <label class="inline-flex items-center gap-2 cursor-pointer">
              <input v-model="agent.enabled" type="checkbox" class="rounded border-slate-600 bg-slate-700 text-violet-500 focus:ring-violet-500/40" />
              <span class="text-slate-400">Enabled</span>
            </label>
            <label class="inline-flex items-center gap-2 cursor-pointer">
              <input v-model="agent.offline" type="checkbox" class="rounded border-slate-600 bg-slate-700 text-violet-500 focus:ring-violet-500/40" />
              <span class="text-slate-400">Offline</span>
            </label>
          </div>
        </div>
      </div>
      <p v-else class="text-xs text-slate-500 italic">No agents configured.</p>
    </section>

    <!-- Workflows Section -->
    <section class="space-y-3 min-w-0 pt-4 border-t border-slate-700/60">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <h4 class="text-sm font-semibold text-slate-200">Workflows</h4>
        <div class="flex flex-col sm:flex-row gap-2">
          <input
            v-model="newWorkflowName"
            type="text"
            placeholder="new-workflow"
            class="w-full sm:w-48 px-2 py-1.5 text-xs bg-slate-800 border border-slate-700 rounded-md text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all font-mono"
          />
          <button class="px-3 py-1.5 text-xs rounded-md bg-slate-700 hover:bg-slate-600 text-slate-200 transition-all" @click="addWorkflow">Add</button>
        </div>
      </div>
      <div v-if="workflowEntries.length" class="space-y-2">
        <div
          v-for="[name, workflow] in workflowEntries"
          :key="name"
          class="rounded-lg border border-slate-700/60 bg-slate-800/40 p-3 space-y-3 min-w-0"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium text-slate-200 break-all font-mono">{{ name }}</span>
            <button class="text-xs text-red-400 hover:text-red-300 transition-colors" @click="removeWorkflow(name)">Remove</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs min-w-0">
            <label class="space-y-1 md:col-span-2 min-w-0">
              <span class="text-slate-400">Description</span>
              <input v-model="workflow.description" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all" />
            </label>
            <label class="inline-flex items-center gap-2 cursor-pointer">
              <input v-model="workflow.offline" type="checkbox" class="rounded border-slate-600 bg-slate-700 text-violet-500 focus:ring-violet-500/40" />
              <span class="text-slate-400">Offline Workflow</span>
            </label>
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-medium text-slate-300">Steps</span>
              <button class="text-xs px-2 py-1 rounded-md border border-slate-600 text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-all" @click="addWorkflowStep(name)">+ Step</button>
            </div>
            <div
              v-for="(step, idx) in workflow.steps"
              :key="`${name}-${idx}`"
              class="rounded-md border border-slate-700/40 bg-slate-800/60 p-2 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs min-w-0"
            >
              <label class="space-y-1 min-w-0">
                <span class="text-slate-500">Agent</span>
                <select v-model="step.agent" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all">
                  <option value="" class="bg-slate-800">(none)</option>
                  <option v-for="option in optionsWithCurrent(availableAgentNameOptions, step.agent)" :key="option" :value="option" class="bg-slate-800">
                    {{ option }}
                  </option>
                </select>
              </label>
              <label class="space-y-1 min-w-0">
                <span class="text-slate-500">Task</span>
                <select v-model="step.task" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all">
                  <option value="" class="bg-slate-800">(none)</option>
                  <option v-for="option in optionsWithCurrent(workflowTaskOptions, step.task)" :key="option" :value="option" class="bg-slate-800">
                    {{ option }}
                  </option>
                </select>
              </label>
              <label class="space-y-1 min-w-0">
                <span class="text-slate-500">Role</span>
                <select v-model="step.role" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all">
                  <option value="" class="bg-slate-800">(none)</option>
                  <option v-for="option in optionsWithCurrent(workflowRoleOptions, step.role)" :key="option" :value="option" class="bg-slate-800">
                    {{ option }}
                  </option>
                </select>
              </label>
              <label class="space-y-1 min-w-0">
                <span class="text-slate-500">Fallback</span>
                <select v-model="step.fallback" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all">
                  <option value="" class="bg-slate-800">(none)</option>
                  <option v-for="option in optionsWithCurrent(availableAgentNameOptions, step.fallback)" :key="option" :value="option" class="bg-slate-800">
                    {{ option }}
                  </option>
                </select>
              </label>
              <label class="space-y-1 md:col-span-2 min-w-0">
                <span class="text-slate-500">Description</span>
                <input v-model="step.description" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
              </label>
              <div class="md:col-span-2">
                <button class="text-xs text-red-400 hover:text-red-300 transition-colors" @click="removeWorkflowStep(name, idx)">Remove Step</button>
              </div>
            </div>
            <p v-if="!workflow.steps.length" class="text-xs text-slate-500 italic">No steps yet.</p>
          </div>
        </div>
      </div>
      <p v-else class="text-xs text-slate-500 italic">No workflows configured.</p>
    </section>

    <!-- Settings Section -->
    <section class="space-y-3 min-w-0 pt-4 border-t border-slate-700/60">
      <h4 class="text-sm font-semibold text-slate-200">Settings</h4>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs min-w-0">
        <label class="space-y-1 min-w-0">
          <span class="text-slate-400">Max Iterations</span>
          <input v-model.number="settings.max_iterations" type="number" min="1" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
        </label>
        <label class="space-y-1 min-w-0">
          <span class="text-slate-400">Log Level</span>
          <select v-model="settings.log_level" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all">
            <option v-for="option in optionsWithCurrent(logLevelOptions, settings.log_level)" :key="option" :value="option" class="bg-slate-800">
              {{ option }}
            </option>
          </select>
        </label>
        <label class="space-y-1 min-w-0">
          <span class="text-slate-400">Output Dir</span>
          <input v-model="settings.output_dir" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
        </label>
        <label class="space-y-1 min-w-0">
          <span class="text-slate-400">Workspace Dir</span>
          <input v-model="settings.workspace_dir" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
        </label>
        <label class="space-y-1 min-w-0">
          <span class="text-slate-400">Reports Dir</span>
          <input v-model="settings.reports_dir" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
        </label>
        <label class="space-y-1 min-w-0">
          <span class="text-slate-400">Min Suggestions Threshold</span>
          <input v-model.number="settings.min_suggestions_threshold" type="number" min="0" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
        </label>
        <label class="space-y-1 md:col-span-2 min-w-0">
          <span class="text-slate-400">Log File</span>
          <input v-model="settings.log_file" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
        </label>
      </div>
      <div class="flex flex-wrap gap-4 text-xs">
        <label class="inline-flex items-center gap-2 cursor-pointer">
          <input v-model="settings.create_reports" type="checkbox" class="rounded border-slate-600 bg-slate-700 text-violet-500" />
          <span class="text-slate-400">Create Reports</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer">
          <input v-model="settings.colored_output" type="checkbox" class="rounded border-slate-600 bg-slate-700 text-violet-500" />
          <span class="text-slate-400">Colored Output</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer">
          <input v-model="settings.offline.enabled" type="checkbox" class="rounded border-slate-600 bg-slate-700 text-violet-500" />
          <span class="text-slate-400">Offline Enabled</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer">
          <input v-model="settings.offline.auto_detect" type="checkbox" class="rounded border-slate-600 bg-slate-700 text-violet-500" />
          <span class="text-slate-400">Offline Auto Detect</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer">
          <input v-model="settings.fallback.enabled" type="checkbox" class="rounded border-slate-600 bg-slate-700 text-violet-500" />
          <span class="text-slate-400">Fallback Enabled</span>
        </label>
      </div>
      <div class="space-y-2 min-w-0">
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-medium text-slate-300">Fallback Map</span>
          <button class="text-xs px-2 py-1 rounded-md border border-slate-600 text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-all" @click="addFallbackMapEntry">+ Entry</button>
        </div>
        <div
          v-for="(entry, idx) in fallbackMapEntries"
          :key="`fb-${idx}`"
          class="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-2"
        >
          <input
            :value="entry.key"
            class="w-full px-2 py-1.5 text-xs bg-slate-800 border border-slate-700 rounded-md text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all"
            placeholder="source-agent"
            @input="updateFallbackMapKey(entry.key, $event.target.value)"
          />
          <input
            :value="entry.value"
            class="w-full px-2 py-1.5 text-xs bg-slate-800 border border-slate-700 rounded-md text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all"
            placeholder="target-agent"
            @input="updateFallbackMapValue(entry.key, $event.target.value)"
          />
          <button class="text-xs text-red-400 hover:text-red-300 text-left sm:text-center transition-colors" @click="removeFallbackMapEntry(entry.key)">Remove</button>
        </div>
        <p v-if="!fallbackMapEntries.length" class="text-xs text-slate-500 italic">No fallback mappings configured.</p>
      </div>
    </section>

    <!-- Agentic Team Section -->
    <section class="space-y-3 min-w-0 pt-4 border-t border-slate-700/60">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <h4 class="text-sm font-semibold text-slate-200">Agentic Team</h4>
        <div class="flex flex-col sm:flex-row gap-2">
          <input
            v-model="newTeamRoleName"
            type="text"
            placeholder="new_role"
            class="w-full sm:w-48 px-2 py-1.5 text-xs bg-slate-800 border border-slate-700 rounded-md text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all"
          />
          <button class="px-3 py-1.5 text-xs rounded-md bg-slate-700 hover:bg-slate-600 text-slate-200 transition-all" @click="addTeamRole">Add</button>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs min-w-0">
        <label class="space-y-1 min-w-0">
          <span class="text-slate-400">Lead Role</span>
          <select v-model="teamConfig.lead_role" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all">
            <option value="" class="bg-slate-800">(none)</option>
            <option v-for="option in optionsWithCurrent(teamRoleNameOptions, teamConfig.lead_role)" :key="option" :value="option" class="bg-slate-800">
              {{ option }}
            </option>
          </select>
        </label>
        <label class="space-y-1 min-w-0">
          <span class="text-slate-400">Max Turns</span>
          <input v-model.number="teamConfig.max_turns" type="number" min="1" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
        </label>
      </div>
      <div v-if="teamRoleEntries.length" class="space-y-2">
        <div
          v-for="[role, spec] in teamRoleEntries"
          :key="role"
          class="rounded-lg border border-slate-700/60 bg-slate-800/40 p-3 space-y-2 min-w-0"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium text-slate-200 break-all font-mono">{{ role }}</span>
            <button class="text-xs text-red-400 hover:text-red-300 transition-colors" @click="removeTeamRole(role)">Remove</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs min-w-0">
            <label class="space-y-1 min-w-0">
              <span class="text-slate-400">Title</span>
              <input v-model="spec.title" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
            </label>
            <label class="space-y-1 min-w-0">
              <span class="text-slate-400">Agent</span>
              <select v-model="spec.agent" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all">
                <option value="" class="bg-slate-800">(none)</option>
                <option v-for="option in optionsWithCurrent(availableAgentNameOptions, spec.agent)" :key="option" :value="option" class="bg-slate-800">
                  {{ option }}
                </option>
              </select>
            </label>
            <label class="space-y-1 md:col-span-2 min-w-0">
              <span class="text-slate-400">Responsibilities</span>
              <input v-model="spec.responsibilities" class="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500/40 transition-all" />
            </label>
          </div>
        </div>
      </div>
      <p v-else class="text-xs text-slate-500 italic">No team roles configured.</p>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useOrchestratorStore } from "../stores/orchestrator";

const store = useOrchestratorStore();
const newAgentName = ref("");
const newWorkflowName = ref("");
const newTeamRoleName = ref("");

const agentTypeOptions = ["cli", "ollama", "llamacpp", "localai", "text-generation-webui", "openai-compatible"];
const agentRoleOptions = ["implementation", "review", "refinement", "suggestions", "docs", "qa", "devops"];
const workflowTaskOptions = ["implement", "review", "refine", "document", "suggestions", "test"];
const workflowRoleOptions = ["implementer", "reviewer", "refiner", "writer", "tester"];
const logLevelOptions = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

const normalizeKey = (value) =>
  String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

const toCsv = (value) => (Array.isArray(value) ? value.join(", ") : "");
const parseCsv = (value) =>
  String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

const optionsWithCurrent = (options, current) => {
  const normalizedCurrent = String(current || "").trim();
  const merged = [...options];
  if (normalizedCurrent && !merged.includes(normalizedCurrent)) {
    merged.push(normalizedCurrent);
  }
  return merged;
};

const ensureConfigShape = () => {
  if (!store.configData || typeof store.configData !== "object") {
    store.configData = {};
  }
  if (!store.configData.agents || typeof store.configData.agents !== "object") {
    store.configData.agents = {};
  }
  if (!store.configData.workflows || typeof store.configData.workflows !== "object") {
    store.configData.workflows = {};
  }
  if (!store.configData.settings || typeof store.configData.settings !== "object") {
    store.configData.settings = {};
  }
  if (!store.configData.agentic_team || typeof store.configData.agentic_team !== "object") {
    store.configData.agentic_team = {};
  }
  if (!store.configData.agentic_team.roles || typeof store.configData.agentic_team.roles !== "object") {
    store.configData.agentic_team.roles = {};
  }
  if (!store.configData.settings.offline || typeof store.configData.settings.offline !== "object") {
    store.configData.settings.offline = {};
  }
  if (!store.configData.settings.fallback || typeof store.configData.settings.fallback !== "object") {
    store.configData.settings.fallback = {};
  }
  if (!store.configData.settings.fallback.map || typeof store.configData.settings.fallback.map !== "object") {
    store.configData.settings.fallback.map = {};
  }

  Object.entries(store.configData.workflows).forEach(([name, workflow]) => {
    if (Array.isArray(workflow)) {
      store.configData.workflows[name] = {
        description: "",
        offline: false,
        steps: workflow,
      };
      return;
    }
    if (!workflow || typeof workflow !== "object") {
      store.configData.workflows[name] = { description: "", offline: false, steps: [] };
      return;
    }
    if (!Array.isArray(workflow.steps)) {
      workflow.steps = [];
    }
  });
};

ensureConfigShape();

const agentEntries = computed(() => {
  ensureConfigShape();
  return Object.entries(store.configData.agents).sort((a, b) => a[0].localeCompare(b[0]));
});

const workflowEntries = computed(() => {
  ensureConfigShape();
  return Object.entries(store.configData.workflows).sort((a, b) => a[0].localeCompare(b[0]));
});

const settings = computed(() => {
  ensureConfigShape();
  return store.configData.settings;
});

const teamConfig = computed(() => {
  ensureConfigShape();
  return store.configData.agentic_team;
});

const teamRoleEntries = computed(() => {
  ensureConfigShape();
  return Object.entries(store.configData.agentic_team.roles).sort((a, b) => a[0].localeCompare(b[0]));
});

const fallbackMapEntries = computed(() => {
  ensureConfigShape();
  return Object.entries(settings.value.fallback.map).map(([key, value]) => ({ key, value }));
});

const agentNameOptions = computed(() => agentEntries.value.map(([name]) => name));
const availableAgentNameOptions = computed(() => {
  const availableFromAgents = (store.agents || [])
    .filter((item) => item?.available)
    .map((item) => item.name)
    .filter(Boolean);
  const availableFromLocal = (store.localModelStatus?.agents || [])
    .filter((item) => item?.available_for_execution)
    .map((item) => item.name)
    .filter(Boolean);
  const merged = new Set([...availableFromAgents, ...availableFromLocal, ...agentNameOptions.value]);
  return Array.from(merged).sort((a, b) => a.localeCompare(b));
});
const teamRoleNameOptions = computed(() => teamRoleEntries.value.map(([role]) => role));

const addAgent = () => {
  ensureConfigShape();
  const key = normalizeKey(newAgentName.value);
  if (!key || store.configData.agents[key]) return;
  store.configData.agents[key] = {
    type: "cli",
    enabled: true,
    command: key,
    role: "implementation",
    timeout: 3600,
    description: "",
  };
  newAgentName.value = "";
};

const removeAgent = (name) => {
  ensureConfigShape();
  delete store.configData.agents[name];
};

const addWorkflow = () => {
  ensureConfigShape();
  const key = normalizeKey(newWorkflowName.value);
  if (!key || store.configData.workflows[key]) return;
  store.configData.workflows[key] = { description: "", offline: false, steps: [] };
  newWorkflowName.value = "";
};

const removeWorkflow = (name) => {
  ensureConfigShape();
  delete store.configData.workflows[name];
};

const addWorkflowStep = (name) => {
  ensureConfigShape();
  const workflow = store.configData.workflows[name];
  if (!workflow || !Array.isArray(workflow.steps)) return;
  workflow.steps.push({ agent: "", task: "implement", role: "", description: "" });
};

const removeWorkflowStep = (name, index) => {
  ensureConfigShape();
  const workflow = store.configData.workflows[name];
  if (!workflow || !Array.isArray(workflow.steps)) return;
  workflow.steps.splice(index, 1);
};

const addFallbackMapEntry = () => {
  ensureConfigShape();
  let idx = 1;
  let key = `source-agent-${idx}`;
  while (Object.prototype.hasOwnProperty.call(settings.value.fallback.map, key)) {
    idx += 1;
    key = `source-agent-${idx}`;
  }
  settings.value.fallback.map[key] = "";
};

const updateFallbackMapKey = (oldKey, newKeyRaw) => {
  ensureConfigShape();
  const newKey = normalizeKey(newKeyRaw);
  if (!newKey || newKey === oldKey) return;
  if (Object.prototype.hasOwnProperty.call(settings.value.fallback.map, newKey)) return;
  const value = settings.value.fallback.map[oldKey];
  delete settings.value.fallback.map[oldKey];
  settings.value.fallback.map[newKey] = value;
};

const updateFallbackMapValue = (key, value) => {
  ensureConfigShape();
  settings.value.fallback.map[key] = value;
};

const removeFallbackMapEntry = (key) => {
  ensureConfigShape();
  delete settings.value.fallback.map[key];
};

const addTeamRole = () => {
  ensureConfigShape();
  const key = normalizeKey(newTeamRoleName.value);
  if (!key || store.configData.agentic_team.roles[key]) return;
  store.configData.agentic_team.roles[key] = {
    title: "",
    agent: "",
    responsibilities: "",
  };
  newTeamRoleName.value = "";
};

const removeTeamRole = (name) => {
  ensureConfigShape();
  delete store.configData.agentic_team.roles[name];
};
</script>
