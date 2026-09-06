from typing import Any, Dict
from serverdeck.core.i18n import i18n
from serverdeck.core.history import MetricsHistory
from serverdeck.tui.theme import colorize
from serverdeck.tui.components import (
    get_term_layout, render_box_header, render_box_line, render_box_footer,
    pad_visible
)

def render_tab_4_hardware_sensors(stats: Dict[str, Any], history: MetricsHistory, theme: Dict[str, Any]):
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    w, h = get_term_layout()
    box_w = min(120, max(40, w - 2))
    inner_w = box_w - 4

    sensors = stats.get("sensors", [])
    gpus = stats.get("gpus", [])

    print(render_box_header("HARDWARE THERMAL SENSORS & GPU MONITOR", box_w, theme))

    tbl_hdr = f"  {'SENSOR / ZONE':<22} {'CURRENT TEMP':<16} {'WARNING':<12} {'CRITICAL':<12} {'STATUS'}"
    print(render_box_line(colorize(tbl_hdr, c_label, bold=True), box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    for s in sensors[:4]:
        c_temp = s.get("current", 0.0)
        h_temp = s.get("high", 80.0)
        crit_temp = s.get("critical", 95.0)

        if c_temp >= crit_temp:
            st_badge = colorize("[ CRIT ]", theme.get("crit", "#f43f5e"), bold=True)
            t_col = theme.get("crit", "#f43f5e")
        elif c_temp >= h_temp:
            st_badge = colorize("[ WARN ]", theme.get("warn", "#f59e0b"), bold=True)
            t_col = theme.get("warn", "#f59e0b")
        else:
            st_badge = colorize("[  OK  ]", theme.get("ok", "#00ff9d"))
            t_col = c_val

        s_name = colorize(pad_visible(s.get("name", "Sensor")[:20], 22), c_hl)
        s_cur = colorize(pad_visible(f"{c_temp:.1f} °C", 16), t_col, bold=True)
        s_high = colorize(pad_visible(f"{h_temp:.1f} °C", 12), c_label)
        s_crit = colorize(pad_visible(f"{crit_temp:.1f} °C", 12), c_label)

        row = f"  {s_name} {s_cur} {s_high} {s_crit} {st_badge}"
        print(render_box_line(row, box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    if gpus:
        gpu_hdr = f"  {'ACCELERATOR / GPU':<28} {'TEMPERATURE':<16} {'VRAM UTILIZATION'}"
        print(render_box_line(colorize(gpu_hdr, c_label, bold=True), box_w, theme))
        for g in gpus[:2]:
            g_name = colorize(pad_visible(g.get("name", "GPU")[:26], 28), c_title)
            g_temp = colorize(pad_visible(f"{g.get('temperature', 0.0):.1f} °C", 16), c_val)
            g_vram = colorize("Integrated / Shared System RAM", c_label)
            print(render_box_line(f"  {g_name} {g_temp} {g_vram}", box_w, theme))
    else:
        print(render_box_line(colorize("  No dedicated discrete PCI GPU devices detected.", c_label), box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
    shortcuts = f"• Shortcuts: Standard Dashboard Navigation"
    print(render_box_line(shortcuts, box_w, theme))
    print(render_box_footer(box_w, theme))

