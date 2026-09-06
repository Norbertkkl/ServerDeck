#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from serverdeck.core.state import (
    BASE_DIR, DEFAULT_CONFIG_PATH, DEFAULT_BOT_CONFIG_PATH, DATA_FILE, SNAPSHOT_FILE,
    find_bin, load_json, save_json, load_app_config, save_app_language, HAS_PSUTIL, STATE_LOCK
)
from serverdeck.core.history import MetricsHistory
from serverdeck.core.watchdog import ServerDeckWatchdog
from serverdeck.core.engine import (
    display_dashboard, get_keypress, export_snapshot_json, run_monitor,
    print_banner, render_static_tab, run_diagnostics, cli_entrypoint
)
from serverdeck.collectors import (
    get_all_device_stats, get_detailed_processes, get_thermal_sensors,
    get_block_devices_and_partitions, get_physical_drives, get_smart_health,
    get_smart_device_details, get_dmi_info, get_system_summary,
    get_cpu_deep_stats, get_memory_deep_stats, get_network_deep_stats,
    get_dns_servers, get_listening_ports, get_serverdeck_services,
    get_username_from_uid, get_process_rss, get_process_summary, kill_process_by_pid
)
from serverdeck.managers import (
    get_mariadb_databases, get_mariadb_users, create_database, drop_database,
    create_db_user, drop_db_user, grant_db_privileges, reset_db_password,
    get_docker_containers, docker_container_action, docker_container_delete,
    deploy_docker_template, get_ufw_status, get_ufw_blocked_packets, ufw_action,
    partition_action, AsyncDiskWorker, send_discord_webhook, load_webhooks_config,
    send_template_webhook, send_system_telemetry_webhook, send_test_webhook_alert,
    check_service_active, get_software_hub_status, get_installer_actions, PythonInstallerManager
)
from serverdeck.tui import (
    THEMES, THEME_KEYS, hex_to_rgb, colorize, load_app_themes,
    visible_len, truncate_visible, pad_visible, format_bytes, format_uptime,
    get_term_layout, render_box_line, render_box_header, render_modal_box,
    render_box_footer, render_bar, render_area_chart, render_tab_bar,
    render_tab_1_dashboard, render_tab_2_processes, render_tab_3_network,
    render_tab_4_hardware_sensors, render_tab_5_partitions_and_smart,
    render_tab_5_kernel_memory_services, render_tab_7_db_and_docker,
    render_tab_8_ufw, render_tab_10_installer
)

if __name__ == "__main__":
    cli_entrypoint()
