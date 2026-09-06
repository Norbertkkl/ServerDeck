import os
import glob
from typing import Any, Dict
from serverdeck.core.state import HAS_PSUTIL

if HAS_PSUTIL:
    import psutil

def get_cpu_deep_stats() -> Dict[str, Any]:
    res = {
        "percent": 0.0,
        "cores_logical": 1,
        "cores_physical": 1,
        "freq_current_mhz": 0.0,
        "freq_min_mhz": 0.0,
        "freq_max_mhz": 0.0,
        "governor": "unknown",
        "arch": "x86_64",
        "model": "Generic CPU"
    }
    if HAS_PSUTIL:
        try:
            res["percent"] = psutil.cpu_percent(interval=None)
            res["cores_logical"] = psutil.cpu_count(logical=True) or 1
            res["cores_physical"] = psutil.cpu_count(logical=False) or 1
            freq = psutil.cpu_freq()
            if freq:
                res["freq_current_mhz"] = round(freq.current, 1)
                res["freq_min_mhz"] = round(freq.min, 1)
                res["freq_max_mhz"] = round(freq.max, 1)
        except Exception:
            pass

    gov_files = glob.glob("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if gov_files:
        try:
            with open(gov_files[0], "r") as f:
                res["governor"] = f.read().strip()
        except Exception:
            pass

    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        res["model"] = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

    return res

