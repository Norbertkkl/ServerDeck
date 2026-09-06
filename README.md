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
2. [Installation and Launch Methods](#installation-and-launch-methods)
3. [TUI Dashboard Guide](#tui-dashboard-guide)
4. [Deep Dive into Tab 7 (Docker and Database Management)](#deep-dive-into-tab-7-docker-and-database-management)
5. [Keyboard Navigation and Shortcuts](#keyboard-navigation-and-shortcuts)
6. [Discord Sentinel Bot and Telemetry Webhooks](#discord-sentinel-bot-and-telemetry-webhooks)
7. [Systemd Service Management](#systemd-service-management)
8. [Command Line Interface Reference](#command-line-interface-reference)
9. [Project Organization](#project-organization)
10. [Troubleshooting and Diagnostic Procedures](#troubleshooting-and-diagnostic-procedures)
11. [License](#license)

---

## Architectural Overview

ServerDeck operates on a decoupled architecture separating interactive rendering from background data collection.

Hardware vitals and operational statistics are queried using direct reads from `/proc`, `/sys`, and system sockets rather than spawning heavy shell tools. Disk health tests (SMART), MariaDB catalog schemas, and Docker inspection pipelines run inside isolated background workers, preventing the interface from freezing when slow storage or network mounts are probed.

Interface elements dynamically adjust between 80-column terminal displays and wide multi-column layouts up to 120 columns without horizontal line wrapping or frame tearing. Color profiles and language settings (English and Polish) persist across reboots inside `config.yaml`. Secret tokens loaded from `.env` are held in process memory without leaking into `/proc/<pid>/environ`.

---

## Installation and Launch Methods

### 1. Zero-Install Execution with NPX (Recommended)

When Node.js (version 16 or newer) and Python 3 are present on the target machine, ServerDeck runs immediately without prior repository cloning or manual virtual environment preparation.

```bash
npx serverdeck
```

The NPX launcher downloads the package from the official NPM registry, configures an isolated local runtime environment, verifies required Python libraries, and starts the dashboard.

### 2. Global Installation with NPM

Installing ServerDeck globally places the executable directly inside the system path.

```bash
npm install -g serverdeck
serverdeck
```

### 3. Production Deployment with Bash and Systemd (Ubuntu and Debian)

For long-term production deployments on dedicated hosts, the automated installation script provisions a dedicated system user, sets up a virtual environment in `/opt/serverdeck/venv`, creates configuration templates in `/etc/serverdeck`, and configures hardened systemd service units.

```bash
curl -fsSL https://raw.githubusercontent.com/Norbertkkl/ServerDeck/main/install.sh | sudo bash -s -- --all
```

After the installation completes, the dashboard and background daemon can be managed using standard system tooling.

```bash
serverdeck
sudo systemctl status serverdeck-bot.service
```

### 4. Developer Setup from Git Source

To inspect or modify the code directly:

1. Clone the repository from GitHub.
```bash
git clone https://github.com/Norbertkkl/ServerDeck.git
cd ServerDeck
```

2. Initialize and activate a Python virtual environment.
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install all required dependencies.
```bash
pip install -r requirements.txt
```

4. Install the package in editable mode and run.
```bash
pip install -e .
serverdeck
```

### 5. Python Package Index (PyPI)

```bash
pip install serverdeck-cli
serverdeck
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

### Configuring the `.env` File

Copy the template configuration file into place:
```bash
cp .env.example .env
chmod 640 .env
```

Set credentials and thresholds inside `.env`:
```ini
SERVERDECK_ENV=production

# Discord bot authentication token obtained from the Discord Developer Portal
DISCORD_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"

# Dedicated channel for the live-updating status embed
DISCORD_STATUS_CHANNEL_ID="123456789012345678"

# Dedicated channel for instantaneous anomaly and threshold notifications
DISCORD_ALERTS_CHANNEL_ID="123456789012345678"

# Numerical Discord user IDs allowed to execute interactive bot commands
DISCORD_ALLOWED_USER_IDS="771669963890491422"

# Discord Webhook URL for terminal-initiated telemetry transmissions
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Alerting thresholds (percentage and temperature degrees Celsius)
ALERT_CPU_PERCENT=90.0
ALERT_RAM_PERCENT=90.0
ALERT_DISK_PERCENT=90.0
ALERT_TEMP_CELSIUS=80.0
```

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
