import os
import time
from typing import Any, Dict, List
from serverdeck.core.state import HAS_PSUTIL, _ports_cache, STATE_LOCK

if HAS_PSUTIL:
    import psutil

def get_network_deep_stats() -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "bytes_recv": 0,
        "bytes_sent": 0,
        "packets_recv": 0,
        "packets_sent": 0,
        "interfaces": []
    }
    if not HAS_PSUTIL:
        return res

    try:
        io_totals = psutil.net_io_counters()
        res["bytes_recv"] = io_totals.bytes_recv
        res["bytes_sent"] = io_totals.bytes_sent
        res["packets_recv"] = io_totals.packets_recv
        res["packets_sent"] = io_totals.packets_sent

        if_addrs = psutil.net_if_addrs()
        if_stats = psutil.net_if_stats()
        if_io = psutil.net_io_counters(pernic=True)

        for if_name, addrs in if_addrs.items():
            st = if_stats.get(if_name)
            is_up = st.isup if st else False
            speed = st.speed if st else 0

            ip_v4 = "N/A"
            mac = "N/A"
            for a in addrs:
                if str(a.family) == "AddressFamily.AF_INET" or a.family == 2:
                    ip_v4 = a.address
                elif str(a.family) == "AddressFamily.AF_PACKET" or a.family == 17:
                    mac = a.address

            io_nic = if_io.get(if_name)
            rx_b = io_nic.bytes_recv if io_nic else 0
            tx_b = io_nic.bytes_sent if io_nic else 0

            res["interfaces"].append({
                "name": if_name,
                "ip": ip_v4,
                "mac": mac,
                "is_up": is_up,
                "speed_mbps": speed,
                "bytes_recv": rx_b,
                "bytes_sent": tx_b
            })
    except Exception:
        pass
    return res

def get_dns_servers() -> List[str]:
    dns = []
    if os.path.exists("/etc/resolv.conf"):
        try:
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("nameserver"):
                        parts = line.split()
                        if len(parts) >= 2:
                            dns.append(parts[1])
        except Exception:
            pass
    return dns or ["127.0.0.53"]

_pid_name_cache: Dict[int, str] = {}

def _resolve_pid_name(pid: int) -> str:
    if not pid:
        return "System"
    if pid in _pid_name_cache:
        return _pid_name_cache[pid]
    name = f"PID:{pid}"
    comm_path = f"/proc/{pid}/comm"
    if os.path.exists(comm_path):
        try:
            with open(comm_path, "r", encoding="utf-8", errors="ignore") as f:
                val = f.read().strip()
                if val:
                    name = val
        except Exception:
            pass
    elif HAS_PSUTIL:
        try:
            name = psutil.Process(pid).name()
        except Exception:
            pass
    if len(_pid_name_cache) > 200:
        _pid_name_cache.clear()
    _pid_name_cache[pid] = name
    return name

def get_listening_ports() -> List[Dict[str, Any]]:
    global _ports_cache
    now = time.time()
    with STATE_LOCK:
        if (now - _ports_cache["time"] < 5.0) and _ports_cache["ports"]:
            return _ports_cache["ports"]

    ports = []
    if HAS_PSUTIL:
        try:
            conns = psutil.net_connections(kind='tcp')
            seen = set()
            for c in conns:
                if c.status == psutil.CONN_LISTEN and c.laddr:
                    port = c.laddr.port
                    ip = c.laddr.ip
                    key = (ip, port)
                    if key not in seen:
                        seen.add(key)
                        proc_name = _resolve_pid_name(c.pid or 0)
                        ports.append({
                            "port": port,
                            "ip": ip,
                            "proto": "tcp",
                            "process": proc_name,
                            "pid": c.pid or 0
                        })
        except Exception:
            pass

    ports.sort(key=lambda x: x["port"])
    with STATE_LOCK:
        _ports_cache["time"] = now
        _ports_cache["ports"] = ports
    return ports

