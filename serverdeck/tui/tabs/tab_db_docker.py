from typing import Any, Dict, List, Optional, Tuple
from serverdeck.core.i18n import i18n
from serverdeck.managers.docker import get_docker_containers
from serverdeck.managers.database import get_mariadb_databases, get_mariadb_users
from serverdeck.tui.theme import colorize
from serverdeck.tui.components import (
    get_term_layout, render_box_header, render_box_line, render_box_footer,
    pad_visible, format_bytes
)
def render_tab_7_db_and_docker(
    theme: Dict[str, Any],
    subview: int = 0,
    selected_container_idx: int = 0,
    selected_db_idx: int = 0,
    selected_user_idx: int = 0,
    snapshot_msg: Optional[str] = None,
    is_modal: bool = False,
    cached_containers: Optional[List[Dict[str, Any]]] = None,
    cached_dbs: Optional[List[Dict[str, Any]]] = None,
    cached_users: Optional[List[Dict[str, Any]]] = None,
    force_refresh: bool = False
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    w, h = get_term_layout()
    box_w = min(120, max(40, w - 2))
    inner_w = box_w - 4

    if cached_containers is not None and not force_refresh:
        containers = cached_containers
    elif subview == 0 or force_refresh:
        containers = get_docker_containers(force=force_refresh)
    else:
        containers = cached_containers if cached_containers is not None else []

    if cached_dbs is not None and not force_refresh:
        databases = cached_dbs
    elif subview == 1 or force_refresh:
        databases = get_mariadb_databases(force=force_refresh)
    else:
        databases = cached_dbs if cached_dbs is not None else []

    if cached_users is not None and not force_refresh:
        users = cached_users
    elif subview == 2 or force_refresh:
        users = get_mariadb_users(force=force_refresh)
    else:
        users = cached_users if cached_users is not None else []

    print(render_box_header("DOCKER CONTAINERS & MARIADB MANAGEMENT", box_w, theme))

    def fmt_sub(title: str, is_active: bool) -> str:
        if is_active:
            return colorize(f"▌►{title}◄▐", c_title, bold=True)
        return colorize(title, c_label)

    sub_0 = fmt_sub("Docker Containers", subview == 0)
    sub_1 = fmt_sub("DB Schemas", subview == 1)
    sub_2 = fmt_sub("User Accounts", subview == 2)
    subview_bar = f"• Subview: {sub_0} | {sub_1} | {sub_2}  [Tab]"
    print(render_box_line(subview_bar, box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    window_size = 2 if is_modal else 4

    if subview == 0:
        hdr = f"  {'':<2} {'CONTAINER ID':<14} {'NAME':<18} {'IMAGE':<18} {'STATUS':<10} {'PORTS'}"
        print(render_box_line(colorize(hdr, c_label, bold=True), box_w, theme))
        print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

        start_idx = max(0, min(selected_container_idx - window_size // 2, max(0, len(containers) - window_size)))
        visible_c = containers[start_idx:start_idx + window_size]

        for offset, c in enumerate(visible_c):
            actual_idx = start_idx + offset
            is_selected = (actual_idx == selected_container_idx)
            pointer = "► " if is_selected else "  "

            c_id = colorize(pad_visible(c['id'], 14), c_hl if is_selected else c_val, bold=is_selected)
            c_name = colorize(pad_visible(c['name'], 18), c_title if is_selected else c_val)
            c_img = colorize(pad_visible(c['image'], 18), c_label)
            st_color = theme.get("ok", "#00ff9d") if "up" in c['status'].lower() or "running" in c['status'].lower() else theme.get("crit", "#f43f5e")
            c_st = colorize(pad_visible(c['status'], 10), st_color)
            c_ports = colorize(c['ports'], c_hl)

            ptr_col = colorize(pointer, c_hl, bold=True)
            row = f"{ptr_col}{c_id} {c_name} {c_img} {c_st} {c_ports}"
            print(render_box_line(row, box_w, theme))

        if not containers:
            print(render_box_line(colorize("No active Docker containers running or detected.", c_label), box_w, theme))

        print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
        shortcuts = f"• Shortcuts: [n] New | [s] State | [r] Restart | [d] Del | [Tab] Switch"
        print(render_box_line(shortcuts, box_w, theme))
        print(render_box_footer(box_w, theme))

    elif subview == 1:
        hdr = f"  {'':<2} {'#':<4} {'DATABASE NAME':<24} {'TABLES':<10} {'SIZE':<14} {'TYPE'}"
        print(render_box_line(colorize(hdr, c_label, bold=True), box_w, theme))
        print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

        start_idx = max(0, min(selected_db_idx - window_size // 2, max(0, len(databases) - window_size)))
        visible_db = databases[start_idx:start_idx + window_size]

        for offset, d in enumerate(visible_db):
            actual_idx = start_idx + offset
            is_selected = (actual_idx == selected_db_idx)
            pointer = "► " if is_selected else "  "

            idx_str = f"#{actual_idx + 1}"
            name_str = d.get("name", "")[:22]
            tbl_count = str(d.get("tables", 0))
            sz_str = format_bytes(d.get("size_bytes", 0)).strip()
            db_engine = d.get("engine", "InnoDB")[:8]

            ptr_col = colorize(pointer, c_hl, bold=True)
            idx_col = colorize(pad_visible(idx_str, 4), c_label)
            name_col = colorize(pad_visible(name_str, 24), c_hl if is_selected else c_val, bold=is_selected)
            tbl_col = colorize(pad_visible(tbl_count, 10), c_val)
            sz_col = colorize(pad_visible(sz_str, 14), theme.get("accent", "#38bdf8"))
            eng_col = colorize(pad_visible(db_engine, 8), c_title)

            row = f"{ptr_col}{idx_col} {name_col} {tbl_col} {sz_col} {eng_col}"
            print(render_box_line(row, box_w, theme))

        if not databases:
            print(render_box_line(colorize("No MariaDB/MySQL databases found or connection failed.", c_label), box_w, theme))

        print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
        shortcuts = f"• Shortcuts: [n] Create DB | [d] Drop DB | [Tab] Switch"
        print(render_box_line(shortcuts, box_w, theme))
        print(render_box_footer(box_w, theme))

    elif subview == 2:
        hdr = f"  {'':<2} {'#':<4} {'USER ACCOUNT':<26} {'HOST':<18} {'PASSWORD':<12} {'TYPE'}"
        print(render_box_line(colorize(hdr, c_label, bold=True), box_w, theme))
        print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

        start_idx = max(0, min(selected_user_idx - window_size // 2, max(0, len(users) - window_size)))
        visible_u = users[start_idx:start_idx + window_size]

        for offset, u in enumerate(visible_u):
            actual_idx = start_idx + offset
            is_selected = (actual_idx == selected_user_idx)
            pointer = "► " if is_selected else "  "

            u_num = pad_visible(str(actual_idx + 1), 4)
            u_name = colorize(pad_visible(u['user'], 26), c_title if is_selected else c_val, bold=is_selected)
            u_host = colorize(pad_visible(u['host'], 18), c_hl)
            u_pass = colorize(pad_visible(u['has_password'], 12), theme.get("ok", "#00ff9d") if u['has_password'] == 'YES' else theme.get("crit", "#f43f5e"))
            u_type = colorize("System", c_label) if u['is_system'] else colorize("Standard", theme.get("ok", "#00ff9d"))

            ptr_col = colorize(pointer, c_hl, bold=True)
            row = f"{ptr_col} {u_num} {u_name} {u_host} {u_pass} {u_type}"
            print(render_box_line(row, box_w, theme))

        if not users:
            print(render_box_line(colorize("No user accounts found.", c_label), box_w, theme))

        print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))
        shortcuts = f"• Shortcuts: [n] Add | [d] Drop | [p] Pass | [g] Priv | [Tab] Switch"
        print(render_box_line(shortcuts, box_w, theme))
        print(render_box_footer(box_w, theme))

    return containers, databases, users

