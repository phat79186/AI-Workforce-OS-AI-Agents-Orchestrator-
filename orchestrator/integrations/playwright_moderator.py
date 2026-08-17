"""Integration for microsoft/playwright — now backed by a REAL headless Chromium browser.

`run_ui_moderation()` launches a real headless Chromium via the real
`playwright` Python package, loads the given HTML, and measures real layout
overflow, real element bounding-box overlap, and real WCAG contrast ratios
(via `orchestrator.integrations._wcag`) against the page's actual computed
styles. `pixel_diff()` compares two real screenshot files pixel-by-pixel
with Pillow. Requires `pip install playwright && playwright install
chromium`; if the browser isn't installed, methods raise
`PlaywrightNotAvailableError` with instructions rather than silently
returning fake data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestrator.integrations._wcag import contrast_ratio, parse_css_color, passes_wcag_aa

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    _PLAYWRIGHT_IMPORT_ERROR: Optional[str] = None
except ImportError as e:  # pragma: no cover - exercised only when playwright isn't installed
    _PLAYWRIGHT_IMPORT_ERROR = str(e)


class PlaywrightNotAvailableError(RuntimeError):
    """Raised when the real `playwright` package/browser isn't installed."""


class PlaywrightVisualAuditor:
    """Real headless-Chromium visual auditor: layout overflow, element overlap, WCAG contrast."""

    def __init__(self) -> None:
        self.version = "1.44.0"
        self.source_repo = "microsoft/playwright"
        if _PLAYWRIGHT_IMPORT_ERROR:
            raise PlaywrightNotAvailableError(
                f"The 'playwright' package isn't importable ({_PLAYWRIGHT_IMPORT_ERROR}). "
                "Install it with: pip install playwright && playwright install chromium"
            )

    def run_ui_moderation(
        self, html_content: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Load `html_content` in a real headless Chromium and run real layout/contrast checks."""
        cfg = config or {}
        viewport = {"width": cfg.get("width", 1280), "height": cfg.get("height", 800)}
        issues: List[Dict[str, str]] = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    page = browser.new_page(viewport=viewport)
                    page.set_content(html_content, wait_until="load")

                    # --- Real layout overflow check (actual DOM measurement) ---
                    scroll_w = page.evaluate("document.documentElement.scrollWidth")
                    client_w = page.evaluate("document.documentElement.clientWidth")
                    overflow_detected = scroll_w > client_w
                    if overflow_detected:
                        issues.append({
                            "severity": "CRITICAL",
                            "element": "html",
                            "message": f"Horizontal overflow: scrollWidth={scroll_w}px > clientWidth={client_w}px",
                        })

                    # --- Real responsive viewport meta tag check (actual DOM query) ---
                    has_viewport_meta = page.evaluate(
                        "!!document.querySelector('meta[name=\"viewport\"]')"
                    )
                    if not has_viewport_meta:
                        issues.append({
                            "severity": "CRITICAL",
                            "element": "head",
                            "message": "Missing <meta name=\"viewport\"> tag.",
                        })

                    # --- Real element bounding-box overlap check ---
                    overlaps = page.evaluate(
                        """
                        () => {
                            const els = Array.from(document.querySelectorAll('body *'))
                                .filter(e => e.offsetWidth > 0 && e.offsetHeight > 0);
                            const rects = els.map(e => ({ tag: e.tagName, rect: e.getBoundingClientRect() }));
                            const overlapping = [];
                            for (let i = 0; i < rects.length; i++) {
                                for (let j = i + 1; j < rects.length; j++) {
                                    const a = rects[i].rect, b = rects[j].rect;
                                    const overlapArea = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left))
                                        * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
                                    const smallerArea = Math.min(a.width * a.height, b.width * b.height);
                                    if (smallerArea > 0 && overlapArea / smallerArea > 0.5) {
                                        overlapping.push([rects[i].tag, rects[j].tag]);
                                    }
                                }
                            }
                            return overlapping.slice(0, 10);
                        }
                        """
                    )
                    element_overlap_detected = len(overlaps) > 0
                    if element_overlap_detected:
                        issues.append({
                            "severity": "WARNING",
                            "element": "body",
                            "message": f"{len(overlaps)} sibling element pair(s) overlap by >50% of the smaller element's area.",
                        })

                    # --- Real WCAG contrast check on visible text nodes ---
                    text_styles = page.evaluate(
                        """
                        () => Array.from(document.querySelectorAll('body *'))
                            .filter(e => e.offsetWidth > 0 && e.offsetHeight > 0
                                && Array.from(e.childNodes).some(n => n.nodeType === 3 && n.textContent.trim()))
                            .slice(0, 50)
                            .map(e => {
                                const s = getComputedStyle(e);
                                return { color: s.color, bg: s.backgroundColor, fontSize: parseFloat(s.fontSize), fontWeight: s.fontWeight, tag: e.tagName };
                            })
                        """
                    )
                    contrast_failures = []
                    worst_ratio: Optional[float] = None
                    for style in text_styles:
                        fg = parse_css_color(style["color"])
                        bg = parse_css_color(style["bg"])
                        if not fg or not bg or style["bg"] in ("rgba(0, 0, 0, 0)", "transparent"):
                            continue  # transparent background: can't reliably compute against this element alone
                        ratio = contrast_ratio(fg, bg)
                        is_large = style["fontSize"] >= 24 or (
                            style["fontSize"] >= 18.66 and style["fontWeight"] in ("bold", "700", "800", "900")
                        )
                        if worst_ratio is None or ratio < worst_ratio:
                            worst_ratio = ratio
                        if not passes_wcag_aa(ratio, large_text=is_large):
                            contrast_failures.append({"tag": style["tag"], "ratio": ratio})

                    if contrast_failures:
                        issues.append({
                            "severity": "CRITICAL",
                            "element": "text",
                            "message": f"{len(contrast_failures)} element(s) fail WCAG AA contrast (worst ratio: {worst_ratio}:1).",
                        })

                finally:
                    browser.close()
        except PlaywrightError as e:
            raise PlaywrightNotAvailableError(f"Playwright browser error: {e}") from e

        score = 100.0 - (len(issues) * 15.0)
        return {
            "source_repo": self.source_repo,
            "version": self.version,
            "visual_qa_score": max(score, 0.0),
            "wcag_aa_contrast_pass": len(contrast_failures) == 0,
            "worst_contrast_ratio": worst_ratio,
            "layout_overflow_detected": overflow_detected,
            "element_overlap_detected": element_overlap_detected,
            "issues": issues,
            "status": "APPROVED" if score >= 80 else "REJECTED",
        }

    def pixel_diff(self, baseline_path: str, candidate_path: str) -> Dict[str, Any]:
        """Compare two real screenshot files pixel-by-pixel using Pillow."""
        from PIL import Image, ImageChops

        base_p, cand_p = Path(baseline_path), Path(candidate_path)
        if not base_p.exists() or not cand_p.exists():
            missing = base_p if not base_p.exists() else cand_p
            raise FileNotFoundError(f"Screenshot not found: {missing}")

        img_a = Image.open(base_p).convert("RGB")
        img_b = Image.open(cand_p).convert("RGB")
        if img_a.size != img_b.size:
            return {
                "source_repo": self.source_repo,
                "baseline": baseline_path,
                "candidate": candidate_path,
                "diff_pixels_percentage": 100.0,
                "mismatched_pixels_count": img_a.size[0] * img_a.size[1],
                "regression_detected": True,
                "status": "SIZE_MISMATCH",
            }

        diff = ImageChops.difference(img_a, img_b)
        bbox = diff.getbbox()
        if bbox is None:
            mismatched = 0
        else:
            # Count pixels with any real per-channel difference above a small tolerance (anti-aliasing noise).
            diff_data = diff.getdata()
            mismatched = sum(1 for px in diff_data if max(px) > 10)

        total_pixels = img_a.size[0] * img_a.size[1]
        diff_pct = round((mismatched / total_pixels) * 100, 4) if total_pixels else 0.0

        return {
            "source_repo": self.source_repo,
            "baseline": baseline_path,
            "candidate": candidate_path,
            "diff_pixels_percentage": diff_pct,
            "mismatched_pixels_count": mismatched,
            "regression_detected": diff_pct > 0.1,
            "status": "VISUAL_MATCH_PASSED" if diff_pct <= 0.1 else "VISUAL_REGRESSION_DETECTED",
        }
