import shutil
from typing import Any, Dict, List, Optional
from serverdeck.tui.theme import colorize
from serverdeck.core.formatters import (
    visible_len, truncate_visible, pad_visible, format_bytes, format_uptime
)

def get_term_layout() -> tuple[int, int]:
    cols, rows = shutil.get_terminal_size(fallback=(78, 24))
    return max(40, cols), max(10, rows)

def get_box_width(cols: Optional[int] = None) -> int:
    if cols is None:
        cols, _ = get_term_layout()
    if cols < 80:
        return max(40, cols - 2)
    return min(120, cols - 2)

def render_box_line(content: str, width: int, theme: Dict[str, Any]) -> str:
    c_border = theme.get("border", "#1e3a8a")
    inner_w = max(0, width - 4)
    if visible_len(content) > inner_w:
        content = truncate_visible(content, inner_w)
    vlen = visible_len(content)
    pad = max(0, inner_w - vlen)
    return f"{colorize('│', c_border)} {content}{' ' * pad} {colorize('│', c_border)}"

def render_box_header(title: str, width: int, theme: Dict[str, Any]) -> str:
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    t_str = f"──[ {colorize(title, c_title, bold=True)} ]"
    pad = max(0, width - 2 - visible_len(t_str))
    return f"{colorize('╭' + t_str + '─' * pad + '╮', c_border)}"

def render_modal_box(title: str, prompt: str, input_val: str, hint: str, theme: Dict[str, Any], box_w: int) -> List[str]:
    c_pri = theme.get("primary", "#00f0ff")
    c_ok = theme.get("ok", "#00ff9d")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    lines = []
    hdr = f"──[ {colorize(title, c_pri, bold=True)} ]"
    hdr_line = f"╭{hdr}" + "─" * max(0, box_w - 2 - visible_len(hdr)) + "╮"
    lines.append(hdr_line)

    if prompt:
        p_txt = f" {colorize(prompt, c_label)}"
        lines.append(render_box_line(p_txt, box_w, theme))

    field_content = f" > {colorize(input_val, c_val, bold=True)}{colorize('█', c_ok)}"
    lines.append(render_box_line(field_content, box_w, theme))

    h_txt = f" {colorize(hint, c_hl)}"
    lines.append(render_box_line(h_txt, box_w, theme))
    lines.append(render_box_footer(box_w, theme))
    return lines

def render_box_footer(width: int, theme: Dict[str, Any]) -> str:
    c_border = theme.get("border", "#1e3a8a")
    return colorize("╰" + "─" * (width - 2) + "╯", c_border)

def render_bar(pct: float, width: int = 14, theme: Optional[Dict[str, Any]] = None) -> str:
    fill_c = theme.get("bar_fill", "#00f0ff") if theme else "#00f0ff"
    empty_c = theme.get("bar_empty", "#1e293b") if theme else "#1e293b"
    ok_c = theme.get("ok", "#00ff9d") if theme else "#00ff9d"
    warn_c = theme.get("warn", "#f59e0b") if theme else "#f59e0b"
    crit_c = theme.get("crit", "#f43f5e") if theme else "#f43f5e"

    clamped = max(0.0, min(100.0, pct))
    fill_chars = int(round((clamped / 100.0) * width))
    empty_chars = width - fill_chars

    if clamped >= 90.0:
        val_c = crit_c
    elif clamped >= 75.0:
        val_c = warn_c
    else:
        val_c = ok_c

    bar_str = colorize("█" * fill_chars, fill_c) + colorize("░" * empty_chars, empty_c)
    val_str = colorize(f"{clamped:4.1f}%", val_c)
    return f"╢{bar_str}╟ {val_str}"

def render_area_chart(
    data: List[float],
    width: int = 44,
    height: int = 3,
    color_high: str = "#00f0ff",
    color_low: str = "#1e3a8a",
    empty_char: str = " "
) -> List[str]:
    shades = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    if not data:
        data = [0.0]

    if len(data) >= width:
        pts = data[-width:]
    else:
        pts = [0.0] * (width - len(data)) + list(data)

    max_val = max(pts) if max(pts) > 0.0 else 1.0
    lines = []
    for r in range(height - 1, -1, -1):
        row_str = []
        r_bottom = (r / height) * max_val
        r_top = ((r + 1) / height) * max_val
        for p in pts:
            if p <= r_bottom:
                row_str.append(empty_char)
            elif p >= r_top:
                t = r / max(1, height - 1)
                r_c = int(int(color_low[1:3], 16) * (1 - t) + int(color_high[1:3], 16) * t)
                g_c = int(int(color_low[3:5], 16) * (1 - t) + int(color_high[3:5], 16) * t)
                b_c = int(int(color_low[5:7], 16) * (1 - t) + int(color_high[5:7], 16) * t)
                row_str.append(f"\033[38;2;{r_c};{g_c};{b_c}m█\033[0m")
            else:
                fraction = (p - r_bottom) / (r_top - r_bottom)
                idx = int(fraction * 8)
                char = shades[max(1, min(8, idx))]
                t = r / max(1, height - 1)
                r_c = int(int(color_low[1:3], 16) * (1 - t) + int(color_high[1:3], 16) * t)
                g_c = int(int(color_low[3:5], 16) * (1 - t) + int(color_high[3:5], 16) * t)
                b_c = int(int(color_low[5:7], 16) * (1 - t) + int(color_high[5:7], 16) * t)
                row_str.append(f"\033[38;2;{r_c};{g_c};{b_c}m{char}\033[0m")
        lines.append("".join(row_str))
    return lines
