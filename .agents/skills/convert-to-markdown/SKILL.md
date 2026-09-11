---
name: convert-to-markdown
description: Convert text and document files (.txt, .rst, .log, etc.) in a directory to standardized .markdown format with clean headings, YAML frontmatter, and code fences.
---

# Convert to Markdown Skill

Batch converts plain text and document files across a directory or project into standardized `.markdown` format.

## When to Use
- When migrating legacy documentation or plain text notes to Markdown.
- When standardizing text documents into `.markdown` format for Obsidian, GitHub Wiki, or documentation static site generators.
- When cleaning up unformatted `.txt`, `.rst`, or log files with clean YAML frontmatter and Markdown headings.

## How to Execute

### 1. Dry run (preview files to convert without modifying disk)
```bash
python .agents/skills/convert-to-markdown/scripts/convert_to_markdown.py --dir . --dry-run
```

### 2. Convert all text files in a directory to .markdown
```bash
python .agents/skills/convert-to-markdown/scripts/convert_to_markdown.py --dir ./docs --extension .markdown
```

### 3. Convert with backup and frontmatter injection
```bash
python .agents/skills/convert-to-markdown/scripts/convert_to_markdown.py --dir ./notes --extension .markdown --backup --inject-frontmatter
```

## Options & Arguments
- `--dir <path>`: Root directory to scan (default: current directory).
- `--extension <.markdown|.md>`: Target extension (default: `.markdown`).
- `--include-ext <exts>`: Comma-separated list of input extensions (default: `txt,text,rst,log,note`).
- `--backup`: Save a `.bak` backup copy before conversion.
- `--delete-original`: Safely remove original source file after creating `.markdown`.
- `--inject-frontmatter`: Add YAML frontmatter (`title`, `original_file`, `converted_at`, `format: markdown`).
- `--dry-run`: List files that would be converted without modifying disk.
