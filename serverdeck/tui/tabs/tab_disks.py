from typing import Any, Dict, List, Optional
from serverdeck.core.i18n import i18n
from serverdeck.collectors.disks import get_physical_drives, get_block_devices_and_partitions
from serverdeck.tui.theme import colorize
from serverdeck.tui.components import (
    get_term_layout, render_box_header, render_box_line, render_box_footer,
    render_bar, pad_visible, format_bytes
)

def render_tab_5_partitions_and_smart(theme: Dict[str, Any], selected_part_idx: int = 0, snapshot_msg: Optional[str] = None, is_modal: bool = False) -> List[Dict[str, Any]]:
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    w, h = get_term_layout()
    box_w = min(120, max(40, w - 2))
    inner_w = box_w - 4

    drives = get_physical_drives()
    partitions = get_block_devices_and_partitions()

    print(render_box_header("STORAGE DEVICES, PARTITIONS & S.M.A.R.T. HEALTH", box_w, theme))

    drv_hdr = f"  {'DRIVE':<12} {'MODEL':<18} {'SIZE':<10} {'HEALTH':<10} {'TEMP':<8} {'POH':<8} {'WEAR'}"
    print(render_box_line(colorize(drv_hdr, c_label, bold=True), box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    for d in drives[:2]:
        h_badge = colorize("PASSED", theme.get("ok", "#00ff9d"), bold=True) if d.get("passed", True) else colorize("FAILED", theme.get("crit", "#f43f5e"), bold=True)
        sz_str = format_bytes(d.get("size_bytes", 0)).strip()
        t_str = f"{d.get('temp_c', 0)}°C" if d.get('temp_c') else "N/A"
        poh_str = f"{d.get('power_on_hours', 0)}h"
        wear_str = f"{d.get('wear_pct', 0)}%" if d.get('nvme') else "N/A"

        d_name = colorize(pad_visible(d.get("name", "dev"), 12), c_title)
        d_model = colorize(pad_visible(d.get("model", "Disk")[:16], 18), c_val)
        row = f"  {d_name} {d_model} {pad_visible(sz_str, 10)} {pad_visible(h_badge, 10)} {pad_visible(t_str, 8)} {pad_visible(poh_str, 8)} {colorize(wear_str, c_hl)}"
        print(render_box_line(row, box_w, theme))

    if not drives:
        print(render_box_line(colorize("No physical drive telemetry detected.", c_label), box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    p_hdr = f"  {'':<2} {'DEVICE':<14} {'FSTYPE':<8} {'MOUNTPOINT':<18} {'USAGE (USED / TOTAL)'}"
    print(render_box_line(colorize(p_hdr, c_label, bold=True), box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    window_size = 2 if is_modal else 4
    start_idx = max(0, min(selected_part_idx - window_size // 2, max(0, len(partitions) - window_size)))
    visible_parts = partitions[start_idx:start_idx + window_size]

    for offset, p in enumerate(visible_parts):
        actual_idx = start_idx + offset
        is_selected = (actual_idx == selected_part_idx)
        pointer = "► " if is_selected else "  "

        dev_str = p.get("path", "")[:12]
        fs_str = p.get("fstype", "raw")[:7]
        mp_str = p.get("mountpoint", "[unmounted]")[:16]
        pct = p.get("used_pct", 0.0)
        used_s = format_bytes(p.get("used_bytes", 0)).strip()
        tot_s = format_bytes(p.get("size", 0)).strip()

        bar = render_bar(pct, 10, theme)
        ptr_col = colorize(pointer, c_hl, bold=True)
        dev_col = colorize(pad_visible(dev_str, 14), c_hl if is_selected else c_val, bold=is_selected)
        fs_col = colorize(pad_visible(fs_str, 8), c_label)
        mp_col = colorize(pad_visible(mp_str, 18), c_title if mp_str != "[unmounted]" else c_label)
        usage_col = f"{bar} ({used_s}/{tot_s})"

        line = f"{ptr_col}{dev_col} {fs_col} {mp_col} {usage_col}"
        print(render_box_line(line, box_w, theme))

    if not partitions:
        print(render_box_line(colorize("No block device partitions detected.", c_label), box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
    shortcuts = f"• Shortcuts: [m] Mount | [u] Unmount | [f] Format | [t] SMART Test | [c] FSCK Check"
    print(render_box_line(shortcuts, box_w, theme))
    print(render_box_footer(box_w, theme))
    return partitions

