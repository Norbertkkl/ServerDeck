from typing import Any, Dict
from serverdeck.core.i18n import i18n
from serverdeck.core.history import MetricsHistory
from serverdeck.tui.theme import colorize
from serverdeck.tui.components import (
    get_term_layout, render_box_header, render_box_line, render_box_footer,
    render_bar, pad_visible, format_bytes, format_uptime
)
from serverdeck.managers.webhook import load_webhooks_config

def render_tab_1_dashboard(stats: Dict[str, Any], history: MetricsHistory, theme: Dict[str, Any]):
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    w, h = get_term_layout()
    box_w = min(120, max(40, w - 2))
    inner_w = box_w - 4

    summary = stats.get("summary", {})
    cpu = stats.get("cpu", {})
    mem = stats.get("memory", {})
    dsk = stats.get("disks", {})
    net = stats.get("network", {}).get("interfaces", [])

    dmi = summary.get("dmi", {})
    host_str = summary.get("hostname", "localhost")
    board_str = dmi.get("board_name", "Linux Host")
    header_title = f"{board_str} ({host_str})"
    print(render_box_header(header_title, box_w, theme))

    distro_str = summary.get("distro", "Linux")
    kernel_str = summary.get("kernel", "N/A")
    uptime_str = format_uptime(summary.get("uptime", 0))
    cpu_arch = cpu.get("arch", "x86_64")
    threads_str = f"{cpu.get('cores_logical', 1)} threads"
    procs_str = f"{summary.get('process_count', 0)} procs"

    l1 = f"• {colorize('OS:', c_label)} {colorize(distro_str, c_val)}   • {colorize('Kernel:', c_label)} {colorize(kernel_str, c_val)}   • {colorize('Uptime:', c_label)} {colorize(uptime_str, c_hl)}"
    l2 = f"• {colorize('CPU Info:', c_label)} {colorize(cpu.get('model', 'CPU')[:28], c_val)} ({cpu_arch}, {threads_str}, {procs_str})"
    print(render_box_line(l1, box_w, theme))
    print(render_box_line(l2, box_w, theme))

    load_str = f"{summary.get('load_1', 0.0):.2f}, {summary.get('load_5', 0.0):.2f}, {summary.get('load_15', 0.0):.2f}"
    l3 = f"• {colorize('Load Average:', c_label)} {colorize(load_str, c_hl)}"
    print(render_box_line(l3, box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    cpu_pct = cpu.get("percent", 0.0)
    ram_pct = mem.get("percent", 0.0)
    swap_pct = mem.get("swap_percent", 0.0)
    root_pct = 0.0
    for p in dsk.get("partitions", []):
        if p.get("mountpoint") == "/":
            root_pct = p.get("percent", 0.0)
            break

    c_bar = render_bar(cpu_pct, 14, theme)
    r_bar = render_bar(ram_pct, 14, theme)
    s_bar = render_bar(swap_pct, 14, theme)
    d_bar = render_bar(root_pct, 14, theme)

    ram_used = format_bytes(mem.get("used", 0)).strip()
    ram_tot = format_bytes(mem.get("total", 0)).strip()

    row_bars_1 = f"CPU:  {c_bar}    RAM:  {r_bar} ({ram_used}/{ram_tot})"
    row_bars_2 = f"SWAP: {s_bar}    DISK: {d_bar} (Root /)"
    print(render_box_line(row_bars_1, box_w, theme))
    print(render_box_line(row_bars_2, box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    rx_spd = f"{format_bytes(history.rx_speed).strip()}/s"
    tx_spd = f"{format_bytes(history.tx_speed).strip()}/s"
    primary_ip = net[0].get('ip', 'N/A') if net else '127.0.0.1'
    primary_if = net[0].get('name', 'eth0') if net else 'lo'
    net_txt = f"Net: ↓ {colorize(rx_spd, c_hl)}  ↑ {colorize(tx_spd, c_hl)}"
    ip_txt = f"Interface: {colorize(primary_if, c_title)} (IP: {colorize(primary_ip, c_val)})"
    print(render_box_line(f"{pad_visible(net_txt, 32)} {ip_txt}", box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    wh_cfg = load_webhooks_config()
    wh_url = wh_cfg.get("webhook_url", "").strip()
    wh_enabled = wh_cfg.get("enabled", False)
    if wh_url and wh_enabled:
        wh_badge = colorize("[ ACTIVE ]", theme.get("ok", "#00ff9d"), bold=True)
    elif wh_url:
        wh_badge = colorize("[ CONFIGURED / OFF ]", theme.get("warn", "#f59e0b"))
    else:
        wh_badge = colorize("[ NOT CONFIGURED ]", theme.get("bar_empty", "#1e293b"))

    url_disp = (wh_url[:28] + "...") if len(wh_url) > 28 else (wh_url or "bot.yaml")
    wh_line = f"• {colorize('Discord Webhook:', c_label)} {wh_badge} {colorize(url_disp, c_val)}  • {colorize('Config:', c_label)} {colorize('bot.yaml', c_hl)}"
    print(render_box_line(wh_line, box_w, theme))

    shortcuts = f"• {colorize('Shortcuts:', c_label)} {colorize('[w]', c_hl)} Telemetry Report | {colorize('[t]', c_hl)} Test Alert | {colorize('[e]', c_hl)} Export JSON"
    print(render_box_line(shortcuts, box_w, theme))
    print(render_box_footer(box_w, theme))

