<template>
  <div class="flex flex-col h-full bg-slate-950 rounded-xl border border-slate-700/60 overflow-hidden">
    <!-- Graph Header -->
    <div class="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-700/60 flex-shrink-0">
      <div class="flex items-center gap-2">
        <svg class="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <h3 class="text-sm font-semibold text-slate-200">Team Communication Graph</h3>
        <span v-if="totalMessages > 0" class="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
          {{ totalMessages }} messages
        </span>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="resetZoom"
          class="text-xs px-2.5 py-1 rounded-md border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-all"
        >
          Reset
        </button>
        <span v-if="store.isRunning" class="flex items-center gap-1.5 text-xs text-amber-400">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
          Live
        </span>
      </div>
    </div>

    <!-- Graph Canvas -->
    <div ref="graphContainer" class="flex-1 relative min-h-0 overflow-hidden">
      <svg ref="svgEl" class="w-full h-full" style="min-height: 300px;">
        <defs>
          <!-- Arrow marker -->
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#475569" />
          </marker>
          <marker
            id="arrowhead-active"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#22d3ee" />
          </marker>
          <marker
            id="arrowhead-default"
            markerWidth="8"
            markerHeight="6"
            refX="7"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="#1e3a5f" opacity="0.6" />
          </marker>
          <!-- Glow filter -->
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <filter id="glow-strong">
            <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <g ref="graphGroup">
          <!-- Links -->
          <g ref="linksGroup"></g>
          <!-- Link labels -->
          <g ref="linkLabelsGroup"></g>
          <!-- Nodes -->
          <g ref="nodesGroup"></g>
        </g>
      </svg>

      <!-- Empty state - only show if somehow no nodes -->
      <div v-if="nodes.length === 0" class="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
        <div class="w-16 h-16 rounded-full bg-slate-800/60 border border-slate-700/40 flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        </div>
        <p class="text-sm text-slate-500 font-medium">No team activity yet</p>
        <p class="text-xs text-slate-600 mt-1">Run a task to see agent communication</p>
      </div>

      <!-- Tooltip -->
      <div
        v-if="tooltip.visible"
        class="absolute pointer-events-none z-10 max-w-xs"
        :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px', transform: 'translate(-50%, -110%)' }"
      >
        <div class="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2.5 shadow-xl shadow-black/50 text-xs">
          <div class="font-semibold text-slate-100 mb-1">{{ tooltip.title }}</div>
          <div v-if="tooltip.subtitle" class="text-slate-400">{{ tooltip.subtitle }}</div>
          <div v-if="tooltip.detail" class="text-slate-400 mt-1">{{ tooltip.detail }}</div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="px-4 py-3 bg-slate-900/60 border-t border-slate-700/60 flex-shrink-0">
      <div class="flex flex-wrap gap-x-5 gap-y-2">
        <div v-for="role in ROLE_DEFS" :key="role.id" class="flex items-center gap-1.5">
          <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" :style="{ backgroundColor: role.color }"></span>
          <span class="text-xs text-slate-400">{{ role.label }}</span>
        </div>
      </div>
      <p class="text-xs text-slate-600 mt-2">
        <span class="text-slate-500">Dashed lines</span> = potential paths ·
        <span class="text-slate-500">Solid lines</span> = active communication ·
        Drag nodes to rearrange
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'
import { useOrchestratorStore } from '../stores/orchestrator'

const store = useOrchestratorStore()

// Role definitions with colors
const ROLE_DEFS = [
  { id: 'project_manager', label: 'Project Manager', color: '#f59e0b' },
  { id: 'architect',       label: 'Architect',       color: '#8b5cf6' },
  { id: 'developer',       label: 'Developer',       color: '#3b82f6' },
  { id: 'qa',              label: 'QA Engineer',     color: '#10b981' },
  { id: 'devops',          label: 'DevOps',          color: '#f43f5e' },
  { id: 'unknown',         label: 'Other',           color: '#64748b' },
]

const ROLE_COLOR_MAP = Object.fromEntries(ROLE_DEFS.map(r => [r.id, r.color]))

const getRoleColor = (roleId) => {
  const normalized = (roleId || '').toLowerCase().replace(/[\s-]/g, '_')
  if (ROLE_COLOR_MAP[normalized]) return ROLE_COLOR_MAP[normalized]
  // Partial match
  for (const [key, color] of Object.entries(ROLE_COLOR_MAP)) {
    if (normalized.includes(key) || key.includes(normalized)) return color
  }
  return ROLE_COLOR_MAP.unknown
}

// Refs
const graphContainer = ref(null)
const svgEl = ref(null)
const graphGroup = ref(null)
const linksGroup = ref(null)
const linkLabelsGroup = ref(null)
const nodesGroup = ref(null)

const tooltip = ref({ visible: false, x: 0, y: 0, title: '', subtitle: '', detail: '' })

let simulation = null
let zoomBehavior = null

// Default team workflow edges - ONE edge per pair, bidirectional label
const DEFAULT_WORKFLOW_EDGES = [
  { source: 'project_manager', target: 'architect', label: 'PM ↔ Arch' },
  { source: 'architect', target: 'developer', label: 'Arch ↔ Dev' },
  { source: 'developer', target: 'qa', label: 'Dev ↔ QA' },
  { source: 'qa', target: 'devops', label: 'QA ↔ Ops' },
  { source: 'devops', target: 'project_manager', label: 'Ops ↔ PM' },
  { source: 'project_manager', target: 'developer', label: 'PM → Dev' },
]

// Extract nodes and edges from store data (team_turns or iterations)
const graphData = computed(() => {
  try {
    const teamTurns = store.team_turns || []
    const iterations = store.iterations || []

    // Build message map from team_turns if available
    const messageCount = {}
    const roleSet = new Set()

    if (teamTurns.length > 0) {
      for (const turn of teamTurns) {
        if (!turn || typeof turn !== 'object') continue

        const from = String(turn.from_role || turn.role || 'unknown').toLowerCase().replace(/[\s-]/g, '_')
        const to = String(turn.to_role || turn.target_role || 'unknown').toLowerCase().replace(/[\s-]/g, '_')

        if (from && from !== 'null') roleSet.add(from)
        if (to && to !== 'unknown' && to !== 'null') roleSet.add(to)

        if (from !== to && from !== 'null' && to !== 'null') {
          const key = `${from}--${to}`
          messageCount[key] = (messageCount[key] || 0) + 1
        }
      }
    } else if (iterations.length > 0) {
      // Fall back to iterations data
      for (const iter of iterations) {
        if (!iter || typeof iter !== 'object') continue
        const steps = iter.steps || []

        for (let i = 0; i < steps.length; i++) {
          const step = steps[i]
          if (!step || typeof step !== 'object') continue

          const from = String(step.agent || step.role || 'unknown').toLowerCase().replace(/[\s-]/g, '_')
          const to = i + 1 < steps.length
            ? String(steps[i + 1].agent || steps[i + 1].role || 'unknown').toLowerCase().replace(/[\s-]/g, '_')
            : null

          if (from && from !== 'null') roleSet.add(from)
          if (to && to !== 'null') {
            roleSet.add(to)
            const key = `${from}--${to}`
            messageCount[key] = (messageCount[key] || 0) + 1
          }
        }
      }
    }

    // Also seed from agents list if no activity yet
    if (roleSet.size === 0 && store.agents && store.agents.length > 0) {
      for (const agent of store.agents) {
        if (!agent || typeof agent !== 'object') continue
        const role = String(agent.role || agent.name || 'unknown').toLowerCase().replace(/[\s-]/g, '_')
        if (role && role !== 'null') roleSet.add(role)
      }
    }

  // Always include the standard 5 roles as seed
  const standardRoles = ['project_manager', 'architect', 'developer', 'qa', 'devops']
  for (const r of standardRoles) roleSet.add(r)

  const nodeList = Array.from(roleSet).map(id => ({
    id,
    label: ROLE_DEFS.find(r => r.id === id)?.label || id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    color: getRoleColor(id),
    messagesSent: Object.entries(messageCount)
      .filter(([k]) => k.startsWith(id + '--'))
      .reduce((s, [, v]) => s + v, 0),
  }))

  // Build edge list - merge bidirectional edges into single edges
  const hasRealMessages = Object.keys(messageCount).length > 0
  const edgeList = []

  if (hasRealMessages) {
    // Merge bidirectional edges
    const processedPairs = new Set()
    for (const [key, count] of Object.entries(messageCount)) {
      const [source, target] = key.split('--')
      const pairKey = [source, target].sort().join('|')

      if (processedPairs.has(pairKey)) continue
      processedPairs.add(pairKey)

      const reverseKey = `${target}--${source}`
      const reverseCount = messageCount[reverseKey] || 0

      if (reverseCount > 0) {
        // Bidirectional edge - show combined label
        edgeList.push({
          source,
          target,
          count,
          reverseCount,
          isDefault: false,
          label: `${count} ↔ ${reverseCount}`
        })
      } else {
        // Unidirectional edge - show count only
        edgeList.push({ source, target, count, isDefault: false })
      }
    }
  } else {
    // Show default workflow edges as "potential" connections
    for (const edge of DEFAULT_WORKFLOW_EDGES) {
      edgeList.push({
        source: edge.source,
        target: edge.target,
        count: 0,
        isDefault: true,
        label: edge.label
      })
    }
  }

  return { nodes: nodeList, edges: edgeList }
  } catch (error) {
    console.error('Graph data processing error:', error)
    // Return fallback with standard agents on error
    const standardRoles = ['project_manager', 'architect', 'developer', 'qa', 'devops']
    const fallbackNodes = standardRoles.map(id => ({
      id,
      label: ROLE_DEFS.find(r => r.id === id)?.label || id,
      color: getRoleColor(id),
      messagesSent: 0,
    }))
    return { nodes: fallbackNodes, edges: [] }
  }
})

const nodes = computed(() => graphData.value.nodes)
const edges = computed(() => graphData.value.edges)

const totalMessages = computed(() =>
  edges.value.reduce((s, e) => s + e.count, 0)
)

const resetZoom = () => {
  if (svgEl.value && zoomBehavior) {
    d3.select(svgEl.value)
      .transition()
      .duration(500)
      .call(zoomBehavior.transform, d3.zoomIdentity)
  }
}

let animationFrameId = null

const buildGraph = () => {
  try {
    if (!svgEl.value || !graphContainer.value) return

    const { nodes: nodeData, edges: edgeData } = graphData.value
    if (!nodeData || !edgeData) return

    const svg = d3.select(svgEl.value)
    const width = graphContainer.value.clientWidth || 600
    const height = graphContainer.value.clientHeight || 450

  svg.attr('viewBox', `0 0 ${width} ${height}`)

  const g = d3.select(graphGroup.value)
  const linksG = d3.select(linksGroup.value)
  const linkLabelsG = d3.select(linkLabelsGroup.value)
  const nodesG = d3.select(nodesGroup.value)

  // Zoom
  zoomBehavior = d3.zoom()
    .scaleExtent([0.3, 3])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })
  svg.call(zoomBehavior).on('dblclick.zoom', null)

  // Stop old simulation
  if (simulation) simulation.stop()

  // Clone data for simulation (d3 mutates nodes)
  const simNodes = nodeData.map(d => ({ ...d }))
  const nodeById = Object.fromEntries(simNodes.map(n => [n.id, n]))

  const simEdges = edgeData.map(d => ({
    ...d,
    source: nodeById[d.source] || d.source,
    target: nodeById[d.target] || d.target,
  })).filter(e => e.source && e.target && typeof e.source === 'object' && typeof e.target === 'object')

  const maxCount = Math.max(...edgeData.map(e => e.count), 1)

  simulation = d3.forceSimulation(simNodes)
    .force('link', d3.forceLink(simEdges).id(d => d.id).distance(130).strength(0.6))
    .force('charge', d3.forceManyBody().strength(-280))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide(50))

  // Links - straight lines
  linksG.selectAll('*').remove()
  const link = linksG.selectAll('line')
    .data(simEdges)
    .join('line')
    .attr('stroke', d => d.isDefault ? '#1e3a5f' : '#334155')
    .attr('stroke-opacity', d => d.isDefault ? 0.5 : 0.7)
    .attr('stroke-width', d => d.isDefault ? 1 : Math.max(1.5, (d.count / maxCount) * 6))
    .attr('stroke-dasharray', d => d.isDefault ? '4,4' : 'none')
    .attr('marker-end', d => d.isDefault ? 'url(#arrowhead-default)' : 'url(#arrowhead)')

  // Link labels (message count or workflow label for defaults)
  linkLabelsG.selectAll('*').remove()
  const linkLabel = linkLabelsG.selectAll('text')
    .data(simEdges)
    .join('text')
    .attr('text-anchor', 'middle')
    .attr('fill', d => d.isDefault ? '#3b5a7d' : '#64748b')
    .attr('font-size', d => d.isDefault ? '8px' : '9px')
    .attr('font-family', 'system-ui, sans-serif')
    .attr('font-style', d => d.isDefault ? 'italic' : 'normal')
    .text(d => {
      if (d.label) return d.label  // Custom label (default workflow or bidirectional)
      if (d.count > 0) return `${d.count}`  // Unidirectional count
      return ''
    })

  // Nodes
  nodesG.selectAll('*').remove()
  const node = nodesG.selectAll('g')
    .data(simNodes)
    .join('g')
    .attr('cursor', 'grab')
    .call(d3.drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null
        d.fy = null
      })
    )

  // Node outer ring (glow)
  node.append('circle')
    .attr('r', 26)
    .attr('fill', 'none')
    .attr('stroke', d => d.color)
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.3)
    .attr('filter', 'url(#glow)')

  // Node circle
  node.append('circle')
    .attr('r', 20)
    .attr('fill', d => d.color + '22')
    .attr('stroke', d => d.color)
    .attr('stroke-width', 2)

  // Node label (abbreviated)
  node.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('fill', d => d.color)
    .attr('font-size', '10px')
    .attr('font-weight', '700')
    .attr('font-family', 'monospace')
    .text(d => d.id.split('_').map(w => w[0].toUpperCase()).join(''))

  // Role label below node
  node.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '38px')
    .attr('fill', '#94a3b8')
    .attr('font-size', '9px')
    .attr('font-family', 'system-ui, sans-serif')
    .text(d => d.label)

  // Tooltip interactions
  node
    .on('mouseenter', (event, d) => {
      const rect = graphContainer.value.getBoundingClientRect()
      tooltip.value = {
        visible: true,
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
        title: d.label,
        subtitle: `Role: ${d.id.replace(/_/g, ' ')}`,
        detail: d.messagesSent > 0 ? `Sent ${d.messagesSent} message${d.messagesSent !== 1 ? 's' : ''}` : 'No messages yet',
      }
      d3.select(event.currentTarget).select('circle:last-of-type')
        .transition().duration(150)
        .attr('r', 24)
        .attr('stroke-width', 3)
    })
    .on('mouseleave', (event) => {
      tooltip.value.visible = false
      d3.select(event.currentTarget).select('circle:last-of-type')
        .transition().duration(150)
        .attr('r', 20)
        .attr('stroke-width', 2)
    })

  // Tick
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => {
        const dx = d.target.x - d.source.x
        const dy = d.target.y - d.source.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        return d.target.x - (dx / dist) * 26
      })
      .attr('y2', d => {
        const dx = d.target.x - d.source.x
        const dy = d.target.y - d.source.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        return d.target.y - (dy / dist) * 26
      })

    linkLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2 - 6)

    node.attr('transform', d => `translate(${d.x},${d.y})`)
  })

  // Animate active edges on running
  const animateEdges = () => {
    if (!store.isRunning) return
    link
      .filter(d => d.count > 0)
      .transition()
      .duration(800)
      .attr('stroke', '#22d3ee')
      .attr('stroke-opacity', 1)
      .attr('marker-end', 'url(#arrowhead-active)')
      .transition()
      .duration(800)
      .attr('stroke', '#334155')
      .attr('stroke-opacity', 0.7)
      .attr('marker-end', 'url(#arrowhead)')
      .on('end', () => {
        if (store.isRunning) animateEdges()
      })
  }
  if (store.isRunning && simEdges.length > 0) animateEdges()
  } catch (error) {
    console.error('Graph rendering error:', error)
    // Silent fail - just don't crash the UI
  }
}

// Rebuild on data changes
watch([() => graphData.value.nodes.length, () => graphData.value.edges.length, () => store.isRunning],
  async () => {
    await nextTick()
    buildGraph()
  },
  { flush: 'post' }
)

onMounted(async () => {
  await nextTick()
  buildGraph()

  // Re-build on resize
  const ro = new ResizeObserver(() => {
    clearTimeout(animationFrameId)
    animationFrameId = setTimeout(buildGraph, 100)
  })
  if (graphContainer.value) ro.observe(graphContainer.value)

  onUnmounted(() => {
    ro.disconnect()
    if (simulation) simulation.stop()
    clearTimeout(animationFrameId)
  })
})
</script>
