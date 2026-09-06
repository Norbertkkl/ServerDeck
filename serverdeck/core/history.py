import time
from collections import deque
from typing import Any, Dict

class MetricsHistory:
    def __init__(self, history_len: int = 46):
        self.max_len = history_len
        self.cpu_history = deque([0.0] * history_len, maxlen=history_len)
        self.ram_history = deque([0.0] * history_len, maxlen=history_len)
        self.net_rx_history = deque([0.0] * history_len, maxlen=history_len)
        self.net_tx_history = deque([0.0] * history_len, maxlen=history_len)
        self.disk_read_history = deque([0.0] * history_len, maxlen=history_len)
        self.disk_write_history = deque([0.0] * history_len, maxlen=history_len)

        self.last_update_time = time.time()
        self.last_net_bytes_recv = 0
        self.last_net_bytes_sent = 0
        self.last_disk_read_bytes = 0
        self.last_disk_write_bytes = 0

        self.rx_speed = 0.0
        self.tx_speed = 0.0
        self.disk_read_speed = 0.0
        self.disk_write_speed = 0.0

    def update(self, stats: Dict[str, Any]):
        now = time.time()
        dt = max(0.1, now - self.last_update_time)

        cpu_val = float(stats.get("cpu", {}).get("percent", 0.0))
        ram_val = float(stats.get("memory", {}).get("percent", 0.0))

        self.cpu_history.append(cpu_val)
        self.ram_history.append(ram_val)

        net_stats = stats.get("network", {})
        curr_rx = net_stats.get("bytes_recv", 0)
        curr_tx = net_stats.get("bytes_sent", 0)

        if self.last_net_bytes_recv > 0 and curr_rx >= self.last_net_bytes_recv:
            self.rx_speed = (curr_rx - self.last_net_bytes_recv) / dt
            self.tx_speed = (curr_tx - self.last_net_bytes_sent) / dt
        else:
            self.rx_speed = 0.0
            self.tx_speed = 0.0

        self.last_net_bytes_recv = curr_rx
        self.last_net_bytes_sent = curr_tx
        self.net_rx_history.append(self.rx_speed)
        self.net_tx_history.append(self.tx_speed)

        disk_stats = stats.get("disks", {})
        curr_d_read = disk_stats.get("read_bytes", 0)
        curr_d_write = disk_stats.get("write_bytes", 0)

        if self.last_disk_read_bytes > 0 and curr_d_read >= self.last_disk_read_bytes:
            self.disk_read_speed = (curr_d_read - self.last_disk_read_bytes) / dt
            self.disk_write_speed = (curr_d_write - self.last_disk_write_bytes) / dt
        else:
            self.disk_read_speed = 0.0
            self.disk_write_speed = 0.0

        self.last_disk_read_bytes = curr_d_read
        self.last_disk_write_bytes = curr_d_write
        self.disk_read_history.append(self.disk_read_speed)
        self.disk_write_history.append(self.disk_write_speed)

        self.last_update_time = now

