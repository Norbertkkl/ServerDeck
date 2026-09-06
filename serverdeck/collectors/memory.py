import os
from typing import Any, Dict
from serverdeck.core.state import HAS_PSUTIL

if HAS_PSUTIL:
    import psutil

def get_memory_deep_stats() -> Dict[str, Any]:
    res = {
        "total": 0,
        "used": 0,
        "free": 0,
        "available": 0,
        "percent": 0.0,
        "buffers": 0,
        "cached": 0,
        "slab": 0,
        "dirty": 0,
        "swap_total": 0,
        "swap_used": 0,
        "swap_free": 0,
        "swap_percent": 0.0,
        "hugepages_total": 0,
        "hugepages_free": 0,
        "hugepages_size_kb": 2048
    }

    if HAS_PSUTIL:
        try:
            vm = psutil.virtual_memory()
            res["total"] = vm.total
            res["used"] = vm.used
            res["free"] = vm.free
            res["available"] = vm.available
            res["percent"] = vm.percent
            res["buffers"] = getattr(vm, "buffers", 0)
            res["cached"] = getattr(vm, "cached", 0)
            res["slab"] = getattr(vm, "slab", 0)
            sw = psutil.swap_memory()
            res["swap_total"] = sw.total
            res["swap_used"] = sw.used
            res["swap_free"] = sw.free
            res["swap_percent"] = sw.percent
        except Exception:
            pass

    if os.path.exists("/proc/meminfo"):
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v_str = parts[1].strip().split()[0]
                        if v_str.isdigit():
                            v = int(v_str) * 1024
                            if k == "Dirty":
                                res["dirty"] = v
                            elif k == "HugePages_Total":
                                res["hugepages_total"] = int(v_str)
                            elif k == "HugePages_Free":
                                res["hugepages_free"] = int(v_str)
                            elif k == "Hugepagesize":
                                res["hugepages_size_kb"] = int(v_str)
        except Exception:
            pass

    return res

