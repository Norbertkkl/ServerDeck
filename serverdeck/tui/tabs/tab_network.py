from typing import Any, Dict
from serverdeck.core.i18n import i18n
from serverdeck.core.history import MetricsHistory
from serverdeck.tui.theme import colorize
from serverdeck.tui.components import (
    get_term_layout, render_box_header, render_box_line, render_box_footer,
    pad_visible, format_bytes, render_area_chart
)

def render_tab_3_network(stats: Dict[str, Any], history: MetricsHistory, theme: Dict[str, Any]):
    c_border = theme.get("border", "#1e3a8a")
    c_title = theme.get("title", "#00f0ff")
    c_label = theme.get("label", "#94a3b8")
    c_val = theme.get("value", "#f0f9ff")
    c_hl = theme.get("highlight", "#38bdf8")

    w, h = get_term_layout()
    box_w = min(120, max(40, w - 2))
    inner_w = box_w - 4

    net_stats = stats.get("network", {})
    interfaces = net_stats.get("interfaces", [])
    ports = stats.get("listening_ports", [])
    dns = stats.get("dns", [])

    print(render_box_header("NETWORK INTERFACES & REAL-TIME BANDWIDTH", box_w, theme))

    tbl_hdr = f"  {'INTERFACE':<12} {'STATUS':<8} {'IPv4 ADDRESS':<18} {'MAC ADDRESS':<18} {'LINK SPEED'}"
    print(render_box_line(colorize(tbl_hdr, c_label, bold=True), box_w, theme))
    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    for iface in interfaces[:3]:
        st_badge = colorize("UP", theme.get("ok", "#00ff9d"), bold=True) if iface['is_up'] else colorize("DOWN", theme.get("bar_empty", "#1e293b"))
        spd_str = f"{iface['speed_mbps']} Mbps" if iface['speed_mbps'] > 0 else "Virtual"
        row = f"  {colorize(pad_visible(iface['name'], 12), c_hl)} {pad_visible(st_badge, 8)} {colorize(pad_visible(iface['ip'], 18), c_val)} {colorize(pad_visible(iface['mac'], 18), c_label)} {colorize(spd_str, c_val)}"
        print(render_box_line(row, box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    rx_spd = f"{format_bytes(history.rx_speed).strip()}/s"
    tx_spd = f"{format_bytes(history.tx_speed).strip()}/s"
    chart_title = f"BANDWIDTH HISTORY (↓ RX: {colorize(rx_spd, c_hl)}  ↑ TX: {colorize(tx_spd, c_title)})"
    print(render_box_line(colorize(chart_title, c_label, bold=True), box_w, theme))

    chart_w = min(inner_w - 2, 48)
    chart_lines = render_area_chart(list(history.net_rx_history), width=chart_w, height=2, color_high=theme.get("primary", "#00f0ff"), color_low=theme.get("border", "#1e3a8a"))
    for cl in chart_lines:
        print(render_box_line("  " + cl, box_w, theme))

    print(render_box_line(colorize("─" * inner_w, c_border), box_w, theme))

    dns_str = ", ".join(dns[:3]) if dns else "127.0.0.53"
    port_items = []
    for p in ports[:4]:
        port_items.append(f"{p['port']}/{p['proto']} ({p['process'][:10]})")
    p_str = ", ".join(port_items) if port_items else "none detected"
    print(render_box_line(f"• {colorize('DNS Servers:', c_label)} {colorize(dns_str, c_val)}   • {colorize('Listening Ports:', c_label)} {colorize(p_str, c_hl)}", box_w, theme))

    shortcuts = f"• Shortcuts: [w] Force Telemetry Report Webhook"
    print(render_box_line(shortcuts, box_w, theme))
    print(render_box_footer(box_w, theme))

