#!/usr/bin/env python3
"""Batch Text to .markdown Converter Utility for AI Workforce OS.

Scans directories for plain text / document files and converts them into
standardized .markdown format with clean headings, lists, and YAML frontmatter.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


IGNORED_DIRS = {
    ".git",
    ".github",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".obsidian",
    ".agents",
    ".claude",
    "dist",
    "build",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert plain text files (.txt, .rst, .log, etc.) to .markdown format."
    )
    parser.add_argument(
        "--dir",
        "-d",
        type=str,
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--extension",
        "-e",
        type=str,
        default=".markdown",
        help="Target markdown extension (default: .markdown)",
    )
    parser.add_argument(
        "--include-ext",
        type=str,
        default="txt,text,rst,log,note",
        help="Comma-separated file extensions to convert (default: txt,text,rst,log,note)",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a .bak backup file before converting/replacing",
    )
    parser.add_argument(
        "--delete-original",
        action="store_true",
        help="Delete original file after creating .markdown version",
    )
    parser.add_argument(
        "--inject-frontmatter",
        action="store_true",
        default=True,
        help="Inject YAML frontmatter header with metadata (default: True)",
    )
    parser.add_argument(
        "--no-frontmatter",
        action="store_false",
        dest="inject_frontmatter",
        help="Disable YAML frontmatter injection",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files that would be converted without modifying disk",
    )
    return parser.parse_args()


def read_file_safe(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Read file content attempting UTF-8 first, then fallback encodings."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            content = file_path.read_text(encoding=enc)
            return content, enc
        except (UnicodeDecodeError, PermissionError):
            continue
    return None, None


def format_to_markdown(raw_content: str, file_path: Path, inject_frontmatter: bool = True) -> str:
    """Format plain text content into clean Markdown syntax."""
    lines = raw_content.splitlines()
    formatted_lines: List[str] = []
    i = 0
    num_lines = len(lines)

    # Extract title candidate
    title_candidate = file_path.stem.replace("_", " ").replace("-", " ").title()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("="):
            title_candidate = stripped
            break

    in_code_block = False

    while i < num_lines:
        line = lines[i]
        stripped = line.strip()

        # Preserve existing code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            formatted_lines.append(line)
            i += 1
            continue

        if in_code_block:
            formatted_lines.append(line)
            i += 1
            continue

        # Convert underline headings:
        # Heading 1
        # =========
        if i + 1 < num_lines and stripped and not stripped.startswith("#"):
            next_stripped = lines[i + 1].strip()
            if next_stripped and set(next_stripped) == {"="} and len(next_stripped) >= 3:
                formatted_lines.append(f"# {stripped}")
                i += 2
                continue
            elif next_stripped and set(next_stripped) == {"-"} and len(next_stripped) >= 3:
                formatted_lines.append(f"## {stripped}")
                i += 2
                continue

        # Convert bullet points (o, •, +, *) to standard Markdown '- '
        bullet_match = re.match(r"^(\s*)(?:[•o\+\*]|\-)\s+(.*)$", line)
        if bullet_match:
            indent = bullet_match.group(1)
            text = bullet_match.group(2)
            formatted_lines.append(f"{indent}- {text}")
            i += 1
            continue

        # Keep regular line
        formatted_lines.append(line)
        i += 1

    body = "\n".join(formatted_lines).strip()

    if inject_frontmatter:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        frontmatter = (
            f"---\n"
            f"title: \"{title_candidate}\"\n"
            f"original_file: \"{file_path.name}\"\n"
            f"converted_at: \"{timestamp}\"\n"
            f"format: markdown\n"
            f"---\n\n"
        )
        return frontmatter + body + "\n"

    return body + "\n"


def convert_directory(
    root_dir: Path,
    target_ext: str = ".markdown",
    include_exts: Optional[List[str]] = None,
    backup: bool = False,
    delete_original: bool = False,
    inject_frontmatter: bool = True,
    dry_run: bool = False,
) -> dict:
    """Recursively convert files matching extensions to target markdown extension."""
    if include_exts is None:
        include_exts = ["txt", "text", "rst", "log", "note"]

    clean_include_exts = {f".{ext.strip().lstrip('.').lower()}" for ext in include_exts}
    clean_target_ext = f".{target_ext.strip().lstrip('.').lower()}"

    stats = {
        "scanned": 0,
        "converted": 0,
        "skipped": 0,
        "errors": 0,
        "files_converted": [],
    }

    if not root_dir.exists():
        print(f"Error: Directory {root_dir} does not exist.")
        return stats

    for root, dirs, files in os.walk(root_dir):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

        for filename in files:
            stats["scanned"] += 1
            file_path = Path(root) / filename
            ext = file_path.suffix.lower()

            if ext not in clean_include_exts:
                stats["skipped"] += 1
                continue

            target_file = file_path.with_suffix(clean_target_ext)

            # Avoid self-overwriting if already targeting the same extension
            if target_file == file_path:
                stats["skipped"] += 1
                continue

            stats["files_converted"].append((str(file_path), str(target_file)))

            if dry_run:
                print(f"[DRY-RUN] Would convert: {file_path} -> {target_file}")
                stats["converted"] += 1
                continue

            content, encoding = read_file_safe(file_path)
            if content is None:
                print(f"[ERROR] Could not decode file: {file_path}")
                stats["errors"] += 1
                continue

            # Format to Markdown
            markdown_content = format_to_markdown(
                content, file_path, inject_frontmatter=inject_frontmatter
            )

            # Optional Backup
            if backup:
                backup_file = file_path.with_suffix(file_path.suffix + ".bak")
                try:
                    file_path.rename(backup_file)
                    # Point file_path back to write new file or read from backup
                    target_file.write_text(markdown_content, encoding="utf-8")
                except Exception as e:
                    print(f"[ERROR] Failed backup/write for {file_path}: {e}")
                    stats["errors"] += 1
                    continue
            else:
                try:
                    target_file.write_text(markdown_content, encoding="utf-8")
                    if delete_original:
                        file_path.unlink()
                except Exception as e:
                    print(f"[ERROR] Failed writing {target_file}: {e}")
                    stats["errors"] += 1
                    continue

            print(f"[CONVERTED] {file_path} -> {target_file}")
            stats["converted"] += 1

    return stats


def main() -> None:
    args = parse_arguments()
    root_path = Path(args.dir).resolve()
    include_exts = [e.strip() for e in args.include_ext.split(",") if e.strip()]

    print("=================================================================")
    print("      CONVERT TO MARKDOWN SKILL — BATCH CONVERSION TOOL          ")
    print("=================================================================")
    print(f"Target Directory  : {root_path}")
    print(f"Target Extension  : {args.extension}")
    print(f"Source Extensions : {include_exts}")
    print(f"Frontmatter       : {'Enabled' if args.inject_frontmatter else 'Disabled'}")
    print(f"Mode              : {'DRY RUN (preview only)' if args.dry_run else 'ACTIVE (write to disk)'}")
    print("=================================================================\n")

    stats = convert_directory(
        root_dir=root_path,
        target_ext=args.extension,
        include_exts=include_exts,
        backup=args.backup,
        delete_original=args.delete_original,
        inject_frontmatter=args.inject_frontmatter,
        dry_run=args.dry_run,
    )

    print("\n-----------------------------------------------------------------")
    print(f"Files Scanned   : {stats['scanned']}")
    print(f"Files Converted : {stats['converted']}")
    print(f"Files Skipped   : {stats['skipped']}")
    print(f"Errors          : {stats['errors']}")
    print("-----------------------------------------------------------------")


if __name__ == "__main__":
    main()
