---
description: Automatically format and convert any raw document, note, or text provided by the user into clean, structured, highly readable Markdown.
trigger: model_decision
---

# Document to Markdown In-Chat Formatting Rule

Whenever the user pastes, sends, attaches, or provides raw text, unformatted notes, logs, specifications, or document content in the conversation:

## 1. Automatic Markdown Transformation
- **No Raw Walls of Text**: Never echo or present unformatted, hard-to-read text blobs.
- **Instant Beautification**: Immediately parse, restructure, and present the content as clean, elegant GitHub-Flavored Markdown (GFM).

## 2. Formatting Standards
- **Hierarchical Headings**: Organize sections logically using `# Title`, `## Major Sections`, and `### Subsections`.
- **Structured Bullet Points**: Convert run-on sentences and enumerations into concise bullet points with bold lead-ins (e.g. `- **Component**: description`).
- **Data Tables**: Whenever structured data, key-value pairs, metrics, or comparisons are present, format them in Markdown tables (`| Column | Column |`).
- **Code & Command Fences**: Enclose all code snippets, paths, terminal commands, configurations, and logs in fenced blocks with syntax highlighting (` ```bash `, ` ```python `, ` ```json `).
- **Visual Callouts**: Emphasize critical requirements, takeaways, or warnings using GitHub alerts:
  - `> [!NOTE]` for contextual background.
  - `> [!IMPORTANT]` for crucial requirements.
  - `> [!TIP]` for best practices.
  - `> [!WARNING]` for caveats or risks.

## 3. Preservation of Meaning
- Preserve 100% of the original content, numbers, formulas, and critical details.
- Fix broken formatting, awkward line breaks, and formatting glitches caused by copy-pasting.
