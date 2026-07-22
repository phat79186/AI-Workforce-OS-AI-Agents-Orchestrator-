<template>
  <div ref="editorContainer" class="code-editor h-[600px]"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { useOrchestratorStore } from '../stores/orchestrator'

const store = useOrchestratorStore()
const editorContainer = ref(null)
let editor = null

onMounted(() => {
  if (editorContainer.value) {
    editor = monaco.editor.create(editorContainer.value, {
      value: '// Select a file from the explorer to view its contents...',
      language: 'python',
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: true },
      fontSize: 13,
      lineNumbers: 'on',
      renderWhitespace: 'selection',
      scrollBeyondLastLine: false,
      readOnly: false,
      fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace',
      fontLigatures: true,
      cursorBlinking: 'smooth',
      smoothScrolling: true,
      padding: { top: 12, bottom: 12 },
    })

    editor.onDidChangeModelContent(() => {
      store.fileContent = editor.getValue()
    })
  }
})

onUnmounted(() => {
  if (editor) {
    editor.dispose()
  }
})

watch(() => store.currentFile, (newFile) => {
  if (editor && newFile) {
    editor.setValue(newFile.content)
    monaco.editor.setModelLanguage(editor.getModel(), newFile.language)
  }
})

watch(() => store.fileContent, (newContent) => {
  if (editor && newContent !== editor.getValue()) {
    editor.setValue(newContent)
  }
})
</script>

<style scoped>
.code-editor {
  border: none;
  overflow: hidden;
}
</style>
