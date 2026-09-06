import time
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from serverdeck.core.state import DEFAULT_BOT_CONFIG_PATH, BASE_DIR, validate_bot_config
from serverdeck.core.i18n import i18n
from serverdeck.collectors.system import get_all_device_stats
from serverdeck.core.formatters import format_bytes, format_uptime

def send_discord_webhook(webhook_url: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not webhook_url or not webhook_url.startswith(("http://", "https://")):
        return False, "Invalid or empty Webhook URL."
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ServerDeck-Webhook-Engine/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            if resp.status in (200, 204):
                return True, "Webhook delivered successfully."
            return False, f"HTTP Error {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, f"Network error: {e}"

def load_webhooks_config() -> Dict[str, Any]:
    candidates = [
        DEFAULT_BOT_CONFIG_PATH,
        Path.home() / ".config" / "serverdeck" / "bot.yaml",
        BASE_DIR / "bot.yaml",
        BASE_DIR / "templates" / "bot.yaml",
        Path(__file__).parent.parent / "templates" / "bot.yaml"
    ]
    for c in candidates:
        if c.exists():
            try:
                import yaml
                with open(c, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        if "webhook" in data and isinstance(data["webhook"], dict):
                            merged = dict(data["webhook"])
                            for k, v in data.items():
                                if k != "webhook":
                                    merged[k] = v
                            return validate_bot_config(merged)
                        return validate_bot_config(data)
            except Exception:
                pass
    return validate_bot_config({})

def send_template_webhook(template_type: str = "system_report", extra_replacements: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    wh_cfg = load_webhooks_config()
    if not wh_cfg.get("enabled", False):
        return False, i18n.t("discord.webhook_disabled", "Discord integration is disabled in bot.yaml.")

    url = wh_cfg.get("webhook_url", "").strip()
    if not url or "YOUR_DISCORD_WEBHOOK_URL_HERE" in url:
        return False, i18n.t("discord.no_url", "No Webhook URL configured in bot.yaml.")

    stats = get_all_device_stats(force=True)
    summary = stats.get("summary", {})
    cpu = stats.get("cpu", {})
    mem = stats.get("memory", {})
    dsk = stats.get("disks", {})
    net = stats.get("network", {})

    mem_total_str = format_bytes(mem.get("total", 0))
    mem_used_str = format_bytes(mem.get("used", 0))
    dsk_root_pct = 0.0
    for p in dsk.get("partitions", []):
        if p.get("mountpoint") == "/":
            dsk_root_pct = p.get("percent", 0.0)
            break

    replacements = {
        "{hostname}": summary.get("hostname", "Linux-Server"),
        "{distro}": summary.get("distro", "Linux"),
        "{kernel}": summary.get("kernel", "N/A"),
        "{uptime}": format_uptime(summary.get("uptime", 0.0)),
        "{load_avg}": f"{summary.get('load_1', 0.0)} / {summary.get('load_5', 0.0)} / {summary.get('load_15', 0.0)}",
        "{cpu_model}": cpu.get("model", "CPU")[:24],
        "{cpu_percent}": f"{cpu.get('percent', 0.0):.1f}%",
        "{ram_percent}": f"{mem.get('percent', 0.0):.1f}%",
        "{ram_used}": mem_used_str.strip(),
        "{ram_total}": mem_total_str.strip(),
        "{disk_percent}": f"{dsk_root_pct:.1f}%",
        "{net_rx_total}": format_bytes(net.get("bytes_recv", 0)).strip(),
        "{net_tx_total}": format_bytes(net.get("bytes_sent", 0)).strip(),
        "{timestamp}": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    if extra_replacements:
        replacements.update(extra_replacements)

    template = wh_cfg.get("templates", {}).get(template_type)
    if not template:
        if template_type == "test_alert":
            template = {
                "title": "ServerDeck System Alert: {alert_metric}",
                "description": "Triggered threshold alert on host **{hostname}**.",
                "color": 15158332,
                "fields": [
                    {"name": "Metric", "value": "{alert_metric}", "inline": True},
                    {"name": "Current Value", "value": "{current_value}", "inline": True},
                    {"name": "Threshold Limit", "value": "{threshold_value}", "inline": True},
                    {"name": "Hostname", "value": "{hostname}", "inline": True},
                    {"name": "Kernel", "value": "{kernel}", "inline": True},
                    {"name": "Triggered At", "value": "{timestamp}", "inline": True}
                ],
                "footer": "ServerDeck Alert Watchdog"
            }
        else:
            template = {
                "title": "ServerDeck Telemetry Report: {hostname}",
                "description": "Real-time system telemetry and health vitals summary.",
                "color": 65535,
                "fields": [
                    {"name": "OS & Kernel", "value": "{distro} ({kernel})", "inline": False},
                    {"name": "Uptime", "value": "{uptime}", "inline": True},
                    {"name": "Load Average", "value": "{load_avg}", "inline": True},
                    {"name": "CPU Usage", "value": "{cpu_percent}", "inline": True},
                    {"name": "RAM Usage", "value": "{ram_used} / {ram_total} ({ram_percent})", "inline": True},
                    {"name": "Root Disk", "value": "{disk_percent}", "inline": True},
                    {"name": "Network RX/TX", "value": "Rx: {net_rx_total} | Tx: {net_tx_total}", "inline": True}
                ],
                "footer": "ServerDeck Telemetry Engine"
            }

    def rep(text: str) -> str:
        for k, v in replacements.items():
            text = text.replace(k, str(v))
        return text

    embed = {
        "title": rep(template.get("title", "ServerDeck")),
        "description": rep(template.get("description", "")),
        "color": template.get("color", 65535),
        "fields": [],
        "footer": {"text": rep(template.get("footer", "ServerDeck"))},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    for f in template.get("fields", []):
        embed["fields"].append({
            "name": rep(f.get("name", "")),
            "value": rep(f.get("value", "")),
            "inline": f.get("inline", True)
        })

    payload = {
        "username": wh_cfg.get("username", "ServerDeck Bot"),
        "avatar_url": wh_cfg.get("avatar_url", ""),
        "embeds": [embed]
    }
    return send_discord_webhook(url, payload)

def send_system_telemetry_webhook(force: bool = True) -> Tuple[bool, str]:
    return send_template_webhook(template_type="system_report")

def send_test_webhook_alert() -> Tuple[bool, str]:
    return send_template_webhook(template_type="test_alert", extra_replacements={
        "{alert_metric}": "Manual Test Trigger",
        "{current_value}": "99.9%",
        "{threshold_value}": "Manual Test"
    })
