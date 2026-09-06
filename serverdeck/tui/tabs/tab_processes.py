from typing import Any, Dict, List
from serverdeck.core.i18n import i18n
from serverdeck.collectors.processes import get_detailed_processes
from serverdeck.tui.theme import colorize
from serverdeck.tui.components import (
    get_term_layout, render_box_header, render_box_line, render_box_footer,
    pad_visible, format_bytes
)

def render_tab_2_processes(sort_by: str, theme: Dict[str, Any], filter_str: str = "", selected_proc_idx: int = 0, is_modal: bool = False) -> List[Dict[str, Any]]:
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    w, h = get_term_layout()
    box_w = min(120, max(40, w - 2))
    inner_w = box_w - 4

    procs_all = get_detailed_processes(sort_by=sort_by, limit=150, filter_str=filter_str)
    total_count = len(procs_all)
    page_size = 3 if is_modal else 8
    total_pages = max(1, (total_count + page_size - 1) // page_size) if total_count else 1

    selected_proc_idx = max(0, min(selected_proc_idx, total_count - 1)) if total_count else 0
    current_page = selected_proc_idx // page_size if total_count else 0
    start_idx = current_page * page_size
    end_idx = min(total_count, start_idx + page_size)
    visible_procs = procs_all[start_idx:end_idx]

    sort_label = "CPU %" if sort_by == "cpu" else "RAM %"
    page_badge = f" [Page {current_page + 1}/{total_pages}]" if total_count else ""
    t2_title = f"{i18n.t('tab2_processes.title', sort=sort_label)}{page_badge}"
    print(render_box_header(t2_title, box_w, theme))

    col_pid = i18n.t("tab2_processes.pid", "PID")
    col_usr = i18n.t("tab2_processes.user", "USER")
    col_cpu = i18n.t("tab2_processes.cpu", "CPU %")
    col_mem = i18n.t("tab2_processes.mem", "MEM %")
    col_cmd = i18n.t("tab2_processes.command", "COMMAND")

    avail_cmd_w = max(18, inner_w - 58)
    header = f"  {'':<2} {col_pid:<7} {col_usr:<10} {col_cpu:<8} {col_mem:<8} {'RAM (RSS)':<12} {'STATUS':<8} {col_cmd}"
    print(render_box_line(colorize(header, c_label, bold=True), box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    for idx, p in enumerate(visible_procs):
        actual_idx = start_idx + idx
        is_selected = (actual_idx == selected_proc_idx)
        pointer = "► " if is_selected else "  "
        pid_str = str(p['pid'])
        user_str = p['user']
        cpu_str = f"{p['cpu_percent']:5.1f}%"
        mem_str = f"{p['memory_percent']:5.1f}%"
        rss_str = format_bytes(p['rss']).strip()
        status_str = p['status'][:7]
        name_str = p['name'][:avail_cmd_w]

        ptr_col = colorize(pointer, c_hl, bold=True)
        pid_col = colorize(pad_visible(pid_str, 7), c_val, bold=is_selected)
        usr_col = colorize(pad_visible(user_str, 10), c_label)
        cpu_col = colorize(pad_visible(cpu_str, 8), theme.get("warn", "#f59e0b") if p['cpu_percent'] > 50 else c_val)
        mem_col = colorize(pad_visible(mem_str, 8), theme.get("warn", "#f59e0b") if p['memory_percent'] > 50 else c_val)
        rss_col = colorize(pad_visible(rss_str, 12), c_hl)
        st_col = colorize(pad_visible(status_str, 8), theme.get("ok", "#00ff9d") if "run" in status_str else c_label)
        cmd_col = colorize(name_str, c_title if is_selected else c_val, bold=is_selected)

        line = f"{ptr_col} {pid_col} {usr_col} {cpu_col} {mem_col} {rss_col} {st_col} {cmd_col}"
        print(render_box_line(line, box_w, theme))

    if not visible_procs:
        print(render_box_line(colorize("No active processes found matching filter.", c_label), box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
    info_pos = f"• [Showing {start_idx + 1}-{end_idx} of {total_count}] | [s] Sort | [k] Kill | [/] Filter | [↑/↓/PgUp/PgDn] Scroll" if total_count else "• [s] Sort | [k] Kill | [/] Filter"
    print(render_box_line(info_pos, box_w, theme))
    print(render_box_footer(box_w, theme))
    return procs_all

