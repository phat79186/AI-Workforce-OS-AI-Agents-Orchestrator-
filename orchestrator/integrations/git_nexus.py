"""Integration named after abhigyanpatwari/GitNexus — now backed by REAL `git` operations.

`sync_multi_remotes()` and `audit_repository_health()` run genuine `git`
subprocess commands against `repo_path` (remote listing, `git ls-remote`
over the network, `git status`, `git fsck`, `git rev-list`) and compute
their results from the actual output — nothing here is hardcoded anymore.

`list_pr_issue_nexus()` is the one method that stays simulated: listing real
GitHub PRs/issues needs an authenticated GitHub API token (unauthenticated
`api.github.com` calls are rate-limited/blocked from this environment), and
no token is configured here. Wire a `GITHUB_TOKEN` and a real
`requests`/`httpx` call into that method to make it real too.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestrator.integrations._simulated import warn_simulated


class GitNexusEngine:
    """Git-backed multi-remote sync checker and repository health auditor (real git calls)."""

    def __init__(self) -> None:
        self.version = "2.0.0"
        self.source_repo = "abhigyanpatwari/GitNexus"

    def _run_git(self, repo_path: str, *args: str, timeout: int = 15) -> subprocess.CompletedProcess:
        """Run a real `git` subcommand against `repo_path` and return the completed process."""
        return subprocess.run(
            ["git", "-C", repo_path, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def _configured_remotes(self, repo_path: str) -> Dict[str, str]:
        """Return the repo's REAL configured remotes as {name: fetch_url} by parsing `git remote -v`."""
        result = self._run_git(repo_path, "remote", "-v")
        remotes: Dict[str, str] = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[2] == "(fetch)":
                remotes[parts[0]] = parts[1]
        return remotes

    def sync_multi_remotes(
        self, repo_path: str, remotes: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Check the REAL sync status of `repo_path` against its configured (or given) remotes.

        Runs `git ls-remote` over the network for each remote and compares the
        remote's HEAD commit for the current branch against the local HEAD.
        """
        target_remotes = remotes if remotes is not None else self._configured_remotes(repo_path)

        branch_result = self._run_git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
        active_branch = branch_result.stdout.strip() or "HEAD"

        local_head_result = self._run_git(repo_path, "rev-parse", "HEAD")
        local_head = local_head_result.stdout.strip() if local_head_result.returncode == 0 else ""

        synced_remotes: List[Dict[str, Any]] = []
        for name, url in target_remotes.items():
            entry: Dict[str, Any] = {"remote_name": name, "url": url}
            ls_result = self._run_git(repo_path, "ls-remote", "--heads", name, active_branch)
            if ls_result.returncode != 0:
                entry["sync_status"] = "UNREACHABLE"
                entry["error"] = ls_result.stderr.strip().splitlines()[-1][:200] if ls_result.stderr.strip() else "git ls-remote failed"
            elif not ls_result.stdout.strip():
                entry["sync_status"] = "BRANCH_NOT_FOUND_ON_REMOTE"
            else:
                remote_head = ls_result.stdout.split()[0]
                entry["remote_head"] = remote_head
                entry["sync_status"] = "UP_TO_DATE" if remote_head == local_head else "OUT_OF_SYNC"
            synced_remotes.append(entry)

        if not synced_remotes:
            overall = "NO_REMOTES_CONFIGURED"
        elif all(r.get("sync_status") == "UP_TO_DATE" for r in synced_remotes):
            overall = "ALL_REMOTES_SYNCHRONIZED"
        else:
            overall = "SYNC_DRIFT_DETECTED"

        return {
            "source_repo": self.source_repo,
            "version": self.version,
            "local_path": repo_path,
            "synced_remotes": synced_remotes,
            "active_branch": active_branch,
            "latest_commit_hash": local_head,
            "status": overall,
        }

    def audit_repository_health(self, repo_path: str, large_file_mb: float = 5.0) -> Dict[str, Any]:
        """Run REAL repository health checks: uncommitted changes, merge conflicts,
        dangling objects, oversized tracked files, and branch drift vs. origin.
        """
        issues: List[str] = []
        score = 100.0

        # 1. Merge conflict in progress? (real filesystem check)
        conflict_in_progress = (Path(repo_path) / ".git" / "MERGE_HEAD").exists()
        if conflict_in_progress:
            issues.append("A merge is currently in progress (MERGE_HEAD present)")
            score -= 25

        # 2. Uncommitted / untracked changes (real `git status --porcelain`)
        status_result = self._run_git(repo_path, "status", "--porcelain")
        uncommitted = [l for l in status_result.stdout.splitlines() if l.strip()]
        if uncommitted:
            issues.append(f"{len(uncommitted)} uncommitted/untracked change(s)")
            score -= min(20.0, len(uncommitted) * 0.5)

        # 3. Dangling objects (real `git fsck`)
        fsck_result = self._run_git(repo_path, "fsck", "--dangling", "--no-progress", timeout=30)
        dangling = [l for l in fsck_result.stdout.splitlines() if l.startswith("dangling")]
        if dangling:
            issues.append(f"{len(dangling)} dangling git object(s)")
            score -= min(10.0, len(dangling) * 0.5)

        # 4. Oversized tracked files (real `git ls-files` + real filesystem stat)
        ls_files_result = self._run_git(repo_path, "ls-files")
        large_files: List[str] = []
        for rel_path in ls_files_result.stdout.splitlines():
            full_path = Path(repo_path) / rel_path
            try:
                if full_path.is_file() and full_path.stat().st_size > large_file_mb * 1024 * 1024:
                    large_files.append(rel_path)
            except OSError:
                continue
        if large_files:
            issues.append(f"{len(large_files)} tracked file(s) over {large_file_mb}MB")
            score -= min(15.0, len(large_files) * 3)

        # 5. Branch drift vs. origin (real `git rev-list --left-right --count`)
        branch_result = self._run_git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
        active_branch = branch_result.stdout.strip()
        branch_drift = False
        ahead, behind = 0, 0
        drift_result = self._run_git(
            repo_path, "rev-list", "--left-right", "--count",
            f"{active_branch}...origin/{active_branch}",
        )
        if drift_result.returncode == 0 and drift_result.stdout.strip():
            parts = drift_result.stdout.strip().split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])
                branch_drift = ahead > 0 or behind > 0
                if branch_drift:
                    issues.append(f"'{active_branch}' is {ahead} ahead / {behind} behind origin/{active_branch}")
                    score -= 5.0

        score = max(0.0, round(score, 1))
        if not issues:
            status = "HEALTHY"
        elif score >= 70:
            status = "NEEDS_ATTENTION"
        else:
            status = "UNHEALTHY"

        return {
            "source_repo": self.source_repo,
            "repo_path": repo_path,
            "repo_health_score": score,
            "conflicts_detected": 1 if conflict_in_progress else 0,
            "uncommitted_changes": len(uncommitted),
            "dangling_objects": len(dangling),
            "large_files": large_files,
            "branch_ahead": ahead,
            "branch_behind": behind,
            "branch_drift_detected": branch_drift,
            "issues": issues,
            "status": status,
        }

    def list_pr_issue_nexus(self) -> Dict[str, Any]:
        """STILL SIMULATED: listing real GitHub PRs/issues needs an authenticated API token.

        Unauthenticated calls to `api.github.com` are rate-limited/blocked from
        this environment, and no `GITHUB_TOKEN` is configured. To make this
        real: set `GITHUB_TOKEN` and call
        `GET https://api.github.com/repos/{owner}/{repo}/pulls` and
        `.../issues` with an `Authorization: Bearer <token>` header.
        """
        warn_simulated("GitNexusEngine.list_pr_issue_nexus (needs a GitHub token to be real)", "abhigyanpatwari/GitNexus")
        return {
            "source_repo": self.source_repo,
            "github_open_prs": 2,
            "gitlab_open_prs": 0,
            "github_issues_count": 5,
            "unified_board_status": "SYNCHRONIZED",
        }
