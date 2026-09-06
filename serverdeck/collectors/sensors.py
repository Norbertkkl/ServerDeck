import os
import glob
from typing import Any, Dict, List
from serverdeck.core.state import HAS_PSUTIL

if HAS_PSUTIL:
    import psutil

def get_thermal_sensors() -> List[Dict[str, Any]]:
    sensors = []
    if HAS_PSUTIL and hasattr(psutil, "sensors_temperatures"):
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for e in entries:
                        sensors.append({
                            "name": f"{name} {e.label or ''}".strip(),
                            "current": e.current,
                            "high": e.high or 80.0,
                            "critical": e.critical or 95.0
                        })
        except Exception:
            pass

    if not sensors:
        tz_files = glob.glob("/sys/class/thermal/thermal_zone*/temp")
        for fpath in tz_files:
            try:
                with open(fpath, "r") as f:
                    val = float(f.read().strip()) / 1000.0
                    zone_name = os.path.basename(os.path.dirname(fpath))
                    sensors.append({
                        "name": zone_name,
                        "current": val,
                        "high": 80.0,
                        "critical": 95.0
                    })
            except Exception:
                pass

    if not sensors:
        sensors.append({
            "name": "Virtual/ACPI",
            "current": 42.0,
            "high": 80.0,
            "critical": 95.0
        })
    return sensors

def get_gpu_devices() -> List[Dict[str, Any]]:
    gpus = []
    card_dirs = glob.glob("/sys/class/drm/card[0-9]")
    for cdir in card_dirs:
        try:
            name = os.path.basename(cdir)
            dev_file = os.path.join(cdir, "device", "uevent")
            driver = "drm"
            if os.path.exists(dev_file):
                with open(dev_file, "r") as f:
                    for line in f:
                        if "DRIVER=" in line:
                            driver = line.split("=", 1)[1].strip()
                            break
            gpus.append({
                "name": f"{name} ({driver})",
                "temperature": 0.0,
                "memory_used": 0,
                "memory_total": 0
            })
        except Exception:
            pass
    return gpus

