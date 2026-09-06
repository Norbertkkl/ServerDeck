import os
import time
import pwd
from typing import Any, Dict, List, Tuple
from serverdeck.core.state import HAS_PSUTIL, _proc_cache, _uid_cache, STATE_LOCK

if HAS_PSUTIL:
    import psutil

_PAGE_SIZE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096

def get_username_from_uid(uid: int) -> str:
    with STATE_LOCK:
        if uid in _uid_cache:
            return _uid_cache[uid]
        try:
            name = pwd.getpwuid(uid).pw_name
        except Exception:
            name = str(uid)
        _uid_cache[uid] = name
        return name

def get_process_rss(pid: int) -> int:
    statm_path = f"/proc/{pid}/statm"
    try:
        with open(statm_path, "r") as f:
            parts = f.read().split()
            if len(parts) >= 2:
                return int(parts[1]) * _PAGE_SIZE
    except Exception:
        pass
    return 0

def get_detailed_processes(sort_by: str = "cpu", limit: int = 8, filter_str: str = "", max_age: float = 1.0) -> List[Dict[str, Any]]:
    global _proc_cache
    if not HAS_PSUTIL:
        return []

    now = time.time()
    with STATE_LOCK:
        if (now - _proc_cache["time"] < max_age) and _proc_cache["procs"]:
            all_procs = _proc_cache["procs"]
        else:
            all_procs = []
            for p in psutil.process_iter(['pid', 'name', 'uids', 'cpu_percent', 'memory_percent', 'status', 'cmdline']):
                try:
                    info = p.info
                    pid = info['pid']
                    rss = get_process_rss(pid)
                    if rss == 0:
                        try:
                            rss = p.memory_info().rss
                        except Exception:
                            rss = 0

                    uids = info.get('uids')
                    uid = uids.real if uids else 0
                    user = get_username_from_uid(uid)

                    cmd = " ".join(info.get('cmdline') or [])
                    if not cmd:
                        cmd = info.get('name') or "unknown"

                    all_procs.append({
                        "pid": pid,
                        "name": info.get('name') or "unknown",
                        "user": user,
                        "cpu_percent": info.get('cpu_percent') or 0.0,
                        "memory_percent": info.get('memory_percent') or 0.0,
                        "rss": rss,
                        "status": info.get('status') or "running",
                        "command": cmd
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            _proc_cache["time"] = now
            _proc_cache["procs"] = all_procs

    if filter_str:
        f_lower = filter_str.lower()
        filtered = [
            p for p in all_procs
            if f_lower in p["name"].lower()
            or f_lower in p["command"].lower()
            or f_lower in str(p["pid"])
            or f_lower in p["user"].lower()
        ]
    else:
        filtered = all_procs

    reverse = True
    key_func = (lambda x: x["cpu_percent"]) if sort_by == "cpu" else (lambda x: x["memory_percent"])
    filtered.sort(key=key_func, reverse=reverse)
    return filtered[:limit]

def get_process_summary() -> int:
    if HAS_PSUTIL:
        try:
            return len(psutil.pids())
        except Exception:
            pass
    return len([p for p in os.listdir("/proc") if p.isdigit()]) if os.path.exists("/proc") else 0

def kill_process_by_pid(pid: int, sig: int = 15) -> Tuple[bool, str]:
    if not HAS_PSUTIL:
        return False, "psutil not available"
    try:
        p = psutil.Process(pid)
        p.send_signal(sig)
        sig_name = "SIGKILL" if sig == 9 else "SIGTERM"
        with STATE_LOCK:
            _proc_cache["time"] = 0.0
        return True, f"Sent {sig_name} to PID {pid}"
    except psutil.NoSuchProcess:
        return False, f"PID {pid} not found"
    except psutil.AccessDenied:
        return False, f"Access denied to PID {pid} (need root)"
    except Exception as e:
        return False, f"Error: {e}"

