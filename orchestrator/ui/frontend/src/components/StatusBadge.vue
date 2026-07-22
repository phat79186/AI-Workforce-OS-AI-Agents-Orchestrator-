<template>
  <span :class="['status-badge', `status-${status}`]">
    <span v-if="status === 'running'" class="badge-dot animate-pulse"></span>
    <span v-else class="badge-dot"></span>
    {{ statusText }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    required: true
  }
})

const statusText = computed(() => {
  return props.status.charAt(0).toUpperCase() + props.status.slice(1)
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  border-width: 1px;
  border-style: solid;
}

.badge-dot {
  display: inline-block;
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 9999px;
  flex-shrink: 0;
}

.status-idle {
  background-color: rgba(30, 41, 59, 0.7);
  color: #94a3b8;
  border-color: rgba(100, 116, 139, 0.3);
}
.status-idle .badge-dot {
  background-color: #475569;
}

.status-running {
  background-color: rgba(120, 53, 15, 0.3);
  color: #fcd34d;
  border-color: rgba(251, 191, 36, 0.35);
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.15);
}
.status-running .badge-dot {
  background-color: #fbbf24;
}

.status-completed {
  background-color: rgba(6, 78, 59, 0.35);
  color: #6ee7b7;
  border-color: rgba(52, 211, 153, 0.3);
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.12);
}
.status-completed .badge-dot {
  background-color: #34d399;
}

.status-error,
.status-failed {
  background-color: rgba(127, 29, 29, 0.35);
  color: #fca5a5;
  border-color: rgba(248, 113, 113, 0.3);
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.12);
}
.status-error .badge-dot,
.status-failed .badge-dot {
  background-color: #f87171;
}
</style>
