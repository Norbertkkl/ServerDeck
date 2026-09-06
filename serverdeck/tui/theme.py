from typing import Any, Dict, Tuple
from serverdeck.core.state import load_app_config

THEMES: Dict[str, Dict[str, Any]] = {
    "glacier_cyan": {
        "name": "Glacier Cyan",
        "primary": "#00f0ff",
        "title": "#00f0ff",
        "border": "#1e3a8a",
        "border_bright": "#38bdf8",
        "header_bg": "#0f172a",
        "label": "#94a3b8",
        "value": "#f0f9ff",
        "highlight": "#38bdf8",
        "ok": "#00ff9d",
        "warn": "#f59e0b",
        "crit": "#f43f5e",
        "bar_fill": "#00f0ff",
        "bar_empty": "#1e293b",
        "tab_active_bg": "#0284c7",
        "tab_active_fg": "#ffffff",
        "tab_inactive_bg": "#0f172a",
        "tab_inactive_fg": "#64748b"
    },
    "matrix_green": {
        "name": "Matrix Green",
        "primary": "#00ff66",
        "title": "#00ff66",
        "border": "#064e3b",
        "border_bright": "#10b981",
        "header_bg": "#022c22",
        "label": "#6ee7b7",
        "value": "#ecfdf5",
        "highlight": "#34d399",
        "ok": "#10b981",
        "warn": "#eab308",
        "crit": "#ef4444",
        "bar_fill": "#00ff66",
        "bar_empty": "#064e3b",
        "tab_active_bg": "#047857",
        "tab_active_fg": "#ffffff",
        "tab_inactive_bg": "#022c22",
        "tab_inactive_fg": "#065f46"
    },
    "cyberpunk_neon": {
        "name": "Cyberpunk Neon",
        "primary": "#ff007f",
        "title": "#ff007f",
        "border": "#701a75",
        "border_bright": "#d946ef",
        "header_bg": "#2e1065",
        "label": "#f0abfc",
        "value": "#fdf4ff",
        "highlight": "#e879f9",
        "ok": "#00f0ff",
        "warn": "#fbbf24",
        "crit": "#f43f5e",
        "bar_fill": "#ff007f",
        "bar_empty": "#4a044e",
        "tab_active_bg": "#c026d3",
        "tab_active_fg": "#ffffff",
        "tab_inactive_bg": "#3b0764",
        "tab_inactive_fg": "#701a75"
    },
    "nordic_aurora": {
        "name": "Nordic Aurora",
        "primary": "#a78bfa",
        "title": "#a78bfa",
        "border": "#312e81",
        "border_bright": "#818cf8",
        "header_bg": "#1e1b4b",
        "label": "#c7d2fe",
        "value": "#eef2ff",
        "highlight": "#6366f1",
        "ok": "#34d399",
        "warn": "#fbbf24",
        "crit": "#f87171",
        "bar_fill": "#a78bfa",
        "bar_empty": "#312e81",
        "tab_active_bg": "#4f46e5",
        "tab_active_fg": "#ffffff",
        "tab_inactive_bg": "#1e1b4b",
        "tab_inactive_fg": "#3730a3"
    }
}

THEME_KEYS = list(THEMES.keys())

def load_app_themes() -> Dict[str, Dict[str, Any]]:
    cfg = load_app_config()
    custom_themes = cfg.get("custom_themes", {})
    all_themes = dict(THEMES)
    if isinstance(custom_themes, dict):
        for k, v in custom_themes.items():
            if isinstance(v, dict):
                merged = dict(THEMES.get("glacier_cyan", {}))
                merged.update(v)
                all_themes[k] = merged
    return all_themes

_rgb_cache: Dict[str, Tuple[int, int, int]] = {}

def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    h = hex_str.strip().lstrip('#')
    if h in _rgb_cache:
        return _rgb_cache[h]
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        _rgb_cache[h] = (r, g, b)
        return (r, g, b)
    return (255, 255, 255)

def colorize(text: str, hex_color: Any = None, bold: bool = False) -> str:
    codes = []
    if bold:
        codes.append("1")
    if hex_color and isinstance(hex_color, str) and hex_color.startswith("#"):
        r, g, b = hex_to_rgb(hex_color)
        codes.append(f"38;2;{r};{g};{b}")
    if codes:
        return f"\033[{';'.join(codes)}m{text}\033[0m"
    return text

