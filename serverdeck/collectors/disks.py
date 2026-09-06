import os
import json
import time
import threading
import subprocess
from typing import Any, Dict, List
from serverdeck.core.state import (
    HAS_PSUTIL, find_bin, _smart_cache, _smart_details_cache, _lsblk_cache, STATE_LOCK
)

if HAS_PSUTIL:
    import psutil

def get_disk_deep_stats() -> Dict[str, Any]:
    res = {
        "read_bytes": 0,
        "write_bytes": 0,
        "read_count": 0,
        "write_count": 0,
        "partitions": []
    }
    if not HAS_PSUTIL:
        return res

    try:
        io_totals = psutil.disk_io_counters()
        if io_totals:
            res["read_bytes"] = io_totals.read_bytes
            res["write_bytes"] = io_totals.write_bytes
            res["read_count"] = io_totals.read_count
            res["write_count"] = io_totals.write_count

        parts = psutil.disk_partitions(all=False)
        for p in parts:
            if not p.fstype or p.fstype in ('squashfs', 'iso9660', 'overlay', 'tmpfs', 'devtmpfs'):
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
                res["partitions"].append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
            except (PermissionError, FileNotFoundError):
                continue
    except Exception:
        pass
    return res

def get_smart_health(device_path: str) -> Dict[str, Any]:
    res = {
        "device": device_path,
        "model": "Unknown Drive",
        "passed": True,
        "temp_c": 0,
        "power_on_hours": 0,
        "wear_pct": 0,
        "nvme": False
    }
    if not find_bin("smartctl"):
        return res

    try:
        proc = subprocess.run(
            ["smartctl", "-H", "-A", "-j", device_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1.5
        )
        if proc.stdout:
            data = json.loads(proc.stdout)
            smart_st = data.get("smart_status", {})
            res["passed"] = smart_st.get("passed", True)

            dev_info = data.get("device", {})
            model = data.get("model_name") or dev_info.get("name") or "Generic Drive"
            res["model"] = model[:20]

            temp_info = data.get("temperature", {})
            res["temp_c"] = temp_info.get("current", 0)

            power_on = data.get("power_on_time", {})
            res["power_on_hours"] = power_on.get("hours", 0)

            if "nvme_smart_health_information_log" in data:
                res["nvme"] = True
                nvme_log = data["nvme_smart_health_information_log"]
                res["wear_pct"] = nvme_log.get("percentage_used", 0)
                if not res["temp_c"]:
                    res["temp_c"] = nvme_log.get("temperature", 0)
            else:
                ata_table = data.get("ata_smart_attributes", {}).get("table", [])
                for attr in ata_table:
                    attr_id = attr.get("id")
                    if attr_id in (194, 190) and not res["temp_c"]:
                        res["temp_c"] = attr.get("raw", {}).get("value", 0)
                    elif attr_id == 9 and not res["power_on_hours"]:
                        res["power_on_hours"] = attr.get("raw", {}).get("value", 0)
    except Exception:
        pass
    return res

_smart_updating = False

def _update_smart_background():
    global _smart_updating
    try:
        drives = []
        block_dir = "/sys/block"
        if os.path.exists(block_dir):
            for bdev in os.listdir(block_dir):
                if bdev.startswith(("sd", "nvme", "vd", "hd")):
                    dev_path = f"/dev/{bdev}"
                    size_file = os.path.join(block_dir, bdev, "size")
                    size_bytes = 0
                    if os.path.exists(size_file):
                        try:
                            with open(size_file, "r") as f:
                                size_bytes = int(f.read().strip()) * 512
                        except Exception:
                            pass
                    if size_bytes > 0:
                        smart = get_smart_health(dev_path)
                        drives.append({
                            "device": dev_path,
                            "name": bdev,
                            "size_bytes": size_bytes,
                            "model": smart.get("model", bdev),
                            "passed": smart.get("passed", True),
                            "temp_c": smart.get("temp_c", 0),
                            "power_on_hours": smart.get("power_on_hours", 0),
                            "wear_pct": smart.get("wear_pct", 0),
                            "nvme": smart.get("nvme", False)
                        })
        with STATE_LOCK:
            _smart_cache["time"] = time.time()
            _smart_cache["drives"] = drives
    finally:
        _smart_updating = False

def get_physical_drives() -> List[Dict[str, Any]]:
    global _smart_cache, _smart_updating
    now = time.time()
    with STATE_LOCK:
        has_cache = bool(_smart_cache["drives"])
        is_fresh = (now - _smart_cache["time"] < 30.0)
        if has_cache and is_fresh:
            return list(_smart_cache["drives"])

    if not _smart_updating:
        _smart_updating = True
        t = threading.Thread(target=_update_smart_background, daemon=True)
        t.start()

    with STATE_LOCK:
        if _smart_cache["drives"]:
            return list(_smart_cache["drives"])

    quick_drives = []
    block_dir = "/sys/block"
    if os.path.exists(block_dir):
        try:
            for bdev in os.listdir(block_dir):
                if bdev.startswith(("sd", "nvme", "vd", "hd")):
                    dev_path = f"/dev/{bdev}"
                    size_file = os.path.join(block_dir, bdev, "size")
                    size_bytes = 0
                    if os.path.exists(size_file):
                        try:
                            with open(size_file, "r") as f:
                                size_bytes = int(f.read().strip()) * 512
                        except Exception:
                            pass
                    if size_bytes > 0:
                        quick_drives.append({
                            "device": dev_path,
                            "name": bdev,
                            "size_bytes": size_bytes,
                            "model": bdev,
                            "passed": True,
                            "temp_c": 0,
                            "power_on_hours": 0,
                            "wear_pct": 0,
                            "nvme": bdev.startswith("nvme")
                        })
        except Exception:
            pass
    return quick_drives

def get_block_devices_and_partitions(force: bool = False) -> List[Dict[str, Any]]:
    global _lsblk_cache
    now = time.time()
    with STATE_LOCK:
        if not force and (now - _lsblk_cache["time"] < 10.0) and _lsblk_cache["parts"]:
            return _lsblk_cache["parts"]

    partitions = []
    if find_bin("lsblk"):
        try:
            res = subprocess.run(
                ["lsblk", "-J", "-b", "-o", "NAME,PATH,SIZE,FSTYPE,MOUNTPOINT,TYPE,LABEL,UUID"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2.0
            )
            if res.stdout:
                data = json.loads(res.stdout)
                def parse_nodes(nodes):
                    for n in nodes:
                        p_type = n.get("type", "")
                        fstype = n.get("fstype") or ""
                        mountpoint = n.get("mountpoint") or ""
                        size = int(n.get("size", 0))
                        path = n.get("path") or f"/dev/{n.get('NAME')}"

                        used_pct = 0.0
                        used_bytes = 0
                        free_bytes = size

                        if mountpoint and HAS_PSUTIL:
                            try:
                                u = psutil.disk_usage(mountpoint)
                                used_pct = u.percent
                                used_bytes = u.used
                                free_bytes = u.free
                            except Exception:
                                pass

                        if p_type in ("part", "lvm", "crypt", "disk") and size > 0:
                            partitions.append({
                                "name": n.get("name"),
                                "path": path,
                                "type": p_type,
                                "fstype": fstype or "raw",
                                "mountpoint": mountpoint,
                                "size": size,
                                "used_bytes": used_bytes,
                                "free_bytes": free_bytes,
                                "used_pct": used_pct,
                                "label": n.get("label") or "",
                                "uuid": n.get("uuid") or ""
                            })
                        if "children" in n:
                            parse_nodes(n["children"])

                parse_nodes(data.get("blockdevices", []))
        except Exception:
            pass

    if not partitions and HAS_PSUTIL:
        try:
            for p in psutil.disk_partitions(all=False):
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    partitions.append({
                        "name": os.path.basename(p.device),
                        "path": p.device,
                        "type": "part",
                        "fstype": p.fstype,
                        "mountpoint": p.mountpoint,
                        "size": u.total,
                        "used_bytes": u.used,
                        "free_bytes": u.free,
                        "used_pct": u.percent,
                        "label": "",
                        "uuid": ""
                    })
                except Exception:
                    pass
        except Exception:
            pass

    with STATE_LOCK:
        _lsblk_cache["time"] = now
        _lsblk_cache["parts"] = partitions
    return partitions

def get_smart_device_details(dev_name: str, force: bool = False) -> Dict[str, Any]:
    global _smart_details_cache
    now = time.time()
    with STATE_LOCK:
        cached = _smart_details_cache.get(dev_name)
        if not force and cached and (now - cached.get("time", 0.0) < 30.0):
            return cached.get("data", {})

    details = {
        "device": dev_name,
        "smart_supported": False,
        "smart_enabled": False,
        "health_passed": True,
        "temperature_c": 0,
        "power_cycles": 0,
        "power_on_hours": 0,
        "wear_percentage": 0,
        "reallocated_sectors": 0,
        "error_count": 0,
        "nvme": False,
        "model": "Generic",
        "serial": "N/A"
    }

    if not find_bin("smartctl"):
        return details

    try:
        proc = subprocess.run(
            ["smartctl", "-a", "-j", dev_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2.0
        )
        if proc.stdout:
            data = json.loads(proc.stdout)
            details["model"] = data.get("model_name") or data.get("device", {}).get("name") or "Generic"
            details["serial"] = data.get("serial_number") or "N/A"

            smart_st = data.get("smart_status", {})
            details["health_passed"] = smart_st.get("passed", True)

            temp_info = data.get("temperature", {})
            details["temperature_c"] = temp_info.get("current", 0)

            power_on = data.get("power_on_time", {})
            details["power_on_hours"] = power_on.get("hours", 0)
            details["power_cycles"] = data.get("power_cycle_count", 0)

            if "nvme_smart_health_information_log" in data:
                details["nvme"] = True
                nvme_log = data["nvme_smart_health_information_log"]
                details["wear_percentage"] = nvme_log.get("percentage_used", 0)
                details["error_count"] = nvme_log.get("media_and_data_integrity_errors", 0)
                if not details["temperature_c"]:
                    details["temperature_c"] = nvme_log.get("temperature", 0)
            else:
                ata_attrs = data.get("ata_smart_attributes", {}).get("table", [])
                for attr in ata_attrs:
                    aid = attr.get("id")
                    if aid == 5:
                        details["reallocated_sectors"] = attr.get("raw", {}).get("value", 0)
                    elif aid in (194, 190) and not details["temperature_c"]:
                        details["temperature_c"] = attr.get("raw", {}).get("value", 0)
                    elif aid == 9 and not details["power_on_hours"]:
                        details["power_on_hours"] = attr.get("raw", {}).get("value", 0)
    except Exception:
        pass

    with STATE_LOCK:
        _smart_details_cache[dev_name] = {"time": now, "data": details}
    return details

