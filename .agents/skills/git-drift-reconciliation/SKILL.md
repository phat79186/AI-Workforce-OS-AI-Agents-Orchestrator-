---
name: git-drift-reconciliation
description: Safeguard GitNexus multi-remote workflows with pre-push divergence checks, conflict dry-runs, and safe reconciliation across GitHub and GitLab mirrors.
---

# Git Drift Reconciliation Skill

Prevents multi-remote divergence and race-condition merge conflicts when synchronizing local workspaces across multiple remote repositories (e.g. GitHub and GitLab mirrors).

## When to Use
- Before pushing commits to multiple remote targets.
- When remote branches have diverged (e.g. `ahead/behind` status detected).
- When a fast-forward push is rejected by a remote host.
- During automated agentic continuous delivery (CD) workflows.

## The Drift Reconciliation Pipeline

```text
                     MULTI-REMOTE SYNC COMMAND
                                │
                                ▼
                   STEP 1: REMOTE TRACKING FETCH
                     (git fetch --all --prune)
                                │
                                ▼
                   STEP 2: DIVERGENCE AUDITING
            (Checks ahead/behind count across all remotes)
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
         NO DIVERGENCE (0/0)           DIVERGENCE DETECTED
                 │                             │
                 │                             ▼
                 │                 STEP 3: REBASE SAFEGUARD
                 │              (Auto rebase with dry-run test)
                 │                             │
                 └──────────────┬──────────────┘
                                │
                                ▼
                   STEP 4: ATOMIC ATTEMPT PUSH
             (Pushes sequentially to GitHub & GitLab with
              immediate rollback on primary failure)
```

## How to Execute via GitNexus & Shell

### 1. Check Divergence Status across Remotes
```bash
# Fetch latest references without merging
git fetch --all --prune

# Audit commit divergence against origin
git rev-list --left-right --count HEAD...@{upstream}
```

### 2. Run Pre-Push Health Audit in Python
```python
from orchestrator.integrations import ExternalEcosystemHub

hub = ExternalEcosystemHub()

# 1. Audit repository health (checks uncommitted diffs, untracked blobs)
health = hub.git_nexus.audit_repository_health(".")
print(f"Repo Health: {health['repo_health_score']}/100 | Status: {health['status']}")

# 2. Run multi-remote sync check
sync_info = hub.git_nexus.sync_multi_remotes(".")
print(f"Sync Status: {sync_info['status']} | Active Branch: {sync_info['active_branch']}")
for r in sync_info['synced_remotes']:
    print(f"  Remote: {r['remote_name']} -> {r['sync_status']}")
```

### 3. Safe Rebase Command if Divergence Occurs
```bash
# Pull and rebase cleanly without creating messy merge commits
git pull --rebase origin main

# Once clean, push to primary remote
git push origin main
```

## Best Practices
- Never use `git push --force` on shared remote repositories.
- Always verify that unit tests pass (100% Green) after resolving any rebase conflict before pushing.
- Configure secondary remotes as mirrors or automated backups to preserve single source of truth on primary remote.
