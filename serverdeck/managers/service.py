import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from serverdeck.core.state import BASE_DIR, find_bin

SYSTEMD_DIR = Path("/etc/systemd/system")
RUN_SYSTEMD = Path("/run/systemd/system")

def is_systemd_available() -> bool:
    return RUN_SYSTEMD.exists() and bool(find_bin("systemctl"))

def get_service_unit_name(target: str = "bot") -> str:
    target_clean = target.lower().strip()
    if target_clean in ("bot", "discord", "serverdeck-bot"):
        return "serverdeck-bot.service"
    return "serverdeck-bot.service"

def run_systemctl_cmd(args: List[str]) -> Tuple[bool, str]:
    if not is_systemd_available():
        return False, "Systemd is not active on this host (Docker container, WSL1, or alternative init system)."

    cmd = ["systemctl"] + args
    is_privileged_action = any(a in ("start", "stop", "restart", "enable", "disable", "daemon-reload", "mask", "unmask") for a in args)

    if os.geteuid() != 0 and is_privileged_action:
        if find_bin("sudo"):
            cmd = ["sudo"] + cmd
        else:
            return False, f"Root privileges required for 'systemctl {' '.join(args)}'. Run with sudo."

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10.0
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode == 0:
            msg = out or f"Successfully executed: {' '.join(cmd)}"
            return True, msg
        return False, err or out or f"Command failed with exit code {proc.returncode}"
    except subprocess.TimeoutExpired:
        return False, "systemctl command timed out after 10 seconds"
    except Exception as e:
        return False, f"Execution error: {e}"

def get_service_status(target: str = "bot") -> Tuple[bool, str]:
    unit = get_service_unit_name(target)
    if not is_systemd_available():
        return False, "Systemd is not active on this system."

    try:
        proc_active = subprocess.run(
            ["systemctl", "is-active", unit],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3.0
        )
        state_str = proc_active.stdout.strip()

        proc_enabled = subprocess.run(
            ["systemctl", "is-enabled", unit],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3.0
        )
        enabled_str = proc_enabled.stdout.strip()

        is_running = (state_str == "active")
        info = f"Unit: {unit} | Status: {state_str.upper()} | Boot Auto-Start: {enabled_str.upper()}"
        return is_running, info
    except Exception as e:
        return False, f"Status check error: {e}"

def get_service_logs(target: str = "bot", lines: int = 30) -> Tuple[bool, str]:
    unit = get_service_unit_name(target)
    if not is_systemd_available():
        return False, "Systemd is not active on this host."

    if not find_bin("journalctl"):
        return False, "journalctl binary not found."

    cmd = ["journalctl", "-u", unit, "-n", str(lines), "--no-pager"]
    if os.geteuid() != 0 and find_bin("sudo"):
        cmd = ["sudo"] + cmd

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip() or f"No logs recorded yet for {unit}."
        return False, proc.stderr.strip() or "Failed to read journalctl logs."
    except Exception as e:
        return False, f"Error retrieving logs: {e}"

def install_systemd_unit(target: str = "bot") -> Tuple[bool, str]:
    if not is_systemd_available():
        return False, "Systemd is not available. Skipping service registration."

    if os.geteuid() != 0:
        return False, "Installing systemd units requires administrative privileges. Run: sudo serverdeck --service install"

    unit_name = get_service_unit_name(target)
    dest_path = SYSTEMD_DIR / unit_name

    src_candidates = [
        BASE_DIR / unit_name,
        BASE_DIR / "serverdeck" / "templates" / unit_name,
        Path(__file__).parent.parent / "templates" / unit_name
    ]

    unit_content = None
    for src in src_candidates:
        if src.exists():
            try:
                with open(src, "r", encoding="utf-8") as f:
                    unit_content = f.read()
                break
            except Exception:
                pass

    if not unit_content:
        return False, f"Unit definition file not found for {unit_name}"

    try:
        etc_dir = Path("/etc/serverdeck")
        var_dir = Path("/var/lib/serverdeck")
        etc_dir.mkdir(parents=True, exist_ok=True)
        var_dir.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(unit_content)

        subprocess.run(["systemctl", "daemon-reload"], check=True, timeout=5.0)
        subprocess.run(["systemctl", "enable", unit_name], check=True, timeout=5.0)
        return True, f"Service {unit_name} installed and enabled successfully."
    except Exception as e:
        return False, f"Failed to install unit {unit_name}: {e}"

def manage_service(action: str, target: str = "bot") -> Tuple[bool, str]:
    act = action.lower().strip()
    unit = get_service_unit_name(target)

    if act == "status":
        return get_service_status(target)
    elif act == "logs":
        return get_service_logs(target)
    elif act == "install":
        return install_systemd_unit(target)
    elif act == "start":
        return run_systemctl_cmd(["start", unit])
    elif act == "stop":
        return run_systemctl_cmd(["stop", unit])
    elif act == "restart":
        return run_systemctl_cmd(["restart", unit])
    elif act == "enable":
        return run_systemctl_cmd(["enable", unit])
    elif act == "disable":
        return run_systemctl_cmd(["disable", unit])
    else:
        return False, f"Unknown action: {action}. Available: status, start, stop, restart, enable, disable, logs, install"

