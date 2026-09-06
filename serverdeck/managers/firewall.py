import re
import time
import copy
import subprocess
from typing import Any, Dict, List, Tuple
from serverdeck.core.state import find_bin

_ufw_cache = {"time": 0.0, "data": None}

def get_ufw_status(force: bool = False) -> Dict[str, Any]:
    global _ufw_cache
    now = time.time()
    if not force and (now - _ufw_cache["time"] < 3.0) and _ufw_cache["data"] is not None:
        return copy.deepcopy(_ufw_cache["data"])

    res = {
        "installed": False,
        "active": False,
        "default_incoming": "deny",
        "default_outgoing": "allow",
        "rules": []
    }
    if not find_bin("ufw"):
        return res
    res["installed"] = True

    try:
        proc = subprocess.run(
            ["ufw", "status", "numbered"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=0.8
        )
        out = proc.stdout.strip()
        if "Status: active" in out:
            res["active"] = True

        proc_v = subprocess.run(
            ["ufw", "status", "verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=0.8
        )
        v_out = proc_v.stdout
        m_inc = re.search(r"Default:\s+(\w+)\s+\(incoming\)", v_out)
        if m_inc:
            res["default_incoming"] = m_inc.group(1).lower()
        m_out = re.search(r"(\w+)\s+\(outgoing\)", v_out)
        if m_out:
            res["default_outgoing"] = m_out.group(1).lower()

        rules = []
        for line in out.splitlines():
            line = line.strip()
            m = re.match(r"^\[\s*(\d+)\]\s+(.*?)\s+(ALLOW IN|DENY IN|ALLOW OUT|DENY OUT|ALLOW|DENY|REJECT|LIMIT)\s+(.*)$", line)
            if m:
                r_num = int(m.group(1))
                r_to = m.group(2).strip()
                r_act = m.group(3).strip()
                r_from = m.group(4).strip()
                rules.append({
                    "num": r_num,
                    "to": r_to,
                    "action": r_act,
                    "from": r_from,
                    "comment": ""
                })
        res["rules"] = rules
    except Exception:
        pass
    _ufw_cache["time"] = now
    _ufw_cache["data"] = res
    return res

def get_ufw_blocked_packets(limit: int = 6) -> List[Dict[str, str]]:
    blocked = []
    if not find_bin("journalctl"):
        return blocked
    try:
        proc = subprocess.run(
            ["journalctl", "-k", "--grep=UFW BLOCK", "-n", str(limit), "--output=cat"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1.5
        )
        for line in proc.stdout.strip().splitlines():
            src_m = re.search(r"SRC=([^\s]+)", line)
            dst_m = re.search(r"DST=([^\s]+)", line)
            proto_m = re.search(r"PROTO=([^\s]+)", line)
            dpt_m = re.search(r"DPT=([^\s]+)", line)
            if src_m and dst_m:
                blocked.append({
                    "src": src_m.group(1),
                    "dst": dst_m.group(1),
                    "proto": proto_m.group(1) if proto_m else "IP",
                    "dpt": dpt_m.group(1) if dpt_m else "?"
                })
    except Exception:
        pass
    return blocked

def ufw_action(cmd_args: List[str]) -> Tuple[bool, str]:
    if not find_bin("ufw"):
        return False, "UFW is not installed on this system."
    try:
        clean_args = [a.strip() for a in cmd_args if a.strip()]
        if not clean_args:
            return False, "Empty UFW command."

        first = clean_args[0].lower()
        if first == "enable":
            cmd = ["ufw", "--force", "enable"]
        elif first == "disable":
            cmd = ["ufw", "disable"]
        elif first == "reload":
            cmd = ["ufw", "reload"]
        elif first == "reset":
            cmd = ["ufw", "--force", "reset"]
        elif first == "delete":
            cmd = ["ufw", "--force"] + clean_args
        elif first in ("allow", "deny", "reject", "limit", "insert", "prepend", "route"):
            cmd = ["ufw"] + clean_args
        else:
            cmd = ["ufw", "allow"] + clean_args

        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=4.0
        )
        if res.returncode == 0:
            _ufw_cache["time"] = 0.0
            _ufw_cache["data"] = None
            out_str = res.stdout.strip().replace("\n", " ")
            msg = out_str if out_str else f"Executed: {' '.join(cmd)}"
            return True, f"UFW: {msg[:65]}"
        else:
            _ufw_cache["time"] = 0.0
            _ufw_cache["data"] = None
            err_str = (res.stderr.strip() or res.stdout.strip()).replace("\n", " ")
            return False, f"UFW Error: {err_str[:65]}"
    except subprocess.TimeoutExpired:
        return False, "UFW operation timed out (4s)."
    except Exception as e:
        return False, f"UFW error: {e}"

