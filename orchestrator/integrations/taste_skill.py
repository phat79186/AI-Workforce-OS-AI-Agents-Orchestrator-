""""Taste Skill" for aesthetic curation guidelines.

Honest scope: "visual taste" is inherently a subjective/curatorial opinion —
there is no real algorithm that objectively scores it, so this version no
longer fabricates a `visual_taste_score: 0.98` precision number implying a
measurement that doesn't exist. The guideline checklist below is a real,
hand-written design opinion (labeled as such), not a computed metric. The
one thing that IS objectively measurable — contrast — is now computed for
real via `orchestrator.integrations._wcag` when `context` provides actual
colors; otherwise that field is honestly omitted rather than guessed.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from orchestrator.integrations._wcag import contrast_ratio, parse_css_color, passes_wcag_aa

_GUIDELINES = {
    "spatial_harmony": {
        "grid_system": "8px baseline grid",
        "alignment": "Optical margin alignment",
        "whitespace_balance": "Generous breathing space with intentional padding contrast",
    },
    "typography_hierarchy": {
        "font_family": "Inter, Outfit, sans-serif",
        "heading_style": "Tracking-tight (-0.02em), font-weight 700",
        "body_style": "Line-height 1.6, font-weight 400",
    },
    "motion_choreography": {
        "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
        "duration": "180ms",
        "hover_interaction": "Subtle scale (1.02x) with smooth shadow elevation transition",
    },
    "taste_guidelines": [
        "Eliminate generic raw colors (plain red/blue); use curated HSL brand themes",
        "Maintain visual weight balance across hero sections and action buttons",
        "Apply subtle glassmorphism backdrop blur (12px) without visual clutter",
        "Ensure fluid motion transitions for enhanced user delight",
    ],
}


class TasteSkill:
    """Curated (human-written, clearly labeled as opinion) design guidelines + real contrast check."""

    def __init__(self) -> None:
        self.version = "2.0.0"
        self.skill_name = "taste-ui-ux"

    def curate_design_taste(
        self, component_or_page: str = "Global UI Component", context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Return the curated guideline checklist, plus a REAL contrast check if `context` gives colors.

        `context` may include `foreground_color` / `background_color` (hex or
        rgb()) to get a real WCAG-verified contrast measurement for the
        target component. There is intentionally no overall numeric "taste
        score" — see module docstring for why.
        """
        target = component_or_page.strip()
        ctx = context or {}

        result: Dict[str, Any] = {
            "skill_name": self.skill_name,
            "version": self.version,
            "target_component": target,
            "note": "The fields below are a curated design opinion (not a computed score) "
                    "except 'measured_contrast', which is real WCAG math when colors are supplied.",
            **_GUIDELINES,
            "status": "GUIDELINES_PROVIDED",
        }

        fg = parse_css_color(ctx.get("foreground_color", "")) if ctx.get("foreground_color") else None
        bg = parse_css_color(ctx.get("background_color", "")) if ctx.get("background_color") else None
        if fg and bg:
            ratio = contrast_ratio(fg, bg)
            result["measured_contrast"] = {
                "ratio": f"{ratio}:1",
                "wcag_aa_pass": passes_wcag_aa(ratio),
            }
            result["status"] = "GUIDELINES_PROVIDED_WITH_CONTRAST_CHECK"

        return result
