from typing import Any, Dict, Optional
from serverdeck.core.i18n import i18n
from serverdeck.tui.theme import colorize
from serverdeck.tui.components import (
    get_term_layout, render_box_header, render_box_line, render_box_footer,
    render_bar, format_bytes
)

def render_tab_5_kernel_memory_services(stats: Dict[str, Any], theme: Dict[str, Any], snapshot_msg: Optional[str] = None):
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    w, h = get_term_layout()
    box_w = min(120, max(40, w - 2))
    inner_w = box_w - 4

    mem = stats.get("memory", {})
    services = stats.get("services", {})

    print(render_box_header("KERNEL MEMORY SUBSYSTEM & CORE DAEMONS", box_w, theme))

    ram_used = format_bytes(mem.get("used", 0)).strip()
    ram_tot = format_bytes(mem.get("total", 0)).strip()
    ram_avail = format_bytes(mem.get("available", 0)).strip()
    ram_bar = render_bar(mem.get("percent", 0.0), 12, theme)

    swap_used = format_bytes(mem.get("swap_used", 0)).strip()
    swap_tot = format_bytes(mem.get("swap_total", 0)).strip()
    swap_bar = render_bar(mem.get("swap_percent", 0.0), 12, theme)

    l1 = f"• {colorize('RAM Utilization:', c_label)}  {ram_bar} ({ram_used} / {ram_tot}, Avail: {ram_avail})"
    l2 = f"• {colorize('SWAP Space:     ', c_label)}  {swap_bar} ({swap_used} / {swap_tot})"
    print(render_box_line(l1, box_w, theme))
    print(render_box_line(l2, box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    buf_s = format_bytes(mem.get("buffers", 0)).strip()
    cach_s = format_bytes(mem.get("cached", 0)).strip()
    slab_s = format_bytes(mem.get("slab", 0)).strip()
    dirty_s = format_bytes(mem.get("dirty", 0)).strip()

    l3 = f"• {colorize('Buffers:', c_label)} {colorize(buf_s, c_val)}   • {colorize('Page Cache:', c_label)} {colorize(cach_s, c_val)}   • {colorize('Kernel Slab:', c_label)} {colorize(slab_s, c_val)}"
    hp_tot = mem.get("hugepages_total", 0)
    hp_free = mem.get("hugepages_free", 0)
    hp_sz = mem.get("hugepages_size_kb", 2048)
    l4 = f"• {colorize('Dirty Pages:', c_label)} {colorize(dirty_s, c_hl)}   • {colorize('HugePages:', c_label)} {colorize(f'{hp_tot - hp_free}/{hp_tot} ({hp_sz}KB)', c_val)}"
    print(render_box_line(l3, box_w, theme))
    print(render_box_line(l4, box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    svc_items = []
    for s_name, is_act in services.items():
        st_txt = colorize("[ ACTIVE ]", theme.get("ok", "#00ff9d"), bold=True) if is_act else colorize("[ INACTIVE ]", theme.get("bar_empty", "#1e293b"))
        svc_items.append(f"{s_name}: {st_txt}")

    row_svc_1 = "   ".join(svc_items[:3])
    row_svc_2 = "   ".join(svc_items[3:6])
    print(render_box_line(f"• {colorize('Core Services:', c_label)}  {row_svc_1}", box_w, theme))
    if row_svc_2:
        print(render_box_line(f"                     {row_svc_2}", box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
    shortcuts = f"• Shortcuts: [w] Force Telemetry Report Webhook"
    print(render_box_line(shortcuts, box_w, theme))
    print(render_box_footer(box_w, theme))

