import os
import shutil
import json
import copy
import threading
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

BASE_DIR = Path(__file__).parent.parent.parent.resolve()

def get_config_dir() -> Path:
    custom = os.environ.get("SERVERDECK_CONFIG_DIR")
    if custom:
        p = Path(custom)
        if p.exists() and os.access(p, os.R_OK):
            return p
    etc = Path("/etc/serverdeck")
    if etc.exists() and os.access(etc, os.R_OK):
        return etc
    user_conf = Path.home() / ".config" / "serverdeck"
    if user_conf.exists() and os.access(user_conf, os.R_OK):
        return user_conf
    return BASE_DIR

def get_data_dir() -> Path:
    custom = os.environ.get("SERVERDECK_DATA_DIR")
    if custom:
        p = Path(custom)
        if p.exists() and os.access(p, os.W_OK):
            return p
    var_lib = Path("/var/lib/serverdeck")
    if var_lib.exists() and os.access(var_lib, os.W_OK):
        return var_lib
    user_state = Path.home() / ".local" / "state" / "serverdeck"
    try:
        user_state.mkdir(parents=True, exist_ok=True)
        if os.access(user_state, os.W_OK):
            return user_state
    except Exception:
        pass
    return BASE_DIR

def get_snapshot_file_path() -> Path:
    data_dir = get_data_dir()
    try:
        if os.access(data_dir, os.W_OK):
            return data_dir / "snapshot.json"
    except Exception:
        pass
    try:
        cwd = Path.cwd()
        if os.access(cwd, os.W_OK):
            return cwd / "snapshot.json"
    except Exception:
        pass
    return Path.home() / "snapshot.json"

DEFAULT_CONFIG_PATH = BASE_DIR / "config.yaml"
DEFAULT_BOT_CONFIG_PATH = BASE_DIR / "bot.yaml"
DATA_FILE = BASE_DIR / "data.json"
SNAPSHOT_FILE = get_snapshot_file_path()

def parse_dotenv(content: str) -> Dict[str, str]:
    res = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        else:
            if " #" in val:
                val = val.split(" #", 1)[0].strip()
            elif "\t#" in val:
                val = val.split("\t#", 1)[0].strip()
        val = val.replace("\\n", "\n").replace("\\t", "\t")
        res[key] = val
    return res

_secrets_cache: Dict[str, str] = {}

def load_secrets_config(custom_path: Optional[Path] = None) -> Dict[str, str]:
    global _secrets_cache
    if _secrets_cache and custom_path is None:
        return _secrets_cache

    candidates = []
    if custom_path:
        candidates.append(Path(custom_path))
    env_var = os.environ.get("SERVERDECK_ENV_FILE")
    if env_var:
        candidates.append(Path(env_var))
    candidates.extend([
        Path("/etc/serverdeck/.env"),
        Path.home() / ".config" / "serverdeck" / ".env",
        BASE_DIR / ".env"
    ])

    for c in candidates:
        if c.exists() and os.access(c, os.R_OK):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    parsed = parse_dotenv(f.read())
                    if parsed:
                        _secrets_cache.update(parsed)
                        return _secrets_cache
            except Exception:
                pass
    return _secrets_cache

def get_secret(key: str, default: str = "") -> str:
    secrets = load_secrets_config()
    if key in secrets:
        return secrets[key]
    return os.environ.get(key, default)

STATE_LOCK = threading.RLock()

_bin_cache: Dict[str, Optional[str]] = {}
_proc_cache: Dict[str, Any] = {"time": 0.0, "procs": []}
_db_cache: Dict[str, Any] = {"dbs": [], "users": [], "time": 0.0}
_smart_cache: Dict[str, Any] = {"time": 0.0, "drives": []}
_smart_details_cache: Dict[str, Any] = {}
_software_hub_cache: Dict[str, Any] = {"time": 0.0, "data": {}}
_portainer_compose_cache: Dict[str, Any] = {"time": 0.0, "portainer": False, "compose": False, "compose_ver": "N/A"}
_sys_summary_cache: Dict[str, Any] = {"time": 0.0, "data": {}}
_ports_cache: Dict[str, Any] = {"time": 0.0, "ports": []}
_services_cache: Dict[str, Any] = {"time": 0.0, "data": {}}
_uid_cache: Dict[int, str] = {}
_stats_cache: Dict[str, Any] = {"time": 0.0, "stats": {}}
_lsblk_cache: Dict[str, Any] = {"time": 0.0, "parts": []}
_docker_containers_cache: Dict[str, Any] = {"time": 0.0, "containers": []}

def find_bin(name: str) -> Optional[str]:
    with STATE_LOCK:
        if name in _bin_cache:
            return _bin_cache[name]
        p = shutil.which(name)
        _bin_cache[name] = p
        return p

def load_json(file_path: Path, default: Any = None) -> Any:
    if not file_path.exists():
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(file_path: Path, data: Any, indent: int = 2) -> bool:
    try:
        temp_file = file_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
        temp_file.replace(file_path)
        return True
    except Exception:
        return False

def get_stats_snapshot() -> Dict[str, Any]:
    with STATE_LOCK:
        raw = _stats_cache.get("stats")
        if not raw:
            return {}
        try:
            return copy.deepcopy(raw)
        except Exception:
            return dict(raw)

def validate_app_config(cfg: Any) -> Dict[str, Any]:
    if not isinstance(cfg, dict):
        cfg = {}
    valid = {
        "language": cfg.get("language", "en") if cfg.get("language") in ("en", "pl") else "en",
        "active_theme": str(cfg.get("active_theme", "glacier_cyan")),
        "themes": cfg.get("themes", {}) if isinstance(cfg.get("themes"), dict) else {}
    }
    for k, v in cfg.items():
        if k not in valid:
            valid[k] = v
    return valid

def validate_bot_config(cfg: Any) -> Dict[str, Any]:
    if not isinstance(cfg, dict):
        cfg = {}
    bot_settings = cfg.get("bot_settings", {})
    if not isinstance(bot_settings, dict):
        bot_settings = {}
    allowed_users = bot_settings.get("allowed_user_ids", [])
    if not isinstance(allowed_users, list):
        allowed_users = []
    interval = bot_settings.get("live_dashboard_interval_seconds", 45)
    try:
        interval = max(5, int(interval))
    except (ValueError, TypeError):
        interval = 45

    thresholds = cfg.get("alert_thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}
    clean_thresholds = {}
    for metric, env_keys in (
        ("cpu_percent", ("SERVERDECK_ALERT_CPU", "ALERT_CPU_PERCENT")),
        ("ram_percent", ("SERVERDECK_ALERT_RAM", "ALERT_RAM_PERCENT")),
        ("disk_percent", ("SERVERDECK_ALERT_DISK", "ALERT_DISK_PERCENT")),
        ("temp_celsius", ("SERVERDECK_ALERT_TEMP", "ALERT_TEMP_CELSIUS"))
    ):
        raw_val = thresholds.get(metric)
        if raw_val is None:
            for ek in env_keys:
                sec_v = get_secret(ek, "")
                if sec_v:
                    raw_val = sec_v
                    break
        try:
            val = float(raw_val if raw_val is not None else 90.0)
            clean_thresholds[metric] = max(1.0, min(100.0, val))
        except (ValueError, TypeError):
            clean_thresholds[metric] = 90.0

    raw_wh = str(cfg.get("webhook_url", "")).strip()
    if "YOUR_DISCORD_WEBHOOK_URL_HERE" in raw_wh or raw_wh.endswith("..."):
        raw_wh = ""
    webhook_url = get_secret("DISCORD_WEBHOOK_URL", "") or raw_wh

    raw_token = str(bot_settings.get("bot_token", "")).strip()
    if "YOUR_DISCORD_BOT_TOKEN_HERE" in raw_token:
        raw_token = ""
    bot_token = get_secret("DISCORD_BOT_TOKEN", "") or raw_token

    status_channel = get_secret("DISCORD_STATUS_CHANNEL_ID", "") or bot_settings.get("status_channel_id", 0)
    alerts_channel = get_secret("DISCORD_ALERTS_CHANNEL_ID", "") or bot_settings.get("alerts_channel_id", 0)
    try:
        status_channel = int(status_channel)
    except (ValueError, TypeError):
        status_channel = 0
    try:
        alerts_channel = int(alerts_channel)
    except (ValueError, TypeError):
        alerts_channel = 0

    secret_users = get_secret("DISCORD_ALLOWED_USER_IDS", "")
    if secret_users and not allowed_users:
        for u in str(secret_users).split(","):
            u = u.strip()
            if u.isdigit():
                allowed_users.append(int(u))

    is_enabled = bool(cfg.get("enabled", False))
    if not is_enabled and (webhook_url or bot_token):
        is_enabled = True

    return {
        "enabled": is_enabled,
        "webhook_url": webhook_url,
        "bot_settings": {
            "bot_token": bot_token,
            "command_prefix": str(bot_settings.get("command_prefix", "!")),
            "enable_slash_commands": bool(bot_settings.get("enable_slash_commands", True)),
            "status_channel_id": status_channel,
            "alerts_channel_id": alerts_channel,
            "live_dashboard_interval_seconds": interval,
            "allowed_user_ids": allowed_users,
            "admin_role_ids": bot_settings.get("admin_role_ids", []) if isinstance(bot_settings.get("admin_role_ids"), list) else [],
            "username": str(bot_settings.get("username", "ServerDeck Sentinel")),
            "avatar_url": str(bot_settings.get("avatar_url", ""))
        },
        "alert_thresholds": clean_thresholds,
        "embed_templates": cfg.get("embed_templates", {}) if isinstance(cfg.get("embed_templates"), dict) else {}
    }

def load_app_config() -> Dict[str, Any]:
    candidates = [
        get_config_dir() / "config.yaml",
        DEFAULT_CONFIG_PATH,
        Path.home() / ".config" / "serverdeck" / "config.yaml",
        BASE_DIR / "templates" / "config.yaml",
        Path(__file__).parent.parent / "templates" / "config.yaml"
    ]
    for c in candidates:
        if c.exists() and os.access(c, os.R_OK):
            try:
                import yaml
                with open(c, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return validate_app_config(data)
            except Exception:
                pass
    return validate_app_config(load_json(DATA_FILE, default={}))

def get_writable_config_path() -> Path:
    candidates = [
        get_config_dir() / "config.yaml",
        Path.home() / ".config" / "serverdeck" / "config.yaml",
        BASE_DIR / "config.yaml"
    ]
    for p in candidates:
        if p.exists() and os.access(p, os.W_OK):
            return p
        if not p.exists():
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                if os.access(p.parent, os.W_OK):
                    return p
            except Exception:
                pass
    user_conf = Path.home() / ".config" / "serverdeck" / "config.yaml"
    user_conf.parent.mkdir(parents=True, exist_ok=True)
    return user_conf

def save_app_language(lang: str) -> bool:
    try:
        import yaml
        cfg = load_app_config()
        cfg["language"] = lang
        cfg_path = get_writable_config_path()
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception:
        return False

def save_app_theme(theme_key: str) -> bool:
    try:
        import yaml
        cfg = load_app_config()
        cfg["active_theme"] = theme_key
        cfg_path = get_writable_config_path()
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception:
        return False
