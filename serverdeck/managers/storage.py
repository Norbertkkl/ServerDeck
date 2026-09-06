import os
import re
import shutil
import time
import threading
import subprocess
from typing import Tuple
from serverdeck.core.state import find_bin
from serverdeck.collectors.disks import get_block_devices_and_partitions, get_smart_device_details

class AsyncDiskWorker:
    def __init__(self):
        self.is_running = False
        self.task_name = ""
        self.result_msg = ""
        self.result_timer = 0.0
        self._thread = None

    def run_action(self, action: str, dev_path: str, extra_arg: str = ""):
        if self.is_running:
            return
        self.is_running = True
        self.task_name = f"{action.upper()} on {dev_path}"
        self.result_msg = ""

        def _worker():
            try:
                ok, msg = partition_action(action, dev_path, extra_arg)
                self.result_msg = msg
                self.result_timer = time.time() + 4.0
            finally:
                self.is_running = False

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

def get_active_system_mounts() -> set[str]:
    protected_devices = set()
    critical_mountpoints = {"/", "/boot", "/boot/efi", "/etc", "/var", "/usr", "/home"}
    if os.path.exists("/proc/mounts"):
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        dev, mp = parts[0], parts[1]
                        if mp in critical_mountpoints:
                            try:
                                real_dev = os.path.realpath(dev)
                                protected_devices.add(real_dev)
                                protected_devices.add(dev)
                            except Exception:
                                protected_devices.add(dev)
        except Exception:
            pass
    return protected_devices

def partition_action(action_type: str, target: str, extra: str = "") -> Tuple[bool, str]:
    try:
        real_target = os.path.realpath(target)

        if action_type == "mount":
            mountpoint = extra.strip()
            if not mountpoint:
                return False, "No mount point provided."
            os.makedirs(mountpoint, exist_ok=True)
            res = subprocess.run(["mount", target, mountpoint], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0)
            if res.returncode == 0:
                get_block_devices_and_partitions(force=True)
                return True, f"Mounted {target} at {mountpoint}"
            return False, f"Mount error: {res.stderr.strip()}"

        elif action_type == "unmount":
            protected = get_active_system_mounts()
            if target in protected or real_target in protected or target in ("/", "/boot", "/boot/efi", "/etc", "/var"):
                return False, f"Rejected: Cannot unmount critical system partition ({target})!"
            res = subprocess.run(["umount", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0)
            if res.returncode == 0:
                get_block_devices_and_partitions(force=True)
                return True, f"Successfully unmounted {target}"
            return False, f"Unmount error: {res.stderr.strip()}"

        elif action_type == "fsck":
            res = subprocess.run(["fsck", "-n", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10.0)
            out_summary = res.stdout.strip().replace("\n", " ")[:60]
            if res.returncode in (0, 1):
                return True, f"FSCK: {out_summary}"
            return False, f"FSCK Warning ({res.returncode}): {out_summary}"

        elif action_type == "smart_test":
            if not find_bin("smartctl"):
                return False, "smartctl utility missing. Install smartmontools."
            res = subprocess.run(["smartctl", "-t", "force", "-t", "short", target], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5.0)
            out_str = res.stdout.strip()
            get_smart_device_details(target, force=True)
            if "Testing has begun" in out_str or "successful" in out_str or res.returncode == 0:
                return True, f"Started S.M.A.R.T. Short Test on {target}!"
            clean_lines = [l.strip() for l in out_str.splitlines() if l.strip() and not l.startswith("smartctl") and not l.startswith("Copyright") and not l.startswith("===")]
            msg = clean_lines[0] if clean_lines else f"Code {res.returncode}"
            return True, f"SMART: {msg[:60]}"

        elif action_type == "format":
            fstype = extra.strip().lower() or "ext4"
            protected = get_active_system_mounts()
            if target in protected or real_target in protected:
                return False, f"CRITICAL: Device {target} is actively mounted as a system partition!"

            if re.match(r'^/dev/(sd[a-z]|nvme\d+n\d+|vd[a-z]|hd[a-z])$', target):
                return False, f"CRITICAL: Refused to format raw whole disk ({target})! Format a specific partition."

            mkfs_cmd = f"mkfs.{fstype}"
            if not shutil.which(mkfs_cmd):
                return False, f"Missing format utility {mkfs_cmd}."
            res = subprocess.run([mkfs_cmd, "-F", target] if fstype == "ext4" else [mkfs_cmd, target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15.0)
            if res.returncode == 0:
                get_block_devices_and_partitions(force=True)
                return True, f"Successfully formatted {target} as {fstype}!"
            return False, f"Format error: {res.stderr.strip()}"

    except Exception as e:
        return False, f"Exception: {e}"
    return False, "Unknown partition action"

