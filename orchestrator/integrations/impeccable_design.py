"""Integration for pbakaus/impeccable — now computes a REAL WCAG contrast ratio.

`audit_ui_component()` takes the component's actual foreground/background
CSS colors and computes a real contrast ratio via
`orchestrator.integrations._wcag` (the real WCAG 2.1 formula) instead of
always returning "AA Passed" / "4.8:1". If no colors are given, it says so
honestly rather than guessing a compliant-looking default.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from orchestrator.integrations._wcag import contrast_ratio, parse_css_color, passes_wcag_aa, passes_wcag_aaa


class ImpeccableDesignSkill:
    """Real (if narrow) UI audit skill: computes an actual WCAG contrast ratio from given colors."""

    def audit_ui_component(
        self,
        component_name: str,
        foreground_color: Optional[str] = None,
        background_color: Optional[str] = None,
        large_text: bool = False,
    ) -> Dict[str, Any]:
        """Audit `component_name`'s real contrast ratio, given its actual foreground/background colors.

        Colors accept `#rrggbb`/`#rgb` hex or `rgb()`/`rgba()` strings. This
        only checks contrast (the one thing computable from colors alone) —
        it does not inspect focus outlines, aria-labels, or other markup,
        since no markup is passed in.
        """
        recommendations: List[str] = [
            "Ensure focus-visible outline is present for keyboard navigation (not checked here — no markup given).",
            "Add aria-label to interactive icon buttons (not checked here — no markup given).",
        ]

        if not foreground_color or not background_color:
            return {
                "component": component_name,
                "wcag_compliance": "UNKNOWN",
                "contrast_ratio": None,
                "recommendations": [
                    "Pass foreground_color and background_color to compute a real WCAG contrast ratio.",
                    *recommendations,
                ],
                "status": "NEEDS_INPUT",
            }

        fg = parse_css_color(foreground_color)
        bg = parse_css_color(background_color)
        if fg is None or bg is None:
            return {
                "component": component_name,
                "wcag_compliance": "UNKNOWN",
                "contrast_ratio": None,
                "recommendations": [
                    f"Could not parse color(s): foreground={foreground_color!r}, background={background_color!r}. "
                    "Use #rrggbb/#rgb hex or rgb()/rgba().",
                    *recommendations,
                ],
                "status": "PARSE_ERROR",
            }

        ratio = contrast_ratio(fg, bg)
        aa = passes_wcag_aa(ratio, large_text=large_text)
        aaa = passes_wcag_aaa(ratio, large_text=large_text)
        compliance = "AAA" if aaa else ("AA" if aa else "FAIL")

        return {
            "component": component_name,
            "wcag_compliance": compliance,
            "contrast_ratio": f"{ratio}:1",
            "large_text": large_text,
            "recommendations": recommendations if aa else [
                f"Contrast ratio {ratio}:1 is below the WCAG AA minimum "
                f"({'3.0' if large_text else '4.5'}:1 for {'large' if large_text else 'normal'} text). "
                "Increase the difference between foreground and background lightness.",
                *recommendations,
            ],
            "status": "APPROVED" if aa else "REJECTED",
        }
