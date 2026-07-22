---
paths:
  - "orchestrator/ui/frontend/**/*"
  - "agentic_team/ui/frontend/**/*"
  - "index.html"
  - "packages/**/*"
---

# Frontend Rules

- Vue 3 with Composition API (Nuxt 3 for UI frontends)
- TailwindCSS for styling
- Pinia for state management
- Monaco Editor for code editing
- Socket.IO for real-time updates
- The two UI frontends are independent — `orchestrator/ui/` and `agentic_team/ui/`
- `index.html` + `packages/` is the landing page (vanilla HTML/CSS/JS, no framework)
- Landing page uses Inter font, dark theme, Chart.js for charts, Mermaid for diagrams
