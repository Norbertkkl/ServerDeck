import time
import threading
from typing import Dict
from serverdeck.core.state import STATE_LOCK, get_stats_snapshot
from serverdeck.collectors.system import get_all_device_stats
from serverdeck.managers.webhook import load_webhooks_config, send_template_webhook

class ServerDeckWatchdog:
    def __init__(self, check_interval: float = 15.0):
        self.interval = check_interval
        self.running = False
        self.last_alerts: Dict[str, float] = {}
        self.cooldown = 300.0
        self._thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def run(self):
        while self.running:
            try:
                wh_cfg = load_webhooks_config()
                if wh_cfg.get("enabled", False) and wh_cfg.get("webhook_url"):
                    thresholds = wh_cfg.get("alert_thresholds", {})
                    stats = get_stats_snapshot() or get_all_device_stats(force=False)
                    now = time.time()

                    cpu_pct = stats.get("cpu", {}).get("percent", 0.0)
                    cpu_thresh = thresholds.get("cpu_percent", 90.0)
                    if cpu_pct >= cpu_thresh and (now - self.last_alerts.get("cpu", 0.0) > self.cooldown):
                        self.last_alerts["cpu"] = now
                        send_template_webhook(template_type="test_alert", extra_replacements={
                            "{alert_metric}": "CPU Utilization Alert",
                            "{current_value}": f"{cpu_pct:.1f}%",
                            "{threshold_value}": f"{cpu_thresh:.1f}%"
                        })

                    ram_pct = stats.get("memory", {}).get("percent", 0.0)
                    ram_thresh = thresholds.get("ram_percent", 90.0)
                    if ram_pct >= ram_thresh and (now - self.last_alerts.get("ram", 0.0) > self.cooldown):
                        self.last_alerts["ram"] = now
                        send_template_webhook(template_type="test_alert", extra_replacements={
                            "{alert_metric}": "RAM Consumption Alert",
                            "{current_value}": f"{ram_pct:.1f}%",
                            "{threshold_value}": f"{ram_thresh:.1f}%"
                        })

                    for p in stats.get("disks", {}).get("partitions", []):
                        if p.get("mountpoint") == "/":
                            d_pct = p.get("percent", 0.0)
                            d_thresh = thresholds.get("disk_percent", 90.0)
                            if d_pct >= d_thresh and (now - self.last_alerts.get("disk", 0.0) > self.cooldown):
                                self.last_alerts["disk"] = now
                                send_template_webhook(template_type="test_alert", extra_replacements={
                                    "{alert_metric}": "Root Filesystem Storage Alert",
                                    "{current_value}": f"{d_pct:.1f}%",
                                    "{threshold_value}": f"{d_thresh:.1f}%"
                                })
                            break
            except Exception:
                pass
            time.sleep(self.interval)

