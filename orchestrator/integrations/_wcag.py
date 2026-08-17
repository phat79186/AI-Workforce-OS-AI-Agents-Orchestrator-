"""Real WCAG 2.1 relative-luminance / contrast-ratio math, shared across integrations.

Formulas are from the actual WCAG 2.1 spec (§1.4.3 Contrast Minimum), not
approximated or hardcoded. Used by `playwright_moderator.py`, `taste_skill.py`,
`ui_ux_pro_max.py`, and `impeccable_design.py` so all of them report a real,
consistently-computed contrast ratio instead of a fixed "AA Passed" string.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

RGB = Tuple[int, int, int]

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
_RGB_FN_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")


def parse_css_color(value: str) -> Optional[RGB]:
    """Parse a `#rrggbb`/`#rgb` hex string or an `rgb()`/`rgba()` function into an (r, g, b) tuple.

    Returns None if `value` doesn't match either format (e.g. a named CSS
    color like "tomato" — callers should resolve those to hex/rgb first).
    """
    value = value.strip()
    hex_match = _HEX_RE.match(value)
    if hex_match:
        h = hex_match.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    fn_match = _RGB_FN_RE.match(value)
    if fn_match:
        return (int(fn_match.group(1)), int(fn_match.group(2)), int(fn_match.group(3)))

    return None


def relative_luminance(rgb: RGB) -> float:
    """Compute the real WCAG 2.1 relative luminance of an (r, g, b) 0-255 color."""

    def channel(c: int) -> float:
        c_srgb = c / 255.0
        return c_srgb / 12.92 if c_srgb <= 0.03928 else ((c_srgb + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(rgb1: RGB, rgb2: RGB) -> float:
    """Compute the real WCAG 2.1 contrast ratio between two colors (range: 1.0 to 21.0)."""
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def passes_wcag_aa(ratio: float, large_text: bool = False) -> bool:
    """Real WCAG 2.1 AA thresholds: 3:1 for large text (>=18pt/14pt-bold), 4.5:1 otherwise."""
    return ratio >= (3.0 if large_text else 4.5)


def passes_wcag_aaa(ratio: float, large_text: bool = False) -> bool:
    """Real WCAG 2.1 AAA thresholds: 4.5:1 for large text, 7:1 otherwise."""
    return ratio >= (4.5 if large_text else 7.0)
