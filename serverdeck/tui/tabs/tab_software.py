from typing import Any, Dict, Optional
from serverdeck.core.i18n import i18n
from serverdeck.managers.installer import get_software_hub_status, get_installer_actions, PythonInstallerManager
from serverdeck.tui.theme import colorize
from serverdeck.tui.components import (
    get_term_layout, render_box_header, render_box_line, render_box_footer,
    pad_visible
)

def render_tab_10_installer(theme: Dict[str, Any], selected_idx: int = 0, installer_mgr: Optional[PythonInstallerManager] = None, is_modal: bool = False):
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    w, h = get_term_layout()
    box_w = min(120, max(40, w - 2))
    inner_w = box_w - 4

    hub_data = get_software_hub_status()
    packages_status = hub_data.get("packages", {})
    py_v = hub_data.get("python_ver", "N/A")
    node_v = hub_data.get("node_ver", "N/A")
    java_v = hub_data.get("java_ver", "N/A")
    act_cnt = hub_data.get("active_count", 0)

    actions = get_installer_actions()
    total_pkgs = len(actions)

    hdr_title = f"SOFTWARE HUB & INSTALLED RUNTIMES ({act_cnt}/{total_pkgs} Active)"
    print(render_box_header(hdr_title, box_w, theme))

    runtime_line = f"• {colorize('Python:', c_label)} {colorize(py_v, c_val)}   • {colorize('Node.js:', c_label)} {colorize(node_v, c_val)}   • {colorize('Java:', c_label)} {colorize(java_v, c_val)}"
    print(render_box_line(runtime_line, box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    if installer_mgr and installer_mgr.is_running:
        status_line = f"• {colorize('STATUS:', theme.get('warn', '#f59e0b'), bold=True)} {colorize(installer_mgr.active_action, c_hl)} (Running in background...)"
        print(render_box_line(status_line, box_w, theme))
        print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

        tail_lines = installer_mgr.output_lines[-4:]
        for line in tail_lines:
            print(render_box_line(colorize(line[:inner_w], c_label), box_w, theme))
        for _ in range(4 - len(tail_lines)):
            print(render_box_line("", box_w, theme))

        print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
        print(render_box_line(colorize("• Installation in progress. Please wait for completion.", c_hl), box_w, theme))
        print(render_box_footer(box_w, theme))
        return

    tbl_hdr = f"  {'':<2} {'PACKAGE':<18} {'STATUS':<17} {'DESCRIPTION'}"
    print(render_box_line(colorize(tbl_hdr, c_label, bold=True), box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    window_size = 4 if is_modal else 7
    start_idx = max(0, min(selected_idx - window_size // 2, max(0, total_pkgs - window_size)))
    visible_actions = actions[start_idx:start_idx + window_size]

    for offset, (act_id, name, desc) in enumerate(visible_actions):
        actual_idx = start_idx + offset
        is_selected = (actual_idx == selected_idx)
        pointer = "► " if is_selected else "  "

        is_inst, is_act = packages_status.get(act_id, (False, False))
        if is_act:
            badge_text = "[ ACTIVE ]"
            st_badge = colorize(badge_text, theme.get("ok", "#00ff9d"), bold=True)
        elif is_inst:
            badge_text = "[ INSTALLED ]"
            st_badge = colorize(badge_text, theme.get("highlight", "#38bdf8"))
        else:
            badge_text = "[ NOT INSTALLED ]"
            st_badge = colorize(badge_text, theme.get("bar_empty", "#1e293b"))

        num_str = f"[{act_id:>2}]"
        disp_name = f"{num_str} {name[:13]}"
        name_str = colorize(pad_visible(disp_name, 18), c_title if is_selected else c_val, bold=is_selected)
        badge_str = pad_visible(st_badge, 17)
        desc_str = colorize(desc[:34], c_label)

        ptr_col = colorize(pointer, c_hl, bold=True)
        row_txt = f"{ptr_col}{name_str} {badge_str} {desc_str}"
        print(render_box_line(row_txt, box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
    scroll_info = f"• Showing {start_idx+1}-{min(total_pkgs, start_idx+window_size)} of {total_pkgs} packages (Use ↑ / ↓ to scroll)   Press [Enter] to install"
    print(render_box_line(colorize(scroll_info, c_label), box_w, theme))
    shortcuts = f"Shortcuts: [Enter]/[i] Install | [u]/[x] Uninstall | [r] Restart | [↑/↓] Select"
    print(render_box_line(shortcuts, box_w, theme))
    print(render_box_footer(box_w, theme))

