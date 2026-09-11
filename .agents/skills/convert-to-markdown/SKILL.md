---
name: convert-to-markdown
description: Convert text and document files (.txt, .rst, .log, etc.) in a directory or sent in chat to standardized .markdown format with clean headings, YAML frontmatter, and code fences.
---

# Convert to Markdown Skill

Batch converts plain text and document files across a directory or sent directly in chat into standardized, beautifully formatted `.markdown`.

## When to Use
- **Interactive Chat Mode**: Whenever the user sends, pastes, or attaches raw text, documents, notes, or logs in chat, automatically format and present them as clean, structured Markdown.
- **Project Migration Mode**: When standardizing files into `.markdown` format for Obsidian, GitHub Wiki, or static site generators.
- **Cleanup Mode**: When converting unformatted `.txt`, `.rst`, or log files with clean YAML frontmatter, tables, and Markdown headings.

---

## 1. Interactive In-Chat Conversion

When the user pastes or shares a document in chat, apply the following structure:
1. **Title & Summary**: Add `# Document Title` and a brief executive overview.
2. **Key Concepts / Highlights**: Use bolded bullet points (`- **Point**: Details`).
3. **Structured Tables**: Convert key-value metrics and comparisons into Markdown tables.
4. **Syntax Highlighted Code**: Wrap code, terminal snippets, or logs in fenced code blocks.
5. **Alert Boxes**: Use `> [!NOTE]`, `> [!IMPORTANT]`, `> [!TIP]` for critical takeaways.

---

## 2. Batch File Conversion via CLI

### Dry run (preview files to convert without modifying disk)
```bash
python .agents/skills/convert-to-markdown/scripts/convert_to_markdown.py --dir . --dry-run
```

### Convert all text files in a directory to .markdown
```bash
python .agents/skills/convert-to-markdown/scripts/convert_to_markdown.py --dir ./docs --extension .markdown
```

### Convert with backup and frontmatter injection
```bash
python .agents/skills/convert-to-markdown/scripts/convert_to_markdown.py --dir ./notes --extension .markdown --backup --inject-frontmatter
```

## Options & Arguments for CLI Tool
- `--dir <path>`: Root directory to scan (default: current directory).
- `--extension <.markdown|.md>`: Target extension (default: `.markdown`).
- `--include-ext <exts>`: Comma-separated list of input extensions (default: `txt,text,rst,log,note`).
- `--backup`: Save a `.bak` backup copy before conversion.
- `--delete-original`: Safely remove original source file after creating `.markdown`.
- `--inject-frontmatter`: Add YAML frontmatter (`title`, `original_file`, `converted_at`, `format: markdown`).
- `--dry-run`: List files that would be converted without modifying disk.
