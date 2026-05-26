"""Inline SVG icons (Lucide-inspired, MIT-licensed style).

Each icon is a 24x24 viewBox stroke-only path that uses ``currentColor`` so
it inherits text color from the surrounding element. Use ``icon(name)`` to
get a renderable HTML string.
"""

from typing import Optional

# Raw path data for each icon — kept compact, all 24x24 viewBox.
_PATHS = {
    # ── Navigation ──────────────────────────────────────────────────────
    "home":       '<path d="M3 12 12 3l9 9"/><path d="M5 10v10h14V10"/>',
    "back":       '<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>',
    "menu":       '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "search":     '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',

    # ── Core actions ────────────────────────────────────────────────────
    "add":        '<path d="M12 5v14M5 12h14"/>',
    "delete":     '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M10 11v6M14 11v6"/><path d="M5 6l1 14a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-14"/>',
    "edit":       '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 1 1 3 3L7 19l-4 1 1-4Z"/>',
    "confirm":    '<path d="M20 6 9 17l-5-5"/>',
    "close":      '<path d="M18 6 6 18M6 6l12 12"/>',
    "clear":      '<path d="M3 6h18M8 6V4h8v2"/><path d="M19 6 17 22H7L5 6"/>',
    "save":       '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
    "play":       '<path d="m6 4 14 8-14 8Z"/>',
    "refresh":    '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
    "info":       '<circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v4h1"/>',
    "warning":    '<path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4M12 17h.01"/>',
    "calendar":   '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "settings":   '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',

    # ── Auth ────────────────────────────────────────────────────────────
    "login":      '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5"/><path d="M15 12H3"/>',
    "logout":     '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
    "lock":       '<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',

    # ── Domain — meals/recipes ──────────────────────────────────────────
    "recipe":     '<path d="M3 10a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v0a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M5 12v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-8"/>',
    "plate":      '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/>',
    "utensils":   '<path d="M3 2v7a3 3 0 0 0 6 0V2"/><path d="M6 9v13"/><path d="M15 2v20"/><path d="M15 8h2a2 2 0 0 1 2 2v6"/>',
    "breakfast":  '<circle cx="12" cy="18" r="2"/><path d="M3 21h18"/><path d="M12 9v3"/><path d="M5 18a7 7 0 0 1 14 0"/><path d="M5 5l1.5 1.5M19 5l-1.5 1.5M12 3v2"/>',
    "lunch":      '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>',
    "dinner":     '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
    "snack":      '<circle cx="12" cy="12" r="9"/><path d="M9 9h.01M15 9h.01M9 15h.01M15 15h.01M12 12h.01"/>',

    # ── Macros / nutrition ──────────────────────────────────────────────
    "flame":      '<path d="M8 14a4 4 0 0 0 8 0c0-3-2-5-2-8 0-2-2-3-2-3s-1 4-3 6-3 3-3 5Z"/>',
    "protein":    '<path d="M6 4h12l-2 6h-8Z"/><path d="M8 10v8a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-8"/>',
    "carbs":      '<path d="M5 12c0-4 3-7 7-7s7 3 7 7v6H5Z"/><path d="M5 18h14"/>',
    "fat":        '<circle cx="12" cy="12" r="8"/><path d="M9 10c1 1 5 1 6 0M9 14c1 1 5 1 6 0"/>',

    # ── Domain — workouts (training figure) ─────────────────────────────
    "training":   '<circle cx="12" cy="4" r="2"/><path d="M14 7h-4l-2 5 3 2v6"/><path d="M11 14l3-2 3 4"/><path d="M6 12l2-2"/>',
    "dumbbell":   '<path d="M6 6v12M18 6v12"/><path d="M3 9v6M21 9v6"/><path d="M6 12h12"/>',
    "running":    '<circle cx="13" cy="4" r="2"/><path d="m4 22 5-5 2-3-1-3-3-1"/><path d="m11 11 4 1 1 4 3 2"/><path d="m18 8-1 4"/>',

    # ── Domain — inventory / scanner / agent ────────────────────────────
    "inventory":  '<path d="m21 16-9 5-9-5V8l9-5 9 5Z"/><path d="m3 8 9 5 9-5"/><path d="M12 22V13"/>',
    "package":    '<path d="m21 16-9 5-9-5V8l9-5 9 5Z"/><path d="M3.27 6.96 12 12.01l8.73-5.05M12 22.08V12"/>',
    "scan":       '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
    "receipt":    '<path d="M4 2v20l3-2 3 2 3-2 3 2 3-2V2l-3 2-3-2-3 2-3-2-3 2Z"/><path d="M8 8h8M8 12h8M8 16h6"/>',
    "agent":      '<rect width="16" height="14" x="4" y="6" rx="2"/><path d="M9 2v4M15 2v4"/><circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/><path d="M10 17h4"/>',
    "user":       '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',

    # ── Misc ────────────────────────────────────────────────────────────
    "star":       '<path d="m12 2 3 7h7l-6 4 2 7-6-4-6 4 2-7-6-4h7Z"/>',
    "target":     '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "trophy":     '<path d="M6 9H4a2 2 0 0 1-2-2V5h4"/><path d="M18 9h2a2 2 0 0 0 2-2V5h-4"/><path d="M6 5h12v6a6 6 0 0 1-12 0Z"/><path d="M9 19h6"/><path d="M12 15v4"/>',
}


def icon(name: str, size: int = 20, color: Optional[str] = None,
         decorative: bool = False, label: Optional[str] = None) -> str:
    """Return an inline SVG string for ``name``.

    Args:
        name: icon key from the registry. Falls back to a placeholder square.
        size: pixel size (square).
        color: optional explicit color; defaults to ``currentColor``.
        decorative: if True, marks SVG as ``aria-hidden`` (no a11y text).
        label: explicit aria-label. If omitted, uses ``name``.
    """
    path = _PATHS.get(name)
    stroke = color or "currentColor"
    if not path:
        path = '<rect width="16" height="16" x="4" y="4" rx="2"/>'
    aria = 'aria-hidden="true"' if decorative else f'role="img" aria-label="{label or name}"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{stroke}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" {aria} '
        f'style="display:inline-block;vertical-align:middle">{path}</svg>'
    )


def has_icon(name: str) -> bool:
    return name in _PATHS
