# ServerDeck

Autonomous Linux server telemetry dashboard, system management TUI, and Discord Sentinel monitoring daemon for homelabs and production nodes.

```text
  ███████╗███████╗██████╗ ██╗   ██╗███████╗██████╗ ██████╗ ███████╗ ██████╗██╗  ██╗
  ██╔════╝██╔════╝██╔══██╗██║   ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝██║ ██╔╝
  ███████╗█████╗  ██████╔╝██║   ██║█████╗  ██████╔╝██║  ██║█████╗  ██║     █████╔╝ 
  ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██╔══╝  ██╔══██╗██║  ██║██╔══╝  ██║     ██╔═██╗ 
  ███████║███████╗██║  ██║ ╚████╔╝ ███████╗██║  ██║██████╔╝███████╗╚██████╗██║  ██╗
  ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝
```

[![NPM Version](https://img.shields.io/npm/v/serverdeck.svg?style=flat-square&color=CB3837)](https://www.npmjs.com/package/serverdeck)
[![Python Version](https://img.shields.io/badge/Python-3.9+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Node.js Version](https://img.shields.io/badge/Node.js-16+-339933.svg?style=flat-square&logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-FCC624.svg?style=flat-square&logo=linux&logoColor=black)]()

---

ServerDeck provides an all-in-one terminal console and telemetry engine built for dedicated bare-metal servers, virtual private servers (VPS), and home laboratories running Debian, Ubuntu, Fedora, or Arch Linux. It pairs an ANSI 24-bit TrueColor text user interface with asynchronous collectors for kernel metrics, disks, networking, containers, and firewall rules, while broadcasting real-time health alerts to Discord channels.

---

## Table of Contents

1. [Architectural Overview](#architectural-overview)
2. [Why the Automated Installer is the Best Choice](#why-the-automated-installer-is-the-best-choice)
3. [Installation Workflows (Ranked by Capability)](#installation-workflows-ranked-by-capability)
4. [Filesystem Hierarchy and Storage Layout](#filesystem-hierarchy-and-storage-layout)
5. [Configuration Files and Data Management](#configuration-files-and-data-management)
6. [TUI Dashboard Guide](#tui-dashboard-guide)
7. [Deep Dive into Tab 7 (Docker and Database Management)](#deep-dive-into-tab-7-docker-and-database-management)
8. [Keyboard Navigation and Shortcuts](#keyboard-navigation-and-shortcuts)
9. [Discord Sentinel Bot and Telemetry Webhooks](#discord-sentinel-bot-and-telemetry-webhooks)
10. [Systemd Service Management](#systemd-service-management)
11. [Command Line Interface Reference](#command-line-interface-reference)
12. [Project Organization](#project-organization)
13. [Troubleshooting and Diagnostic Procedures](#troubleshooting-and-diagnostic-procedures)
14. [License](#license)

---

## Architectural Overview

ServerDeck operates on a decoupled architecture separating interactive rendering from background data collection.

Hardware vitals and operational statistics are queried using direct reads from `/proc`, `/sys`, and system sockets rather than spawning heavy shell tools. Disk health tests (SMART), MariaDB catalog schemas, and Docker inspection pipelines run inside isolated background workers, preventing the interface from freezing when slow storage or network mounts are probed.

Interface elements dynamically adjust between 80-column terminal displays and wide multi-column layouts up to 120 columns without horizontal line wrapping or frame tearing. Color profiles and language settings (English and Polish) persist across reboots inside `config.yaml`. Secret tokens loaded from `.env` are held in process memory without leaking into `/proc/<pid>/environ`.

---

## Why the Automated Installer is the Best Choice

While ServerDeck can be quickly previewed via NPX or Pip, the automated bash installation script (`install.sh`) is the single most beneficial, complete, and robust installation route for any real-world Linux system.

The table below demonstrates why running the full installation script delivers functionality that package managers cannot provide:

| Capability / Architecture Layer | Automated Script (`install.sh`) | NPX (`npx serverdeck`) | Pip (`pip install`) |
| :--- | :---: | :---: | :---: |
| **Systemd 24/7 Daemon Auto-Start** | Included (Auto-configured) | Not available | Manual setup required |
| **Crash Auto-Recovery (`Restart=always`)** | Included (System-level) | Not available | Manual setup required |
| **Dedicated Service User (`serverdeck`)** | Created (`/var/lib/serverdeck`) | Runs as current user | Runs as current user |
| **Non-Root Docker Access (`docker` group)** | Auto-provisioned | Permission denied if non-root | Permission denied if non-root |
| **Hardware Sensors (`lm-sensors`, `smartctl`)** | Auto-installed via APT | Missing unless pre-installed | Missing unless pre-installed |
| **Hardened Secrets Path (`/etc/serverdeck`)** | Created (`0750` / `0640`) | Ephemeral / Home directory | Ephemeral / Home directory |
| **PEP 668 Virtual Environment** | Isolated in `/opt/serverdeck/venv` | Ephemeral `~/.local/state` | System Python risk |
| **Global Path Executable (`/usr/local/bin`)** | Available to all users | Only available if Node installed | Only in active virtualenv |
| **Homelab Software Provisioning Engine** | 16 modular full-stack targets | Terminal monitor only | Terminal monitor only |

### The Advantages of the Script in Detail

#### Zero-Privilege Escalation for Daily Monitoring
Running hardware monitors as root is an unnecessary security risk. The script provisions an unprivileged system user (`serverdeck`), creates dedicated data directories (`/var/lib/serverdeck`), and joins the user to the `docker` group. This grants the telemetry engine direct access to the Docker socket and hardware counters without requiring `sudo` for everyday dashboard sessions.

#### Uninterrupted 24/7 Discord Telemetry
NPX and pip commands stop transmitting metrics the moment you close your terminal window. The automated script deploys and activates `serverdeck-bot.service` in systemd. The Discord Sentinel daemon runs silently in the background, surviving reboots, network interruptions, and SSH disconnects.

#### Automatic Hardware Driver and Sensor Tooling
Features like SMART drive wear calculations, NVMe health metrics, and motherboard fan tachometers rely on system utilities such as `smartctl` and `sensors`. The installer automatically detects your Linux distribution and installs these utilities ahead of time, ensuring tabs 4 and 5 display live hardware metrics rather than empty cards.

#### Full Modular Homelab Stack Deployment
Beyond ServerDeck itself, the installer doubles as an automated server provisioner. Using flags or the interactive menu, administrators can stand up Docker Engine, MariaDB, Nginx with Certbot SSL, Portainer, Cockpit, WireGuard, and Pterodactyl with tuned firewall rules in a single unattended execution.

---

## Installation Workflows (Ranked by Capability)

### Method 1: The Automated Production Installer (Recommended)

This is the preferred route for bare-metal servers, home servers, and cloud instances running Ubuntu or Debian.

#### Complete Automated Stack Installation
Run the single command below to deploy ServerDeck, its background daemon, systemd integration, and all core hardware dependencies:

```bash
curl -fsSL https://raw.githubusercontent.com/Norbertkkl/ServerDeck/main/install.sh | sudo bash -s -- --all
```

#### Interactive Modular Installer
If you wish to select specific modules (such as installing Docker Engine, setting up MariaDB, or configuring UFW firewall policies selectively), execute the script without flags to open the interactive setup menu:

```bash
curl -fsSL https://raw.githubusercontent.com/Norbertkkl/ServerDeck/main/install.sh | sudo bash
```

The installer presents 16 individual provisioning targets:
1. OpenSSH & SFTP Server hardening on port 22
2. MariaDB / MySQL database engine installation and security wizard
3. Official Docker Engine and Docker Compose repository setup
4. Nginx Web Server with Certbot SSL automation
5. Apache2 Web Server with Certbot SSL automation
6. Samba SMB/CIFS Network File Sharing (`/srv/serverdeck_share`)
7. Cockpit Web Console on port 9090
8. Portainer Community Edition Docker Web UI on port 9443
9. WireGuard VPN, Tailscale, and Fail2ban security modules
10. Java 21 LTS and Node.js / NPM / PM2 runtimes
11. Rclone, BorgBackup, and Restic backup tooling
12. Prometheus Node Exporter on port 9100
13. Pterodactyl Game Server Management Panel and Wings daemon
14. System essentials, Python 3 runtime, and hardware libraries
15. UFW firewall automated port mapping and default policies
16. Full ServerDeck Stack deployment

#### Verification After Script Installation
Once the script completes, ServerDeck is available immediately from any path:

```bash
# Launch the interactive terminal console
serverdeck

# Inspect background Discord daemon status
sudo systemctl status serverdeck-bot.service
```

---

### Method 2: Zero-Install Preview via NPX (Quick Evaluation)

If you are on an unmanaged machine, lack root access, or simply want to test the TUI interface for five minutes without altering system files, use NPX:

```bash
npx serverdeck
```

Requirements:
- Node.js version 16 or newer
- Python 3.9 or newer

The NPX launcher creates a sandboxed virtual environment in `~/.local/state/serverdeck/venv_npm`, checks for dependencies, and runs the TUI directly. It does not configure background systemd services or alter system groups.

---

### Method 3: Global Package via NPM

For workstations where Node.js is already the primary package manager:

```bash
npm install -g serverdeck
serverdeck
```

To update an existing installation to the latest registry version:
```bash
npm update -g serverdeck
```

---

### Method 4: Developer Setup from Git Source

For contributors developing new collectors, designing custom themes, or testing pull requests:

1. Clone the repository:
```bash
git clone https://github.com/Norbertkkl/ServerDeck.git
cd ServerDeck
```

2. Create and activate an isolated virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install required build and runtime dependencies:
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

4. Install the package in editable mode:
```bash
pip install -e .
```

5. Initialize the environment configuration and run:
```bash
cp .env.example .env
serverdeck
```

---

### Method 5: Python Package Index (PyPI)

If you prefer using standard Python tooling without Node.js:

```bash
pip install serverdeck-cli
serverdeck
```

---

## Filesystem Hierarchy and Storage Layout

ServerDeck follows Linux Filesystem Hierarchy Standards (FHS) to isolate configuration, runtime state, binary entrypoints, and virtual environments across privileged and unprivileged execution environments.

### System Configuration Locations (`/etc/serverdeck`)

When running under root permissions or when installed via `install.sh`, all configuration assets reside inside `/etc/serverdeck`.

| File Path | Recommended Permissions | Default Owner | Operational Purpose |
| :--- | :---: | :---: | :--- |
| `/etc/serverdeck/config.yaml` | `0644` | `root:serverdeck` | Dashboard preferences, refresh intervals, active theme, and locale |
| `/etc/serverdeck/bot.yaml` | `0640` | `root:serverdeck` | Discord bot channel mappings, allowed user IDs, and command policies |
| `/etc/serverdeck/.env` | `0640` | `root:serverdeck` | Sensitive secrets, Discord bot token, webhook URL, and alert thresholds |

When running as an unprivileged user without write permissions to `/etc`, ServerDeck falls back to the user directory `~/.config/serverdeck/`.

### Persistent State and Runtime Data (`/var/lib/serverdeck`)

Telemetry snapshots, operational history, and runtime data files are saved into `/var/lib/serverdeck`.

| File Path | Recommended Permissions | Default Owner | Operational Purpose |
| :--- | :---: | :---: | :--- |
| `/var/lib/serverdeck/data.json` | `0660` | `serverdeck:serverdeck` | Historical rolling metrics for CPU, RAM, and network throughput |
| `/var/lib/serverdeck/snapshot.json` | `0660` | `serverdeck:serverdeck` | Complete sanitized telemetry dump generated on demand or export (`e`) |

If `/var/lib/serverdeck` is unavailable or read-only, ServerDeck routes state files to `~/.local/state/serverdeck/`, with a secondary fallback to the current working directory.

### Executable Binary Entrypoints

Global executable wrappers bridge Node.js and Python runtimes to ensure ServerDeck is universally accessible from any working directory.

| Binary Path | Mode | Purpose | Target Execution Script |
| :--- | :---: | :--- | :--- |
| `/usr/local/bin/serverdeck` | `0755` | Primary systemwide interactive TUI monitor | `/opt/serverdeck/venv/bin/python3 app.py` |
| `/usr/local/bin/serverdeck-bot` | `0755` | Standalone Discord Sentinel daemon | `/opt/serverdeck/venv/bin/python3 -m serverdeck.bot.main` |
| `npm bin -g`/`serverdeck` | `0755` | Global NPM wrapper launcher | `bin/serverdeck.js` |

### Python Virtual Environment Paths

To comply with PEP 668 ("externally managed environments") on modern distributions such as Ubuntu 24.04 and Debian 12, ServerDeck never pollutes system Python packages. It provisions isolated virtual environments based on the installation mechanism:

| Installation Mode | Virtual Environment Directory | Description |
| :--- | :--- | :--- |
| **System Installer (`install.sh`)** | `/opt/serverdeck/venv` | Shared production environment owned by `root:serverdeck` (`0755`) |
| **NPM / NPX Launcher (`bin/serverdeck.js`)** | `~/.local/state/serverdeck/venv_npm` | User-scoped auto-provisioned virtualenv when repo is read-only |
| **Local NPX in Repo** | `./.venv_npm` | Local workspace environment if repository directory is writable |
| **Git Source Clone** | `./.venv` | Standard developer virtual environment created via `python3 -m venv` |

### Systemd Service Unit

The automated installer deploys a hardened systemd unit file at:
```text
/etc/systemd/system/serverdeck-bot.service
```

This service runs under the unprivileged system account `serverdeck`, links `/etc/serverdeck/.env` into process memory, locks write access to system binaries via `ProtectSystem=strict`, restricts home access via `ProtectHome=read-only`, and constrains data writes exclusively to `/var/lib/serverdeck`.

---

## Configuration Files and Data Management

ServerDeck uses three configuration files located in `/etc/serverdeck` (or the repository root).

### 1. Environment Secrets Configuration (`.env`)

The `.env` file houses secrets, authentication tokens, webhook endpoints, and alerting thresholds. Create this file by copying `.env.example`:

```bash
cp .env.example .env
chmod 640 .env
```

Parameters and variable definitions:

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `SERVERDECK_ENV` | `production` | Deployment mode identifier (`production`, `development`, `testing`) |
| `SERVERDECK_CONFIG_DIR` | `/etc/serverdeck` | Custom override path for configuration files |
| `SERVERDECK_DATA_DIR` | `/var/lib/serverdeck` | Custom override path for metric history and snapshots |
| `DISCORD_BOT_TOKEN` | *Empty* | Bot application token generated in the Discord Developer Portal |
| `DISCORD_STATUS_CHANNEL_ID` | `0` | Numerical ID of the Discord channel where the live embed is pinned |
| `DISCORD_ALERTS_CHANNEL_ID` | `0` | Numerical ID of the Discord channel where alerts are dispatched |
| `DISCORD_ALLOWED_USER_IDS` | *Empty* | Comma-separated list of numerical Discord user IDs permitted to run actions |
| `DISCORD_WEBHOOK_URL` | *Empty* | Discord Webhook URL used for terminal-initiated telemetry embeds (`w` key) |
| `ALERT_CPU_PERCENT` | `90.0` | Processor utilization threshold triggering an alert notification |
| `ALERT_RAM_PERCENT` | `90.0` | System memory consumption threshold triggering an alert notification |
| `ALERT_DISK_PERCENT` | `90.0` | Root partition storage fill threshold triggering an alert notification |
| `ALERT_TEMP_CELSIUS` | `80.0` | Thermal sensor threshold triggering an alert notification |

### 2. General Dashboard Preferences (`config.yaml`)

Controls TUI appearance, timing loops, and localization defaults:

```yaml
general:
  refresh_rate: 1.0        # Screen redraw and polling interval in seconds
  theme: "dracula"         # Active TrueColor palette (dracula, glacier_cyan, monokai, cyberpunk, amber_crt, nord)
  language: "en"           # Display language (en or pl)
  log_level: "INFO"        # Logging verbosity (DEBUG, INFO, WARNING, ERROR)

collectors:
  enable_docker: true      # Inspect local Docker container daemon
  enable_smart: true       # Run asynchronous SMART queries for disk health
  enable_mariadb: true     # Inspect local MariaDB / MySQL database catalog
  enable_sensors: true     # Read temperature sensors and fan tachometers
  enable_ufw: true         # Monitor active UFW firewall rules
```

When users press `c` (Theme) or `l` (Language) inside the running dashboard, ServerDeck writes the selected preference directly back into `config.yaml` to ensure settings persist.

### 3. Discord Bot Sentinel Policy (`bot.yaml`)

Defines operational intervals and message layouts for the Discord daemon:

```yaml
bot:
  update_interval: 10      # Seconds between updates to the live pinned status embed
  alert_cooldown: 300      # Seconds before repeating an unresolved threshold alert
  embed_color: "0x00f0ff"  # Hex color of the live Discord embed border
  enable_modal_actions: true
```

---

## TUI Dashboard Guide

Press number keys `1` through `9` on the keyboard to switch between cards.

| Tab | Name | Primary Metrics | Controls and Capabilities |
| :---: | :--- | :--- | :--- |
| **`1`** | **Overview** | CPU percentage, RAM and SWAP utilization, root disk fill, bandwidth rates | Live webhook indicator, instant snapshot export |
| **`2`** | **Processes** | PID, process name, owner, CPU percent, memory RSS, system uptime | Dynamic sorting by CPU or RAM (`s`), process termination (`k`) |
| **`3`** | **Network** | Physical and virtual adapters, IP and MAC addresses, RX and TX speeds | DNS resolver configuration, listening TCP and UDP sockets |
| **`4`** | **Sensors** | Core package temperatures, ACPI zones, fan tachometers | Dedicated GPU stats for NVIDIA, AMD, and Intel hardware |
| **`5`** | **Disks and SMART** | Mountpoints, filesystem types, storage capacity, partition table | Non-blocking SMART health checks (`t`), partition unmounting (`u`) |
| **`6`** | **Memory** | Virtual memory breakdown, kernel slab, buffers, cache, Dirty pages | HugePages allocation, core systemd service health |
| **`7`** | **DB and Docker** | MariaDB and MySQL catalogs, user accounts, running container states | Container deployment, database creation, user privilege control |
| **`8`** | **Firewall** | UFW operational status, default policies, rule numbering | Interactive rule creation (`a`), rule deletion (`d`) |
| **`9`** | **Software Hub** | Inspection and provisioning of 38 server utilities and engines | One-key deployment (`Enter`), package uninstallation (`u`) |

---

## Deep Dive into Tab 7 (Docker and Database Management)

Tab 7 houses three integrated subviews designed for homelab infrastructure. Press the `Tab` key to cycle sequentially between subviews.

```text
╭──[ DOCKER CONTAINERS & MARIADB MANAGEMENT ]────────────────────────────────╮
│ • Subview: ▌►Docker Containers◄▐ | DB Schemas | User Accounts  [Tab]       │
```

### Subview 0: Docker Containers

This view lists all active containers along with their image tags, current operational states, and exposed network ports.

Pressing `n` opens a preconfigured application deployment modal offering ready-to-run stacks such as Nginx, Redis, PostgreSQL, MariaDB, Portainer, Uptime Kuma, AdGuard Home, or Node.js. Pressing `s` starts or stops the selected container, `r` triggers a restart, and `d` removes the container.

### Subview 1: Database Schemas (MariaDB and MySQL)

This view queries `information_schema.schemata` with a left join against table statistics, ensuring newly initialized databases with zero tables remain fully visible alongside existing databases.

Pressing `n` activates the schema creation modal. Type the desired database identifier and press `Enter` to commit. ServerDeck sanitizes the input against SQL injection, executes `CREATE DATABASE`, flushes system privileges, and immediately refreshes the catalog table. Pressing `d` safely drops the selected database while preventing accidental deletion of internal system schemas such as `mysql`, `sys`, and `information_schema`.

### Subview 2: Database User Accounts

This view exposes local and remote database accounts, connection host constraints, authentication flags, and system privileges.

Pressing `n` opens the user creation dialog accepting input formatted as `username:password` or `user@host:password`. Pressing `p` resets credentials for the highlighted user account. Pressing `g` assigns all privileges on a specified database to that account. Pressing `d` drops the selected user while protecting local root accounts.

---

## Keyboard Navigation and Shortcuts

### Global Navigation Keys

| Key | Purpose |
| :--- | :--- |
| **`1` – `9`** | Direct navigation to the specified dashboard tab |
| **`Tab`** | Advance to the next subview on Tab 7, or cycle to the next tab |
| **`Shift+Tab`** | Return to the preceding tab or subview |
| **`↑` / `↓`** | Move line cursor through tables with zero redraw latency |
| **`PageUp` / `PageDown`** | Scroll tables vertically by 5 entries |
| **`Home` / `End`** | Jump directly to the top or bottom of the active list |
| **`c` / `C`** | Cycle through the 6 TrueColor terminal themes |
| **`l` / `L`** | Toggle interface language between English and Polish |
| **`+` / `-`** | Adjust polling interval between 0.5s and 5.0s |
| **`p`** | Pause or resume live screen updating |
| **`w`** | Transmit an immediate system telemetry embed to the Discord webhook |
| **`t`** | Transmit a synthetic alert embed to verify webhook connectivity |
| **`e`** | Write a complete JSON snapshot to `snapshot.json` |
| **`q`** / **`Ctrl+C`** | Safely exit the dashboard and restore terminal states |

### Tab-Specific Action Keys

| Context | Key | Action Performed |
| :--- | :---: | :--- |
| **Tab 2 (Processes)** | `s` | Toggle sorting priority between CPU and Memory RSS |
| **Tab 2 (Processes)** | `/` | Open live search filter to isolate processes by name |
| **Tab 2 (Processes)** | `k` | Open termination prompt to issue SIGTERM or SIGKILL by PID |
| **Tab 5 (Disks)** | `t` | Run an asynchronous SMART diagnostics inquiry |
| **Tab 5 (Disks)** | `k` | Trigger a filesystem consistency check on unmounted partitions |
| **Tab 5 (Disks)** | `u` | Unmount the highlighted storage volume |
| **Tab 7 (Docker)** | `n` | Open template deployment modal for popular container stacks |
| **Tab 7 (Docker)** | `s` | Toggle container operational state between start and stop |
| **Tab 7 (Docker)** | `r` | Restart the selected Docker container |
| **Tab 7 (Docker)** | `d` | Force-stop and remove the highlighted container |
| **Tab 7 (DB Schemas)** | `n` | Open schema creation modal |
| **Tab 7 (DB Schemas)** | `d` | Drop the highlighted database schema |
| **Tab 7 (DB Users)** | `n` | Create a new database user account with optional credentials |
| **Tab 7 (DB Users)** | `p` | Reset password for the selected database user |
| **Tab 7 (DB Users)** | `g` | Grant database privileges to the highlighted user |
| **Tab 7 (DB Users)** | `d` | Drop the selected database account |
| **Tab 8 (Firewall)** | `a` | Add a new UFW firewall rule |
| **Tab 8 (Firewall)** | `d` | Remove the selected firewall rule by index |
| **Tab 9 (Software)** | `Enter` | Install or update the selected software package |
| **Tab 9 (Software)** | `r` | Restart the service associated with the package |
| **Tab 9 (Software)** | `u` | Uninstall the highlighted software component |

---

## Discord Sentinel Bot and Telemetry Webhooks

ServerDeck includes a telemetry daemon that monitors operational thresholds and maintains an embed dashboard inside designated Discord channels.

### Starting the Bot Daemon

Run the bot directly inside an interactive shell:
```bash
serverdeck --bot
```

When installed as a system service, start the daemon using the CLI:
```bash
serverdeck --service start bot
serverdeck --service logs bot
```

---

## Systemd Service Management

The CLI provides built-in control over background units without requiring raw systemctl syntax.

```bash
# Display service status
serverdeck --service status bot

# Launch service instance
serverdeck --service start bot

# Restart running instance
serverdeck --service restart bot

# Stream live output journals
serverdeck --service logs bot

# Enable autostart on system boot
serverdeck --service enable bot

# Disable system boot autostart
serverdeck --service disable bot
```

Standard systemd administration commands remain fully supported on the host:
```bash
sudo systemctl status serverdeck-bot.service
sudo journalctl -u serverdeck-bot.service -f
```

---

## Command Line Interface Reference

```text
Usage: serverdeck [OPTIONS]

Options:
  --bot                 Start the standalone Discord Sentinel telemetry daemon
  --service <ACTION> <TARGET>
                        Manage systemd services (status|start|stop|restart|logs|enable|disable)
  --snapshot            Export a sanitized JSON telemetry snapshot to standard output
  -t, --tab <1-9>       Render a single static frame of the specified tab and exit
  --theme <NAME>        Force a color theme (dracula, glacier_cyan, monokai, cyberpunk, amber_crt, nord)
  -d, --diagnostics     Execute internal collector tests and benchmarking suites
  -b, --banner          Print the ASCII brand logo and version metadata
  -v, --version         Print package version and exit
  -h, --help            Print usage instructions and command options
```

---

## Project Organization

```text
ServerDeck/
├── bin/
│   └── serverdeck.js         # Node.js wrapper and NPX runner
├── serverdeck/
│   ├── app.py                # Main application dispatch point
│   ├── cli.py                # Argument parsing and subcommands
│   ├── bot/
│   │   └── main.py           # Discord Sentinel client implementation
│   ├── collectors/           # Telemetry metrics collection modules
│   │   ├── cpu.py            # Processor load, utilization, frequency
│   │   ├── disks.py          # Storage mounts, I/O rates, SMART queries
│   │   ├── memory.py         # Memory consumption, slab, swap, caches
│   │   ├── network.py        # Adapter bandwidth, packets, open ports
│   │   ├── processes.py      # Process list, resource consumption, PIDs
│   │   ├── sensors.py        # Thermal probes, fans, GPU telemetry
│   │   └── system.py         # Hostname, architecture, kernel, uptime
│   ├── core/
│   │   ├── engine.py         # TUI event loop, terminal state, keystroke handling
│   │   ├── i18n.py           # Bilingual translation engine (PL/EN)
│   │   └── state.py          # Configuration caching and secret management
│   ├── managers/             # System interaction modules
│   │   ├── database.py       # MariaDB and MySQL schema and user operations
│   │   ├── docker.py         # Docker container inspection and lifecycle
│   │   ├── firewall.py       # UFW firewall query and rule execution
│   │   ├── installer.py      # Software Hub engine for package management
│   │   └── service.py        # Systemd unit operations and elevation
│   └── tui/
│       ├── components.py     # ANSI boxes, progress meters, modal views
│       ├── theme.py          # 24-bit TrueColor color palette specifications
│       └── tabs/             # Tab 1 through Tab 9 layout implementations
├── package.json              # NPM package specification
├── requirements.txt          # Python runtime requirements
├── install.sh                # Linux installer script
└── README.md                 # Project documentation
```

---

## Troubleshooting and Diagnostic Procedures

### MariaDB Connection and Schema Visibility

When newly created databases do not display, verify that the database server daemon is running on the host:
```bash
sudo systemctl status mariadb
# or
sudo service mariadb status
```

If the database service is stopped, start it before querying schemas:
```bash
sudo systemctl start mariadb
```

ServerDeck connects to MariaDB using the local UNIX socket (`/run/mysqld/mysqld.sock`). Newly generated empty schemas with zero tables are tracked through `information_schema.schemata` and appear in the list immediately after creation.

Ensure you switch to the **DB Schemas** subview by pressing `Tab` prior to pressing `n` to create a database. Pressing `n` on the default Docker subview will open the container deployment dialog instead.

### Administrator Privileges for System Modals

Modifying UFW firewall rules, formatting block devices, mounting storage, and installing packages via the Software Hub require administrative elevation. Launch the program as root or prefix the command with sudo:
```bash
sudo serverdeck
```

### Preference Persistence

Language and theme settings selected with `l` and `c` are written to `/etc/serverdeck/config.yaml` when running with administrative permissions, or fall back to `~/.config/serverdeck/config.yaml` for standard user sessions. If modifications do not persist across reboots, verify write permissions on the corresponding configuration path.

---

## License

ServerDeck is released under the **MIT License**. Refer to the [LICENSE](LICENSE) file for complete terms.
Author: Norbert ([@Norbertkkl](https://github.com/Norbertkkl)).
