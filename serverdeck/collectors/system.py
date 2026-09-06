import os
import platform
import time
import subprocess
from typing import Any, Dict
from serverdeck.core.state import (
    HAS_PSUTIL, find_bin, _sys_summary_cache, _services_cache, _stats_cache, STATE_LOCK
)
from serverdeck.collectors.cpu import get_cpu_deep_stats
from serverdeck.collectors.memory import get_memory_deep_stats
from serverdeck.collectors.network import get_network_deep_stats, get_dns_servers, get_listening_ports
from serverdeck.collectors.disks import get_disk_deep_stats, get_physical_drives
from serverdeck.collectors.sensors import get_thermal_sensors, get_gpu_devices
from serverdeck.collectors.processes import get_detailed_processes, get_process_summary

if HAS_PSUTIL:
    import psutil

def get_dmi_info() -> Dict[str, str]:
    info = {
        "board_name": "Generic Linux Host",
        "board_vendor": "Linux",
        "bios_version": "N/A",
        "chassis_type": "Server"
    }
    dmi_path = "/sys/class/dmi/id"
    if os.path.exists(dmi_path):
        def read_dmi(field: str) -> str:
            p = os.path.join(dmi_path, field)
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        val = f.read().strip()
                        if val and val not in ("None", "Default string", "To be filled by O.E.M."):
                            return val
                except (PermissionError, OSError):
                    pass
            return ""

        model = read_dmi("product_name") or read_dmi("board_name")
        vendor = read_dmi("sys_vendor") or read_dmi("board_vendor")
        bios = read_dmi("bios_version")
        chassis = read_dmi("chassis_type")

        if model:
            info["board_name"] = model[:24]
        if vendor:
            info["board_vendor"] = vendor[:18]
        if bios:
            info["bios_version"] = bios[:14]
        if chassis:
            info["chassis_type"] = chassis[:12]
    else:
        if os.path.exists("/.dockerenv"):
            info["board_name"] = "Docker Container"
            info["board_vendor"] = "Docker Inc."
        elif os.path.exists("/proc/sys/fs/binfmt_misc/WSL"):
            info["board_name"] = "WSL2 Virtual"
            info["board_vendor"] = "Microsoft"

    return info

def get_system_summary() -> Dict[str, Any]:
    global _sys_summary_cache
    now = time.time()
    with STATE_LOCK:
        if (now - _sys_summary_cache["time"] < 2.0) and _sys_summary_cache["data"]:
            return _sys_summary_cache["data"]

    distro_str = "Linux"
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro_str = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass

    uptime_s = 0.0
    if os.path.exists("/proc/uptime"):
        try:
            with open("/proc/uptime", "r") as f:
                uptime_s = float(f.read().split()[0])
        except Exception:
            pass
    elif HAS_PSUTIL:
        try:
            uptime_s = time.time() - psutil.boot_time()
        except Exception:
            pass

    load_1, load_5, load_15 = 0.0, 0.0, 0.0
    try:
        load_1, load_5, load_15 = os.getloadavg()
    except Exception:
        pass

    summary = {
        "hostname": platform.node(),
        "kernel": platform.release(),
        "distro": distro_str,
        "uptime": uptime_s,
        "load_1": round(load_1, 2),
        "load_5": round(load_5, 2),
        "load_15": round(load_15, 2),
        "process_count": get_process_summary(),
        "dmi": get_dmi_info()
    }

    with STATE_LOCK:
        _sys_summary_cache["time"] = now
        _sys_summary_cache["data"] = summary
    return summary

def get_serverdeck_services() -> Dict[str, bool]:
    global _services_cache
    now = time.time()
    with STATE_LOCK:
        if (now - _services_cache["time"] < 10.0) and _services_cache["data"]:
            return _services_cache["data"]

    services = ["sshd", "docker", "mariadb", "cron", "systemd-journald", "ufw"]
    status_map = {s: False for s in services}
    if find_bin("systemctl"):
        try:
            res = subprocess.run(
                ["systemctl", "is-active"] + services,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=1.0
            )
            lines = res.stdout.strip().splitlines()
            for idx, s in enumerate(services):
                if idx < len(lines):
                    status_map[s] = (lines[idx].strip() == "active")
        except Exception:
            pass

    with STATE_LOCK:
        _services_cache["time"] = now
        _services_cache["data"] = status_map
    return status_map

def get_all_device_stats(force: bool = False) -> Dict[str, Any]:
    global _stats_cache
    now = time.time()
    with STATE_LOCK:
        if not force and (now - _stats_cache["time"] < 0.8) and _stats_cache["stats"]:
            return _stats_cache["stats"]

    cpu_stats = get_cpu_deep_stats()
    mem_stats = get_memory_deep_stats()
    net_stats = get_network_deep_stats()
    disk_stats = get_disk_deep_stats()
    summary = get_system_summary()
    drives = get_physical_drives()
    sensors = get_thermal_sensors()
    gpus = get_gpu_devices()
    procs = get_detailed_processes(limit=8)
    dns = get_dns_servers()
    ports = get_listening_ports()
    services = get_serverdeck_services()

    stats = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "cpu": cpu_stats,
        "memory": mem_stats,
        "network": net_stats,
        "disks": disk_stats,
        "physical_drives": drives,
        "sensors": sensors,
        "gpus": gpus,
        "processes": procs,
        "dns": dns,
        "listening_ports": ports,
        "services": services
    }

    with STATE_LOCK:
        _stats_cache["time"] = now
        _stats_cache["stats"] = stats
    return stats

