---
name: tiered-visual-qa
description: Eliminate Playwright browser latency and memory overhead using a fast 2-tier testing strategy (Instant Static DOM/CSS Linting -> On-Demand Headless Playwright).
---

# Tiered Visual QA Skill

Eliminates the latency (~1-2s) and memory footprint of launching headless Chromium binaries for every minor UI change by enforcing a 2-tier visual testing lifecycle.

## When to Use
- During rapid iterative UI/UX development and code refinement loops.
- When evaluating component markup, accessibility, and color contrast without browser overhead.
- In CI pipelines to fail fast before spinning up heavy browser containers.
- Prior to final commit or Pull Request submission to verify pixel-diff fidelity.

## The 2-Tier Visual Testing Lifecycle

```text
                    GENERATED HTML/CSS COMPONENT
                                │
                                ▼
                   TIER 1: STATIC AUDIT (<10ms)
             (Evaluates viewport meta, color contrast math,
              missing alt/aria attributes, and placeholder assets)
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
              FAILED                        PASSED
         (Instant feedback,                    │
          no browser cost)                     ▼
                                    IS PRE-COMMIT / PR MERGE?
                                        ┌──────┴──────┐
                                        ▼             ▼
                                       YES            NO
                                        │             │
                                        ▼             ▼
                          TIER 2: PLAYWRIGHT E2E    FAST EXIT
                       (Headless Chromium render,   (Approved in
                        screenshot & Pixel-Diff)     <15ms)
```

## How to Execute in Code

```python
from orchestrator.integrations import ExternalEcosystemHub

hub = ExternalEcosystemHub()

html_content = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: Inter, sans-serif; background: #0f172a; color: #f8fafc; }
    .btn { background: #6366f1; color: #ffffff; padding: 8px 16px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>Executive AI Dashboard</h1>
  <button class="btn" aria-label="Deploy initiative">Deploy Initiative</button>
</body>
</html>
"""

# 1. Tier 1: Instant Static Audit
if hub.playwright_moderator:
    tier1_res = hub.playwright_moderator.run_ui_moderation(html_content)
    print(f"Tier 1 Status: {tier1_res['status']} | Score: {tier1_res['visual_qa_score']}/100")

    # 2. Tier 2: Run Headless Pixel-Diff only if Tier 1 passes and full check is needed
    if tier1_res["status"] == "APPROVED":
        # Compares rendered screenshot against baseline
        diff_res = hub.playwright_moderator.pixel_diff("baseline.png", "candidate.png")
        print(f"Tier 2 Pixel Regression: {diff_res['status']} (Diff: {diff_res['diff_pixels_percentage']}%)")
```

## Best Practices
- Keep Tier 1 automated and always-on during agent code generation.
- Never spin up headless Chromium if Tier 1 reports basic errors like missing viewport or invalid contrast ratios.
- Run Tier 2 only on release milestones or pre-commit verification hooks.
