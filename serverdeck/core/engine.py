import os
import sys
import time
import copy
import signal
import termios
import tty
import select
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from serverdeck.core.state import (
    SNAPSHOT_FILE, save_json, save_app_language, save_app_theme,
    load_app_config, get_stats_snapshot, get_snapshot_file_path
)
from serverdeck.core.i18n import i18n
from serverdeck.core.history import MetricsHistory
from serverdeck.core.watchdog import ServerDeckWatchdog
from serverdeck.collectors.system import get_all_device_stats
from serverdeck.collectors.processes import kill_process_by_pid
from serverdeck.collectors.disks import get_smart_device_details
from serverdeck.managers.storage import AsyncDiskWorker
from serverdeck.managers.database import (
    create_database, drop_database, create_db_user, drop_db_user,
    grant_db_privileges, reset_db_password
)
from serverdeck.managers.docker import (
    docker_container_action, docker_container_delete, deploy_docker_template
)
from serverdeck.managers.firewall import get_ufw_status, ufw_action
from serverdeck.managers.webhook import (
    send_system_telemetry_webhook, send_test_webhook_alert
)
from serverdeck.managers.installer import (
    PythonInstallerManager, get_installer_actions
)
from serverdeck.tui.theme import THEMES, THEME_KEYS, colorize
from serverdeck.tui.components import (
    get_term_layout, visible_len, render_box_line, render_box_footer, render_modal_box
)
from serverdeck.tui.navigation import render_tab_bar
from serverdeck.tui.tabs import (
    render_tab_1_dashboard, render_tab_2_processes, render_tab_3_network,
    render_tab_4_hardware_sensors, render_tab_5_partitions_and_smart,
    render_tab_5_kernel_memory_services, render_tab_7_db_and_docker,
    render_tab_8_ufw, render_tab_10_installer
)

INSTALLER_ACTIONS = get_installer_actions()

def display_dashboard(
    stats: Optional[Dict[str, Any]],
    history: MetricsHistory,
    active_tab: int = 1,
    sort_by: str = "cpu",
    theme_key: str = "glacier_cyan",
    is_paused: bool = False,
    refresh_rate: float = 1.0,
    snapshot_msg: Optional[str] = None,
    filter_str: str = "",
    selected_proc_idx: int = 0,
    selected_container_idx: int = 0,
    selected_db_idx: int = 0,
    selected_user_idx: int = 0,
    db_subview: int = 0,
    selected_ufw_idx: int = 0,
    selected_part_idx: int = 0,
    selected_installer_idx: int = 0,
    installer_mgr: Optional[PythonInstallerManager] = None,
    prompt_text: Optional[str] = None,
    modal_info: Optional[Tuple[str, str, str, str]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    theme = THEMES[theme_key]
    c_bbright = theme.get("border_bright", "#38bdf8")
    c_title = theme.get("title", "#00f0ff")
    w, h = get_term_layout()
    inner_w = max(40, w - 4)

    if w < 65 or h < 18:
        box_w = max(30, w - 2)
        print(colorize("╔" + "═" * (box_w - 2) + "╗", c_bbright, bold=True))
        title = "TERMINAL WINDOW TOO SMALL"
        print(f"{colorize('║', c_bbright, bold=True)} {colorize(f'{title:^{box_w - 4}}', theme.get('warn', '#f59e0b'), bold=True)} {colorize('║', c_bbright, bold=True)}")
        print(colorize("╚" + "═" * (box_w - 2) + "╝", c_bbright, bold=True))
        c_msg1 = f"Current size: {w}x{h} (Min: 65x18)"
        c_msg2 = "Please enlarge window to display UI"
        print(render_box_line(c_msg1, box_w, theme))
        print(render_box_line(c_msg2, box_w, theme))
        print(render_box_footer(box_w, theme))
        sys.stdout.write("\033[J")
        sys.stdout.flush()
        return [], [], [], [], [], []

    box_w = min(120, max(40, w - 2))
    frame_w = box_w
    frame_inner = max(10, frame_w - 4)
    print(colorize("╔" + "═" * (frame_w - 2) + "╗", c_bbright, bold=True))
    status_tag = " [PAUSED]" if is_paused else ""
    ts_val = stats['timestamp'] if stats else time.strftime("%Y-%m-%d %H:%M:%S")
    title = f"SERVERDECK{status_tag} ({ts_val})"
    print(f"{colorize('║', c_bbright, bold=True)} {colorize(f'{title:^{frame_inner}}', c_title, bold=True)} {colorize('║', c_bbright, bold=True)}")
    print(colorize("╚" + "═" * (frame_w - 2) + "╝", c_bbright, bold=True))

    print(" " + render_tab_bar(active_tab, theme))
    print()

    current_procs = []
    current_containers = []
    current_dbs = []
    current_users = []
    current_ufw_rules = []
    current_partitions = []

    is_modal = (modal_info is not None)

    if active_tab == 1 and stats:
        render_tab_1_dashboard(stats, history, theme)
    elif active_tab == 2:
        current_procs = render_tab_2_processes(sort_by, theme, filter_str, selected_proc_idx, is_modal=is_modal)
    elif active_tab == 3 and stats:
        render_tab_3_network(stats, history, theme)
    elif active_tab == 4 and stats:
        render_tab_4_hardware_sensors(stats, history, theme)
    elif active_tab == 5:
        current_partitions = render_tab_5_partitions_and_smart(theme, selected_part_idx, snapshot_msg, is_modal=is_modal)
    elif active_tab == 6 and stats:
        render_tab_5_kernel_memory_services(stats, theme, snapshot_msg)
    elif active_tab == 7:
        current_containers, current_dbs, current_users = render_tab_7_db_and_docker(
            theme, db_subview, selected_container_idx, selected_db_idx, selected_user_idx, snapshot_msg, is_modal=is_modal
        )
    elif active_tab == 8:
        current_ufw_rules = render_tab_8_ufw(theme, selected_ufw_idx, filter_str, snapshot_msg, is_modal=is_modal)
    elif active_tab == 9 or active_tab == 10:
        render_tab_10_installer(theme, selected_installer_idx, installer_mgr, is_modal=is_modal)

    if modal_info is not None:
        m_title, m_prompt, m_val, m_hint = modal_info
        modal_lines = render_modal_box(m_title, m_prompt, m_val, m_hint, theme, box_w)
        for ml in modal_lines:
            print(ml)
    elif prompt_text is not None:
        p_len = visible_len(prompt_text)
        print(colorize(f"──[ PROMPT: {prompt_text} ]" + "─" * max(2, w - p_len - 15) + "──", theme.get("ok", "#00ff9d"), bold=True))
    elif snapshot_msg:
        s_len = visible_len(snapshot_msg)
        print(colorize(f"──[ STATUS: {snapshot_msg} ]" + "─" * max(2, w - s_len - 15) + "──", theme.get("ok", "#00ff9d"), bold=True))
    else:
        theme_name = theme.get("name", theme_key)
        lang_label = i18n.current_lang.upper()
        footer = f" [1-9/Tab] Tabs | [l] Lang: {lang_label} | [c] Theme: {theme_name} | [+/-] {refresh_rate:.1f}s | [p] Pause | [q] Quit "
        foot_w = max(40, w - 2)
        if len(footer) > foot_w - 4:
            footer = f" [1-9] Tabs | [l] {lang_label} | [c] Theme | [+/-] {refresh_rate:.1f}s | [q] Quit "
        print(colorize(f"──{footer:─^{foot_w - 4}}──", c_bbright))

    sys.stdout.write("\033[J")
    sys.stdout.flush()
    return current_procs, current_containers, current_dbs, current_users, current_ufw_rules, current_partitions

def get_keypress(timeout: float = 0.05) -> Optional[str]:
    fd = sys.stdin.fileno()
    rlist, _, _ = select.select([fd], [], [], timeout)
    if not rlist:
        return None

    ch = sys.stdin.read(1)
    if ch == '\033':
        rlist, _, _ = select.select([fd], [], [], 0.02)
        if not rlist:
            return 'ESC'
        ch2 = sys.stdin.read(1)
        if ch2 == '[':
            rlist, _, _ = select.select([fd], [], [], 0.02)
            if not rlist:
                return 'ESC'
            ch3 = sys.stdin.read(1)
            if ch3 == 'A': return 'UP'
            if ch3 == 'B': return 'DOWN'
            if ch3 == 'C': return 'RIGHT'
            if ch3 == 'D': return 'LEFT'
            if ch3 == 'H': return 'HOME'
            if ch3 == 'F': return 'END'
            if ch3 in ('5', '6'):
                ch4 = sys.stdin.read(1) if select.select([fd], [], [], 0.02)[0] else ''
                if ch3 == '5' and ch4 == '~': return 'PAGE_UP'
                if ch3 == '6' and ch4 == '~': return 'PAGE_DOWN'
            if ch3 == '3':
                ch4 = sys.stdin.read(1) if select.select([fd], [], [], 0.02)[0] else ''
                if ch4 == '~': return 'DELETE'
        return 'ESC'
    return ch

def sanitize_snapshot_data(val: Any) -> Any:
    sensitive_keys = ("password", "token", "secret", "webhook", "auth", "key", "credential", "private")
    if isinstance(val, dict):
        cleaned = {}
        for k, v in val.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in sensitive_keys) and not k_lower.endswith(("_count", "_total", "_len", "_keys")):
                cleaned[k] = "***"
            else:
                cleaned[k] = sanitize_snapshot_data(v)
        return cleaned
    elif isinstance(val, list):
        return [sanitize_snapshot_data(item) for item in val]
    elif isinstance(val, str):
        if "discord.com/api/webhooks/" in val:
            return "***"
        return val
    return val

def export_snapshot_json(stats: Dict[str, Any], history: MetricsHistory) -> str:
    safe_stats = get_stats_snapshot() or copy.deepcopy(stats)
    clean_metrics = sanitize_snapshot_data(safe_stats)
    snapshot_data = {
        "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": clean_metrics,
        "history_averages": {
            "avg_cpu_last_minute": round(sum(history.cpu_history) / max(1, len(history.cpu_history)), 2),
            "avg_ram_last_minute": round(sum(history.ram_history) / max(1, len(history.ram_history)), 2),
            "peak_rx_bytes_sec": round(max(history.net_rx_history, default=0.0), 2),
            "peak_tx_bytes_sec": round(max(history.net_tx_history, default=0.0), 2)
        }
    }
    target_path = get_snapshot_file_path()
    save_json(target_path, snapshot_data, indent=2)
    t_now = time.strftime('%H:%M:%S')
    if getattr(i18n, 'current_lang', 'en') == 'pl':
        return f"Zapisano snapshot do {target_path.name} o {t_now}"
    return f"Snapshot exported to {target_path.name} at {t_now}"

def run_monitor():
    sys.stdout.write("\033[?1049h\033[?25l\033[2J\033[H")
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    active_tab = 1
    sort_by = "cpu"
    is_paused = False
    refresh_rate = 1.0
    app_cfg = load_app_config()
    saved_theme = app_cfg.get("active_theme", "glacier_cyan")
    theme_idx = THEME_KEYS.index(saved_theme) if saved_theme in THEME_KEYS else 0
    snapshot_msg: Optional[str] = None
    snapshot_msg_timer = 0.0

    watchdog = ServerDeckWatchdog(check_interval=15.0)
    watchdog.start()

    installer_mgr = PythonInstallerManager()
    disk_worker = AsyncDiskWorker()

    selected_proc_idx = 0
    filter_str = ""
    is_filtering = False
    is_killing = False
    kill_input_pid = ""

    db_subview = 0
    selected_container_idx = 0
    selected_db_idx = 0
    selected_user_idx = 0
    is_deploying_container = False
    deploy_input_choice = ""
    is_deleting_container = False
    is_creating_db = False
    db_input_name = ""
    is_dropping_db = False
    is_creating_db_user = False
    db_input_user = ""
    is_dropping_db_user = False
    is_granting_db_priv = False
    db_input_grant_dbname = ""
    is_resetting_db_pass = False
    db_input_new_pass = ""

    selected_ufw_idx = 0
    is_adding_ufw = False
    ufw_input_rule = ""
    is_deleting_ufw = False

    selected_installer_idx = 0
    is_uninstalling_software = False

    selected_part_idx = 0
    is_mounting = False
    mount_input = ""
    is_unmounting = False
    is_formatting = False
    format_input_fs = ""

    cached_procs: List[Dict[str, Any]] = []
    cached_containers: List[Dict[str, Any]] = []
    cached_dbs: List[Dict[str, Any]] = []
    cached_users: List[Dict[str, Any]] = []
    cached_ufw_rules: List[Dict[str, Any]] = []
    cached_partitions: List[Dict[str, Any]] = []

    history = MetricsHistory(history_len=46)
    last_refresh_time = 0.0
    need_full_clear = True
    stats = None

    def on_window_resize(signum, frame):
        nonlocal need_full_clear
        need_full_clear = True

    try:
        signal.signal(signal.SIGWINCH, on_window_resize)
    except Exception:
        pass

    try:
        while True:
            now = time.time()
            time_until_refresh = max(0.0, (last_refresh_time + refresh_rate) - now)
            poll_timeout = min(0.05, time_until_refresh)

            key = get_keypress(timeout=poll_timeout)
            need_immediate_render = False

            if installer_mgr.is_running or disk_worker.is_running:
                need_immediate_render = True

            if disk_worker.result_msg and time.time() < disk_worker.result_timer:
                snapshot_msg = disk_worker.result_msg
                snapshot_msg_timer = disk_worker.result_timer
                disk_worker.result_msg = ""
                need_immediate_render = True

            if is_filtering:
                if key:
                    if key in ('\n', '\r', 'ESC'):
                        is_filtering = False
                    elif key in ('\x7f', '\x08'):
                        filter_str = filter_str[:-1]
                        selected_proc_idx = 0
                        selected_ufw_idx = 0
                    elif len(key) == 1 and key.isprintable():
                        filter_str += key
                        selected_proc_idx = 0
                        selected_ufw_idx = 0
                    need_immediate_render = True
            elif is_creating_db:
                if key:
                    if key in ('\n', '\r'):
                        if db_input_name.strip():
                            ok, msg = create_database(db_input_name.strip())
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                        is_creating_db = False
                        db_input_name = ""
                        need_immediate_render = True
                    elif key == 'ESC':
                        is_creating_db = False
                        db_input_name = ""
                        need_immediate_render = True
                    elif key in ('\x7f', '\x08'):
                        db_input_name = db_input_name[:-1]
                        need_immediate_render = True
                    elif len(key) == 1 and key.isprintable():
                        db_input_name += key
                        need_immediate_render = True
            elif is_dropping_db:
                if key:
                    if key in ('\n', '\r', 'y', 'Y'):
                        if cached_dbs and selected_db_idx < len(cached_dbs):
                            target_db = cached_dbs[selected_db_idx]["name"]
                            ok, msg = drop_database(target_db)
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                            selected_db_idx = max(0, selected_db_idx - 1)
                        is_dropping_db = False
                        need_immediate_render = True
                    elif key in ('n', 'N', 'ESC'):
                        is_dropping_db = False
                        need_immediate_render = True
            elif is_creating_db_user:
                if key:
                    if key in ('\n', '\r'):
                        if db_input_user.strip():
                            u_str = db_input_user.strip()
                            if ":" in u_str:
                                user_part, pass_part = u_str.split(":", 1)
                            else:
                                user_part, pass_part = u_str, ""
                            if "@" in user_part:
                                uname, host = user_part.split("@", 1)
                            else:
                                uname, host = user_part, "%"
                            ok, msg = create_db_user(uname, host, pass_part)
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                        is_creating_db_user = False
                        db_input_user = ""
                        need_immediate_render = True
                    elif key == 'ESC':
                        is_creating_db_user = False
                        db_input_user = ""
                        need_immediate_render = True
                    elif key in ('\x7f', '\x08'):
                        db_input_user = db_input_user[:-1]
                        need_immediate_render = True
                    elif len(key) == 1 and key.isprintable():
                        db_input_user += key
                        need_immediate_render = True
            elif is_dropping_db_user:
                if key:
                    if key in ('\n', '\r', 'y', 'Y'):
                        if cached_users and selected_user_idx < len(cached_users):
                            u = cached_users[selected_user_idx]
                            ok, msg = drop_db_user(u["user"], u["host"])
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                            selected_user_idx = max(0, selected_user_idx - 1)
                        is_dropping_db_user = False
                        need_immediate_render = True
                    elif key in ('n', 'N', 'ESC'):
                        is_dropping_db_user = False
                        need_immediate_render = True
            elif is_granting_db_priv:
                if key:
                    if key in ('\n', '\r'):
                        if db_input_grant_dbname.strip() and cached_users and selected_user_idx < len(cached_users):
                            u = cached_users[selected_user_idx]
                            ok, msg = grant_db_privileges(db_input_grant_dbname.strip(), u["user"], u["host"])
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                        is_granting_db_priv = False
                        db_input_grant_dbname = ""
                        need_immediate_render = True
                    elif key == 'ESC':
                        is_granting_db_priv = False
                        db_input_grant_dbname = ""
                        need_immediate_render = True
                    elif key in ('\x7f', '\x08'):
                        db_input_grant_dbname = db_input_grant_dbname[:-1]
                        need_immediate_render = True
                    elif len(key) == 1 and key.isprintable():
                        db_input_grant_dbname += key
                        need_immediate_render = True
            elif is_resetting_db_pass:
                if key:
                    if key in ('\n', '\r'):
                        if db_input_new_pass.strip() and cached_users and selected_user_idx < len(cached_users):
                            u = cached_users[selected_user_idx]
                            ok, msg = reset_db_password(u["user"], u["host"], db_input_new_pass.strip())
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                        is_resetting_db_pass = False
                        db_input_new_pass = ""
                        need_immediate_render = True
                    elif key == 'ESC':
                        is_resetting_db_pass = False
                        db_input_new_pass = ""
                        need_immediate_render = True
                    elif key in ('\x7f', '\x08'):
                        db_input_new_pass = db_input_new_pass[:-1]
                        need_immediate_render = True
                    elif len(key) == 1 and key.isprintable():
                        db_input_new_pass += key
                        need_immediate_render = True
            elif is_deleting_container:
                if key:
                    if key in ('\n', '\r', 'y', 'Y'):
                        if cached_containers and selected_container_idx < len(cached_containers):
                            cid = cached_containers[selected_container_idx]["id"]
                            ok, msg = docker_container_delete(cid)
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                            selected_container_idx = max(0, selected_container_idx - 1)
                        is_deleting_container = False
                        need_immediate_render = True
                    elif key in ('n', 'N', 'ESC'):
                        is_deleting_container = False
                        need_immediate_render = True
            elif is_deploying_container:
                if key:
                    if key in ('1', '2', '3', '4', '5', '6', '7', '8'):
                        ok, msg = deploy_docker_template(key)
                        snapshot_msg = msg
                        snapshot_msg_timer = time.time() + 5.0
                        is_deploying_container = False
                        deploy_input_choice = ""
                        need_immediate_render = True
                    elif key == 'ESC':
                        is_deploying_container = False
                        deploy_input_choice = ""
                        need_immediate_render = True
            elif is_uninstalling_software:
                if key:
                    if key in ('\n', '\r', 'y', 'Y', 'u', 'U'):
                        if not installer_mgr.is_running and selected_installer_idx < len(INSTALLER_ACTIONS):
                            act_num = INSTALLER_ACTIONS[selected_installer_idx][0]
                            installer_mgr.start_action(act_num, mode="uninstall")
                            need_immediate_render = True
                        is_uninstalling_software = False
                    else:
                        is_uninstalling_software = False
                        need_immediate_render = True
            elif is_killing:
                if key:
                    if key in ('\n', '\r'):
                        pid_to_kill = kill_input_pid or (str(cached_procs[selected_proc_idx]['pid']) if cached_procs and selected_proc_idx < len(cached_procs) else "")
                        if pid_to_kill.isdigit():
                            ok, msg = kill_process_by_pid(int(pid_to_kill), sig=15)
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                        is_killing = False
                        kill_input_pid = ""
                        need_immediate_render = True
                    elif key == '9':
                        pid_to_kill = kill_input_pid or (str(cached_procs[selected_proc_idx]['pid']) if cached_procs and selected_proc_idx < len(cached_procs) else "")
                        if pid_to_kill.isdigit():
                            ok, msg = kill_process_by_pid(int(pid_to_kill), sig=9)
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                        is_killing = False
                        kill_input_pid = ""
                        need_immediate_render = True
                    elif key == 'ESC':
                        is_killing = False
                        kill_input_pid = ""
                        need_immediate_render = True
                    elif key in ('\x7f', '\x08'):
                        kill_input_pid = kill_input_pid[:-1]
                        need_immediate_render = True
                    elif key.isdigit():
                        kill_input_pid += key
                        need_immediate_render = True
            elif is_adding_ufw:
                if key:
                    if key in ('\n', '\r'):
                        if ufw_input_rule.strip():
                            rule_args = ufw_input_rule.strip().split()
                            ok, msg = ufw_action(rule_args)
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                        is_adding_ufw = False
                        ufw_input_rule = ""
                        need_immediate_render = True
                    elif key == 'ESC':
                        is_adding_ufw = False
                        ufw_input_rule = ""
                        need_immediate_render = True
                    elif key in ('\x7f', '\x08'):
                        ufw_input_rule = ufw_input_rule[:-1]
                        need_immediate_render = True
                    elif len(key) == 1 and key.isprintable():
                        ufw_input_rule += key
                        need_immediate_render = True
            elif is_deleting_ufw:
                if key:
                    if key in ('\n', '\r', 'y', 'Y'):
                        if cached_ufw_rules and selected_ufw_idx < len(cached_ufw_rules):
                            r_num = str(cached_ufw_rules[selected_ufw_idx]["num"])
                            ok, msg = ufw_action(["delete", r_num])
                            snapshot_msg = msg
                            snapshot_msg_timer = time.time() + 4.0
                            selected_ufw_idx = max(0, selected_ufw_idx - 1)
                        is_deleting_ufw = False
                        need_immediate_render = True
                    elif key in ('n', 'N', 'ESC'):
                        is_deleting_ufw = False
                        need_immediate_render = True
            elif is_mounting:
                if key:
                    if key in ('\n', '\r'):
                        if mount_input.strip() and cached_partitions and selected_part_idx < len(cached_partitions):
                            target_p = cached_partitions[selected_part_idx]["path"]
                            disk_worker.run_action("mount", target_p, mount_input.strip())
                            snapshot_msg = f"Mounting {target_p} to {mount_input.strip()}..."
                            snapshot_msg_timer = time.time() + 3.0
                        is_mounting = False
                        mount_input = ""
                        need_immediate_render = True
                    elif key == 'ESC':
                        is_mounting = False
                        mount_input = ""
                        need_immediate_render = True
                    elif key in ('\x7f', '\x08'):
                        mount_input = mount_input[:-1]
                        need_immediate_render = True
                    elif len(key) == 1 and key.isprintable():
                        mount_input += key
                        need_immediate_render = True
            elif is_unmounting:
                if key:
                    if key in ('\n', '\r', 'y', 'Y'):
                        if cached_partitions and selected_part_idx < len(cached_partitions):
                            target_p = cached_partitions[selected_part_idx]["path"]
                            disk_worker.run_action("unmount", target_p)
                            snapshot_msg = f"Unmounting {target_p}..."
                            snapshot_msg_timer = time.time() + 3.0
                        is_unmounting = False
                        need_immediate_render = True
                    elif key in ('n', 'N', 'ESC'):
                        is_unmounting = False
                        need_immediate_render = True
            elif is_formatting:
                if key:
                    if key in ('\n', '\r'):
                        if cached_partitions and selected_part_idx < len(cached_partitions):
                            target_p = cached_partitions[selected_part_idx]["path"]
                            fs = format_input_fs.strip().lower() or "ext4"
                            disk_worker.run_action("format", target_p, fs)
                            snapshot_msg = f"Formatting {target_p} as {fs} in background..."
                            snapshot_msg_timer = time.time() + 4.0
                        is_formatting = False
                        format_input_fs = ""
                        need_immediate_render = True
                    elif key == 'ESC':
                        is_formatting = False
                        format_input_fs = ""
                        need_immediate_render = True
                    elif key in ('\x7f', '\x08'):
                        format_input_fs = format_input_fs[:-1]
                        need_immediate_render = True
                    elif len(key) == 1 and key.isprintable():
                        format_input_fs += key
                        need_immediate_render = True

            elif key:
                if key in ('q', 'Q', '\x03'):
                    break
                elif key in ('l', 'L'):
                    new_lang = i18n.toggle_language()
                    save_app_language(new_lang)
                    snapshot_msg = f"Language switched to {new_lang.upper()}"
                    snapshot_msg_timer = time.time() + 3.0
                    need_full_clear = True
                    need_immediate_render = True
                elif key in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'):
                    new_tab = 9 if (key == '0' or key == '9') else int(key)
                    if new_tab != active_tab:
                        active_tab = new_tab
                        filter_str = ""
                        need_full_clear = True
                        need_immediate_render = True
                        sys.stdout.write("\033[2J\033[3J\033[H")
                        sys.stdout.flush()
                elif key == '\t':
                    active_tab = (active_tab % 9) + 1
                    filter_str = ""
                    need_full_clear = True
                    need_immediate_render = True
                    sys.stdout.write("\033[2J\033[3J\033[H")
                    sys.stdout.flush()
                elif key in ('v', 'V'):
                    if active_tab == 7:
                        db_subview = (db_subview + 1) % 3
                        need_full_clear = True
                        need_immediate_render = True
                elif key in ('c', 'C'):
                    if active_tab == 5 and cached_partitions and selected_part_idx < len(cached_partitions):
                        target_p = cached_partitions[selected_part_idx]["path"]
                        disk_worker.run_action("fsck", target_p)
                        snapshot_msg = f"Initiated FSCK integrity check on {target_p} in background..."
                        snapshot_msg_timer = time.time() + 4.0
                        need_immediate_render = True
                    elif active_tab == 7 and db_subview == 0:
                        is_deploying_container = True
                        need_immediate_render = True
                    else:
                        theme_idx = (theme_idx + 1) % len(THEME_KEYS)
                        save_app_theme(THEME_KEYS[theme_idx])
                        need_full_clear = True
                        need_immediate_render = True
                elif key in ('w', 'W') and active_tab in (1, 3, 6):
                    ok, msg = send_system_telemetry_webhook(force=True)
                    snapshot_msg = msg
                    snapshot_msg_timer = time.time() + 5.0
                    need_immediate_render = True
                elif key in ('t', 'T') and active_tab == 8:
                    ufw_st = get_ufw_status()
                    target_action = "disable" if ufw_st.get("active", False) else "enable"
                    ok, msg = ufw_action([target_action])
                    snapshot_msg = f"UFW {'Enabled' if target_action == 'enable' else 'Disabled'}: {msg}"
                    snapshot_msg_timer = time.time() + 4.0
                    need_immediate_render = True
                elif key in ('r', 'R') and active_tab == 8:
                    ok, msg = ufw_action(["reload"])
                    snapshot_msg = f"UFW Reloaded: {msg}"
                    snapshot_msg_timer = time.time() + 4.0
                    need_immediate_render = True
                elif key in ('t', 'T') and active_tab == 1:
                    ok, msg = send_test_webhook_alert()
                    snapshot_msg = msg
                    snapshot_msg_timer = time.time() + 5.0
                    need_immediate_render = True
                elif key in ('UP', 'PAGE_UP') or (key in ('k', 'K', 'w', 'W') and active_tab in (5, 7, 8, 9)):
                    if active_tab == 2:
                        selected_proc_idx = max(0, selected_proc_idx - (5 if key == 'PAGE_UP' else 1))
                    elif active_tab == 5:
                        selected_part_idx = max(0, selected_part_idx - (5 if key == 'PAGE_UP' else 1))
                    elif active_tab == 7:
                        if db_subview == 0:
                            selected_container_idx = max(0, selected_container_idx - (5 if key == 'PAGE_UP' else 1))
                        elif db_subview == 1:
                            selected_db_idx = max(0, selected_db_idx - (5 if key == 'PAGE_UP' else 1))
                        elif db_subview == 2:
                            selected_user_idx = max(0, selected_user_idx - (5 if key == 'PAGE_UP' else 1))
                    elif active_tab == 8:
                        selected_ufw_idx = max(0, selected_ufw_idx - (5 if key == 'PAGE_UP' else 1))
                    elif active_tab == 9:
                        selected_installer_idx = max(0, selected_installer_idx - (5 if key == 'PAGE_UP' else 1))
                    need_immediate_render = True
                elif key in ('DOWN', 'PAGE_DOWN') or (key in ('j', 'J') and active_tab in (5, 7, 8, 9)) or (key in ('s', 'S') and active_tab in (5, 8, 9)):
                    if active_tab == 2:
                        selected_proc_idx = min(max(0, len(cached_procs) - 1), selected_proc_idx + (5 if key == 'PAGE_DOWN' else 1))
                    elif active_tab == 5:
                        selected_part_idx = min(max(0, len(cached_partitions) - 1), selected_part_idx + (5 if key == 'PAGE_DOWN' else 1))
                    elif active_tab == 7:
                        if db_subview == 0:
                            selected_container_idx = min(max(0, len(cached_containers) - 1), selected_container_idx + (5 if key == 'PAGE_DOWN' else 1))
                        elif db_subview == 1:
                            selected_db_idx = min(max(0, len(cached_dbs) - 1), selected_db_idx + (5 if key == 'PAGE_DOWN' else 1))
                        elif db_subview == 2:
                            selected_user_idx = min(max(0, len(cached_users) - 1), selected_user_idx + (5 if key == 'PAGE_DOWN' else 1))
                    elif active_tab == 8:
                        selected_ufw_idx = min(max(0, len(cached_ufw_rules) - 1), selected_ufw_idx + (5 if key == 'PAGE_DOWN' else 1))
                    elif active_tab == 9:
                        selected_installer_idx = min(len(INSTALLER_ACTIONS) - 1, selected_installer_idx + (5 if key == 'PAGE_DOWN' else 1))
                    need_immediate_render = True
                elif key == 'HOME':
                    if active_tab == 2: selected_proc_idx = 0
                    elif active_tab == 5: selected_part_idx = 0
                    elif active_tab == 7:
                        if db_subview == 0: selected_container_idx = 0
                        elif db_subview == 1: selected_db_idx = 0
                        elif db_subview == 2: selected_user_idx = 0
                    elif active_tab == 8: selected_ufw_idx = 0
                    elif active_tab == 9: selected_installer_idx = 0
                    need_immediate_render = True
                elif key == 'END':
                    if active_tab == 2: selected_proc_idx = max(0, len(cached_procs) - 1)
                    elif active_tab == 5: selected_part_idx = max(0, len(cached_partitions) - 1)
                    elif active_tab == 7:
                        if db_subview == 0: selected_container_idx = max(0, len(cached_containers) - 1)
                        elif db_subview == 1: selected_db_idx = max(0, len(cached_dbs) - 1)
                        elif db_subview == 2: selected_user_idx = max(0, len(cached_users) - 1)
                    elif active_tab == 8: selected_ufw_idx = max(0, len(cached_ufw_rules) - 1)
                    elif active_tab == 9: selected_installer_idx = len(INSTALLER_ACTIONS) - 1
                    need_immediate_render = True
                elif key in ('\n', '\r', 'i', 'I'):
                    if active_tab == 9 and not installer_mgr.is_running:
                        act_num = INSTALLER_ACTIONS[selected_installer_idx][0]
                        installer_mgr.start_action(act_num, mode="install")
                        need_immediate_render = True
                elif key == '/':
                    if active_tab in (2, 8):
                        is_filtering = True
                        need_immediate_render = True
                elif key in ('k', 'K'):
                    if active_tab == 2:
                        is_killing = True
                        need_immediate_render = True
                    elif active_tab == 7 and db_subview == 2:
                        is_dropping_db_user = True
                        need_immediate_render = True
                elif key in ('m', 'M'):
                    if active_tab == 5 and cached_partitions and selected_part_idx < len(cached_partitions):
                        is_mounting = True
                        mount_input = "/mnt/"
                        need_immediate_render = True
                    elif active_tab == 2:
                        sort_by = "mem"
                        need_immediate_render = True
                elif key in ('n', 'N'):
                    if active_tab == 7:
                        if db_subview == 1:
                            is_creating_db = True
                            db_input_name = ""
                            need_immediate_render = True
                        elif db_subview == 2:
                            is_creating_db_user = True
                            db_input_user = ""
                            need_immediate_render = True
                elif key in ('u', 'U'):
                    if active_tab == 7 and db_subview == 2:
                        is_creating_db_user = True
                        db_input_user = ""
                        need_immediate_render = True
                    elif active_tab == 9 and not installer_mgr.is_running:
                        is_uninstalling_software = True
                        need_immediate_render = True
                    elif active_tab == 5 and cached_partitions and selected_part_idx < len(cached_partitions):
                        is_unmounting = True
                        need_immediate_render = True
                elif key in ('x', 'X'):
                    if active_tab == 7:
                        if db_subview == 0 and cached_containers and selected_container_idx < len(cached_containers):
                            is_deleting_container = True
                            need_immediate_render = True
                        elif db_subview == 1 and cached_dbs and selected_db_idx < len(cached_dbs):
                            is_dropping_db = True
                            need_immediate_render = True
                        elif db_subview == 2 and cached_users and selected_user_idx < len(cached_users):
                            is_dropping_db_user = True
                            need_immediate_render = True
                    elif active_tab == 9 and not installer_mgr.is_running:
                        is_uninstalling_software = True
                        need_immediate_render = True
                    elif active_tab == 5 and cached_partitions and selected_part_idx < len(cached_partitions):
                        is_unmounting = True
                        need_immediate_render = True
                elif key in ('g', 'G'):
                    if active_tab == 7 and db_subview == 2 and cached_users and selected_user_idx < len(cached_users):
                        is_granting_db_priv = True
                        db_input_grant_dbname = ""
                        need_immediate_render = True
                elif key in ('p', 'P'):
                    if active_tab == 7 and db_subview == 2 and cached_users and selected_user_idx < len(cached_users):
                        is_resetting_db_pass = True
                        db_input_new_pass = ""
                        need_immediate_render = True
                    else:
                        is_paused = not is_paused
                        need_immediate_render = True
                elif key in ('e', 'E') and active_tab == 1:
                    if stats:
                        snapshot_msg = export_snapshot_json(stats, history)
                        snapshot_msg_timer = time.time() + 4.0
                        need_immediate_render = True
                elif key in ('a', 'A'):
                    if active_tab == 8:
                        is_adding_ufw = True
                        ufw_input_rule = ""
                        need_immediate_render = True
                elif key in ('d', 'D'):
                    if active_tab == 8:
                        is_deleting_ufw = True
                        need_immediate_render = True
                    elif active_tab == 7:
                        if db_subview == 0:
                            is_deleting_container = True
                            need_immediate_render = True
                        elif db_subview == 1:
                            is_dropping_db = True
                            need_immediate_render = True
                        elif db_subview == 2:
                            is_dropping_db_user = True
                            need_immediate_render = True
                elif key in ('f', 'F'):
                    if active_tab == 5 and cached_partitions and selected_part_idx < len(cached_partitions):
                        is_formatting = True
                        format_input_fs = "ext4"
                        need_immediate_render = True
                elif key in ('+', '='):
                    refresh_rate = min(10.0, refresh_rate + 0.5)
                    need_immediate_render = True
                elif key in ('-', '_'):
                    refresh_rate = max(0.5, refresh_rate - 0.5)
                    need_immediate_render = True

            if snapshot_msg and time.time() > snapshot_msg_timer:
                snapshot_msg = None
                need_immediate_render = True

            should_refresh = (now - last_refresh_time >= refresh_rate) or need_immediate_render

            if should_refresh:
                if not is_paused or stats is None:
                    stats = get_all_device_stats(force=True)
                    history.update(stats)
                last_refresh_time = now

                if need_full_clear:
                    sys.stdout.write("\033[2J\033[3J\033[H")
                    sys.stdout.flush()
                    need_full_clear = False
                else:
                    sys.stdout.write("\033[H")
                    sys.stdout.flush()

                modal_info = None
                prompt_str = None
                if is_filtering:
                    target_name = "UFW Rules" if active_tab == 8 else "Processes"
                    modal_info = (f"FILTER {target_name.upper()}", f"Filter matching {target_name}:", filter_str, "[Enter/ESC] Confirm Filter | [Backspace] Clear")
                elif is_adding_ufw:
                    modal_info = ("ADD UFW FIREWALL RULE", "Enter rule specification (e.g. 8080/tcp, allow 22, deny 3306, limit 22/tcp):", ufw_input_rule, "[Enter] Apply Rule | [ESC] Cancel")
                elif is_deleting_ufw:
                    r_info = f"#{cached_ufw_rules[selected_ufw_idx]['num']} ({cached_ufw_rules[selected_ufw_idx]['to']})" if cached_ufw_rules and selected_ufw_idx < len(cached_ufw_rules) else ""
                    modal_info = ("DELETE UFW RULE", f"Are you sure you want to delete firewall rule {r_info}?", "", "[y/Enter] Confirm Delete | [n/ESC] Cancel")
                elif is_creating_db:
                    modal_info = ("CREATE DATABASE SCHEMA", "Enter new database schema name to create:", db_input_name, "[Enter] Create Schema | [ESC] Cancel")
                elif is_dropping_db:
                    db_name = cached_dbs[selected_db_idx]["name"] if cached_dbs and selected_db_idx < len(cached_dbs) else ""
                    modal_info = ("DROP DATABASE SCHEMA", f"Permanently drop database '{db_name}' and all tables?", "", "[y/Enter] Confirm Drop | [n/ESC] Cancel")
                elif is_creating_db_user:
                    modal_info = ("CREATE DATABASE USER", "Enter new user credentials in 'username:password' or 'user@host:pass' format:", db_input_user, "[Enter] Create User | [ESC] Cancel")
                elif is_dropping_db_user:
                    u_info = f"'{cached_users[selected_user_idx]['user']}'@'{cached_users[selected_user_idx]['host']}'" if cached_users and selected_user_idx < len(cached_users) else ""
                    modal_info = ("DROP DATABASE USER", f"Permanently remove database user {u_info}?", "", "[y/Enter] Confirm Drop | [n/ESC] Cancel")
                elif is_granting_db_priv:
                    u_name = cached_users[selected_user_idx]['user'] if cached_users and selected_user_idx < len(cached_users) else ""
                    modal_info = ("GRANT PRIVILEGES", f"Grant ALL privileges on database to user '{u_name}':", db_input_grant_dbname, "[Enter] Grant Privileges | [ESC] Cancel")
                elif is_resetting_db_pass:
                    u_name = cached_users[selected_user_idx]['user'] if cached_users and selected_user_idx < len(cached_users) else ""
                    modal_info = ("RESET PASSWORD", f"Enter new password for user '{u_name}':", db_input_new_pass, "[Enter] Set Password | [ESC] Cancel")
                elif is_deploying_container:
                    modal_info = ("DEPLOY DOCKER CONTAINER", "[1] Nginx [2] Redis [3] Postgres [4] MariaDB [5] Portainer [6] Uptime Kuma [7] AdGuard [8] Node.js", deploy_input_choice, "[1-8] Select Predefined Stack | [ESC] Cancel")
                elif is_deleting_container:
                    c_info = cached_containers[selected_container_idx]["name"] if cached_containers and selected_container_idx < len(cached_containers) else ""
                    modal_info = ("REMOVE CONTAINER", f"Force stop and delete Docker container '{c_info}'?", "", "[y/Enter] Confirm Delete | [n/ESC] Cancel")
                elif is_killing:
                    def_pid = cached_procs[selected_proc_idx]['pid'] if cached_procs and selected_proc_idx < len(cached_procs) else ""
                    modal_info = ("KILL PROCESS", f"Target PID to terminate (default selected PID: {def_pid}):", kill_input_pid or str(def_pid), "[Enter] SIGTERM (15) | [9] SIGKILL (9) | [ESC] Cancel")
                elif is_mounting:
                    p_info = cached_partitions[selected_part_idx]['path'] if cached_partitions and selected_part_idx < len(cached_partitions) else ""
                    modal_info = ("MOUNT PARTITION", f"Enter target mountpoint directory for {p_info}:", mount_input, "[Enter] Mount | [ESC] Cancel")
                elif is_unmounting:
                    p_info = cached_partitions[selected_part_idx]['path'] if cached_partitions and selected_part_idx < len(cached_partitions) else ""
                    modal_info = ("UNMOUNT PARTITION", f"Unmount partition {p_info} from filesystem?", "", "[y/Enter] Confirm Unmount | [n/ESC] Cancel")
                elif is_formatting:
                    p_info = cached_partitions[selected_part_idx]['path'] if cached_partitions and selected_part_idx < len(cached_partitions) else ""
                    modal_info = ("FORMAT PARTITION", f"Enter filesystem type to format {p_info} (ext4, vfat, xfs, btrfs, ntfs):", format_input_fs, "[Enter] Format (DATA LOSS) | [ESC] Cancel")
                elif is_uninstalling_software:
                    pkg_title = INSTALLER_ACTIONS[selected_installer_idx][1] if selected_installer_idx < len(INSTALLER_ACTIONS) else ""
                    modal_info = ("UNINSTALL PACKAGE", f"Are you sure you want to uninstall {pkg_title}?", "", "[y/Enter/u] Confirm Uninstall | [n/ESC] Cancel")

                theme_key = THEME_KEYS[theme_idx]
                cached_procs, cached_containers, cached_dbs, cached_users, cached_ufw_rules, cached_partitions = display_dashboard(
                    stats=stats,
                    history=history,
                    active_tab=active_tab,
                    sort_by=sort_by,
                    theme_key=theme_key,
                    is_paused=is_paused,
                    refresh_rate=refresh_rate,
                    snapshot_msg=snapshot_msg,
                    filter_str=filter_str,
                    selected_proc_idx=selected_proc_idx,
                    selected_container_idx=selected_container_idx,
                    selected_db_idx=selected_db_idx,
                    selected_user_idx=selected_user_idx,
                    db_subview=db_subview,
                    selected_ufw_idx=selected_ufw_idx,
                    selected_part_idx=selected_part_idx,
                    selected_installer_idx=selected_installer_idx,
                    installer_mgr=installer_mgr,
                    prompt_text=prompt_str,
                    modal_info=modal_info
                )

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?1049l\033[?25h\n")
        sys.stdout.flush()

def print_banner():
    banner = (
        "\033[38;2;0;240;255m\n"
        "  ███████╗███████╗██████╗ ██╗   ██╗███████╗██████╗ ██████╗ ███████╗ ██████╗██╗  ██╗\n"
        "  ██╔════╝██╔════╝██╔══██╗██║   ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝██║ ██╔╝\n"
        "  ███████╗█████╗  ██████╔╝██║   ██║█████╗  ██████╔╝██║  ██║█████╗  ██║     █████╔╝ \n"
        "  ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██╔══╝  ██╔══██╗██║  ██║██╔══╝  ██║     ██╔═██╗ \n"
        "  ███████║███████╗██║  ██║ ╚████╔╝ ███████╗██║  ██║██████╔╝███████╗╚██████╗██║  ██╗\n"
        "  ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝\n"
        "\033[0m"
    )
    print(banner)
    print("  Author: Pan N (Norbert) | Contact: kontakt.pan.n@gmail.com")
    print("  Repository: https://github.com/Norbertkkl/ServerDeck")
    print("  Linux Server Monitoring Dashboard & Hardware Management Suite")
    print("  ----------------------------------------------------------------------------\n")

def render_static_tab(tab_num: int, theme_name: str = "glacier_cyan"):
    if theme_name not in THEMES:
        theme_name = "glacier_cyan"
    stats = get_all_device_stats(force=True)
    history = MetricsHistory()
    history.update(stats)
    print(f"\n--- [ STATIC RENDER OF TAB {tab_num} ] ---")
    display_dashboard(
        stats=stats,
        history=history,
        active_tab=tab_num,
        sort_by="cpu",
        theme_key=theme_name,
        is_paused=True,
        refresh_rate=1.0
    )
    print(f"\n--- [ END OF TAB {tab_num} RENDER ] ---\n")

def run_diagnostics():
    print_banner()
    print("[*] Running ServerDeck System Diagnostics & Platform Verification...\n")
    checks = [
        ("Python 3 Runtime", True, sys.version.split()[0]),
        ("Linux Kernel OS", os.path.exists("/proc/version"), os.uname().release if hasattr(os, "uname") else "N/A"),
        ("Root / Sudo Privileges", os.geteuid() == 0, f"UID: {os.geteuid()}"),
        ("psutil Library", bool(sys.modules.get('psutil')), "Available"),
        ("PyYAML Library", bool(sys.modules.get('yaml')), "Available"),
        ("Docker Daemon Socket", os.path.exists("/var/run/docker.sock"), "/var/run/docker.sock"),
        ("UFW Firewall Binary", bool(os.path.exists("/usr/sbin/ufw") or os.path.exists("/usr/bin/ufw")), "Installed"),
        ("smartctl Utility", bool(os.path.exists("/usr/sbin/smartctl") or os.path.exists("/usr/bin/smartctl")), "Installed"),
        ("MariaDB / MySQL Client", bool(os.path.exists("/usr/bin/mariadb") or os.path.exists("/usr/bin/mysql")), "Installed")
    ]
    for name, ok, detail in checks:
        badge = "\033[38;2;0;255;157m[  OK  ]\033[0m" if ok else "\033[38;2;244;63;94m[ WARN ]\033[0m"
        print(f"  {badge} {name:<26} -> {detail}")
    print("\n[*] Diagnostic checks complete.")

def cli_entrypoint():
    from serverdeck.cli import main
    main()


