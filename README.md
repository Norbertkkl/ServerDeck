# ServerDeck

Autonomous Linux Server Telemetry Dashboard, System Management TUI, and Discord Sentinel Daemon.

```text
  ███████╗███████╗██████╗ ██╗   ██╗███████╗██████╗ ██████╗ ███████╗ ██████╗██╗  ██╗
  ██╔════╝██╔════╝██╔══██╗██║   ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝██║ ██╔╝
  ███████╗█████╗  ██████╔╝██║   ██║█████╗  ██████╔╝██║  ██║█████╗  ██║     █████╔╝ 
  ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██╔══╝  ██╔══██╗██║  ██║██╔══╝  ██║     ██╔═██╗ 
  ███████║███████╗██║  ██║ ╚████╔╝ ███████╗██║  ██║██████╔╝███████╗╚██████╗██║  ██╗
  ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝
```

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9+-brightgreen.svg)](https://www.python.org/)
[![Node: 16+](https://img.shields.io/badge/Node-16+-green.svg)](https://nodejs.org/)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)]()

ServerDeck is a lightweight terminal monitoring suite and management platform designed for homelabs, dedicated nodes, and cloud instances (Ubuntu 22.04 / 24.04 LTS, Debian, Fedora, Arch). It features a zero-dependency ANSI TrueColor TUI, non-blocking telemetry collectors, an autonomous Discord Sentinel bot, and native systemd service integration.

---

## Key Highlights

- **Non-Blocking Telemetry Collectors**: Asynchronous SMART discovery, cached firewall querying, direct `/proc` and `/sys` parsing with sub-millisecond latency.
- **Dynamic Responsive TUI**: Auto-scaling layout adapting from 80x24 up to 120 columns without border warping.
- **Persistent Preferences**: Interactive theme switching (`c`/`C`) and bilingual localization (`l`) stored persistently in `config.yaml`.
- **Zero-Leak Secret Isolation**: Zero-dependency `.env` parser storing secrets in memory cache (`_secrets_cache`) to prevent `/proc/<pid>/environ` exposure.
- **Systemd Service Manager**: Native command-line controller (`serverdeck --service {status|start|stop|restart|logs|enable|disable}`) with graceful fallback in containerized environments.
- **Autonomous Discord Sentinel**: Live embed dashboard, customizable threshold alerts (CPU, RAM, Disks, Temperature), interactive modal actions, and slash commands.
- **Software Hub**: Integrated installer and status checker for 38 server utilities, runtimes, web servers, databases, and game server managers.

---

## Quick Start

### 1. Instant Run via NPX (Zero Installation)
Requires Node.js 16+ and Python 3:
```bash
npx serverdeck
```
Or install globally via npm:
```bash
npm install -g serverdeck
serverdeck
```

### 2. Full System Installation via Bash (Ubuntu / Debian)
Provisions isolated virtual environment (`/opt/serverdeck/venv`), system user (`serverdeck`), directory permissions, and systemd units:
```bash
curl -fsSL https://raw.githubusercontent.com/Norbertkkl/ServerDeck/main/install.sh | sudo bash -s -- --all
```

### 3. Python Package Manager (PyPI)
```bash
pip install serverdeck-cli
serverdeck
```

---

## TUI Dashboard Tabs

| Key | Tab Name | Description |
| :---: | :--- | :--- |
| `1` | **Overview** | System vitals, CPU, RAM, SWAP, root disk, network rate, webhook status |
| `2` | **Processes** | Real-time process table, memory RSS, dynamic column scaling, PID killing |
| `3` | **Network** | Physical interfaces, IP/MAC addresses, throughput, DNS resolver, listening ports |
| `4` | **Sensors** | Motherboard DMI/SMBIOS, hardware thermal zones, GPU metrics, CPU topology |
| `5` | **Disks & SMART** | Mountpoints, filesystem usage, asynchronous SMART health status |
| `6` | **Memory** | Detailed virtual memory, page buffers, caches, HugePages, core system services |
| `7` | **DB & Docker** | MariaDB/MySQL database management, Docker container statuses and lifecycle actions |
| `8` | **Firewall** | UFW status, incoming/outgoing rules, default policies, packet statistics |
| `9` | **Software Hub** | Status inspection and one-key installation of 38 server packages |

### Interactive Keyboard Shortcuts

- `1`-`9`: Jump to specific dashboard tab
- `Tab` / `Shift+Tab`: Cycle through tabs sequentially
- `l`: Switch language (English / Polish)
- `c`: Switch color theme (6 TrueColor 24-bit presets)
- `+` / `-`: Adjust refresh interval (0.5s to 5.0s)
- `w`: Dispatch instant system telemetry webhook report
- `t`: Dispatch test alert webhook
- `e`: Export telemetry JSON snapshot
- `r`: Force manual frame refresh
- `q`: Exit dashboard

---

## Command Line Interface (CLI)

```bash
# Launch interactive TUI monitor
serverdeck

# Launch autonomous Discord Sentinel bot daemon
serverdeck --bot

# Manage systemd service instances
serverdeck --service status bot
serverdeck --service restart bot
serverdeck --service logs bot

# Dump sanitized JSON telemetry snapshot to stdout
serverdeck --snapshot

# Render a single static tab frame (useful for SSH scripts and MOTD)
serverdeck -t 1 --theme glacier_cyan

# Run internal self-test diagnostics and benchmarks
serverdeck -d

# Show official banner and version
serverdeck -b
serverdeck -v
```

---

## Configuration & Secret Hierarchy

ServerDeck loads configurations following strict precedence:
1. CLI flags (`--config`, `--bot-config`, `--env-file`)
2. Environment variables and `.env` file
3. System and user YAML configuration files
4. Internal safe defaults

### Directory Hierarchy (Ubuntu FHS Standards)

- **Configuration**: `/etc/serverdeck/` (`config.yaml`, `bot.yaml`, `.env`)
  - Permissions: `750 root:serverdeck`
  - Secret files: `chmod 640`
  - Unprivileged user fallback: `~/.config/serverdeck/`
- **Runtime Data & Snapshots**: `/var/lib/serverdeck/` (`data.json`, `snapshot.json`)
  - Permissions: `770 serverdeck:serverdeck`
  - Unprivileged user fallback: `~/.local/state/serverdeck/` or `./snapshot.json`
- **System Service**: `/etc/systemd/system/serverdeck-bot.service`
  - Hardened sandbox: `User=serverdeck`, `ProtectSystem=strict`, `ProtectHome=read-only`

### Environment Variables (`.env`)

Create `.env` from the provided template:
```bash
cp .env.example .env
chmod 640 .env
```

```ini
# ServerDeck Environment Configuration
SERVERDECK_ENV=production
SERVERDECK_LOG_LEVEL=INFO

# Discord Sentinel Bot Credentials
DISCORD_BOT_TOKEN="your_bot_token_here"
DISCORD_STATUS_CHANNEL_ID="0"
DISCORD_ALERTS_CHANNEL_ID="0"

# Discord Webhook Integration
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Alert Thresholds (Percentage / Celsius)
SERVERDECK_ALERT_CPU=90.0
SERVERDECK_ALERT_RAM=90.0
SERVERDECK_ALERT_DISK=90.0
SERVERDECK_ALERT_TEMP=85.0
```

---

## Hardened Systemd Service

To enable and run the Discord bot as a secure system daemon:

```bash
sudo systemctl enable --now serverdeck-bot.service
sudo systemctl status serverdeck-bot.service
```

Or via ServerDeck CLI:
```bash
serverdeck --service enable bot
serverdeck --service start bot
serverdeck --service status bot
```

---

## Benchmarking & Performance

Run the built-in benchmark to verify telemetry collector latencies:
```bash
python3 debug.py --bench
```

Typical execution timings on low-power hardware (AMD GX-415GA / Raspberry Pi 4):
- Full Device Stats: ~11ms
- Process Table (16 rows): ~0.02ms
- MariaDB / MySQL Query: ~23ms
- Docker Container Inspection: ~1.8ms
- Physical Drives (Asynchronous SMART): ~0.01ms
- UFW Rules (Cached TTL): ~0.04ms

---

## Packaging & Publishing

### NPM Package
```bash
# Test execution locally
npx . --snapshot

# Publish to npm registry
npm publish --access public
```

### PyPI Wheel Package
```bash
# Build wheel and sdist with twine validation
bash scripts/publish.sh

# Upload to production PyPI
twine upload dist/*
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for full details.
