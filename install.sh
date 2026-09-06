#!/usr/bin/env bash
#  SERVERDECK - INITIAL INSTALLATION & AUTO-SETUP SCRIPT 
#  Comprehensive ServerDeck Stack Installer for Debian / Ubuntu Linux:
#   - Essential serverdeck utilities & Python runtime
#   - OpenSSH Server configuration & security
#   - MariaDB / MySQL database engine & wizard
#   - Docker Engine & Docker Compose (Official Repo)
#   - Pterodactyl Panel & Wings (Game Server Management)
#   - UFW Firewall automated policies & port mapping
#   - ServerDeck global binary & service integration

set -uo pipefail

# Colors & Styling (24-bit / ANSI Neon Theme)
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_CYAN="\033[38;2;0;240;255m"
C_BLUE="\033[38;2;56;189;248m"
C_GREEN="\033[38;2;0;255;157m"
C_YELLOW="\033[38;2;245;158;11m"
C_RED="\033[38;2;244;63;94m"
C_PURPLE="\033[38;2;168;85;247m"
C_MUTED="\033[38;2;148;163;184m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Logging Functions
log_info() {
    echo -e "${C_BLUE}[info]${C_RESET} ${1}"
}

log_success() {
    echo -e "${C_GREEN}[ok]${C_RESET} ${C_BOLD}${1}${C_RESET}"
}

log_warn() {
    echo -e "${C_YELLOW}[warn]${C_RESET} ${1}"
}

log_error() {
    echo -e "${C_RED}[err]${C_RESET} ${C_BOLD}${1}${C_RESET}"
}

log_step() {
    echo -e "\n${C_PURPLE}════════════════════════════════════════════════════════════════════════════════${C_RESET}"
    echo -e "${C_CYAN}${C_BOLD} [*] ${1}${C_RESET}"
    echo -e "${C_PURPLE}════════════════════════════════════════════════════════════════════════════════${C_RESET}\n"
}

# Root & Environment Verification
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run with administrative privileges (root)!"
        echo -e "${C_YELLOW}Run: sudo $0${C_RESET}\n"
        exit 1
    fi
}

detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO_NAME="${NAME:-Linux}"
        DISTRO_ID="${ID:-debian}"
        DISTRO_VERSION="${VERSION_ID:-}"
        log_info "Detected OS: ${C_BOLD}${DISTRO_NAME}${C_RESET} (${DISTRO_ID} ${DISTRO_VERSION})"
    else
        DISTRO_NAME="Generic Linux"
        DISTRO_ID="debian"
        log_warn "/etc/os-release not found. Assuming Debian/Ubuntu environment."
    fi
}

# Banner
print_banner() {
    clear
    echo -e "${C_CYAN}${C_BOLD}"
    cat << "EOF"
 ____                           ____            _    
/ ___|  ___ _ ____   _____ _ __|  _ \  ___  ___| | __
\___ \ / _ \ '__\ \ / / _ \ '__| | | |/ _ \/ __| |/ /
 ___) |  __/ |   \ V /  __/ |  | |_| |  __/ (__|   < 
|____/ \___|_|    \_/ \___|_|  |____/ \___|\___|_|\_\

EOF
    echo -e "${C_RESET}"
    echo -e "${C_BLUE}═══════════════════════════════════════════════════════════════════════════════════${C_RESET}"
    echo -e "  ${C_CYAN}${C_BOLD}SERVERDECK${C_RESET} - ${C_BOLD}Comprehensive Linux Server Telemetry & Auto-Setup Suite${C_RESET}"
    echo -e "  ${C_MUTED}Author:${C_RESET}  Norbertkkl / ServerDeck Team      ${C_MUTED}Version:${C_RESET}  1.0.0"
    echo -e "  ${C_MUTED}Repo:${C_RESET}    https://github.com/Norbertkkl/ServerDeck   ${C_MUTED}License:${C_RESET}  MIT"
    echo -e "${C_BLUE}═══════════════════════════════════════════════════════════════════════════════════${C_RESET}\n"
}

# INSTALLATION MODULES

# 1. Essential System Tools & Python Runtime (Multi-Distro)
install_essentials() {
    log_step "1/16: Installing Essential System Tools & Python Runtime"
    
    if command -v apt-get >/dev/null 2>&1; then
        log_info "Detected APT package manager (Debian/Ubuntu/Raspberry Pi OS)..."
        apt-get update -y
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            curl wget git htop tmux ncdu ufw smartmontools fail2ban net-tools \
            ca-certificates gnupg lsb-release software-properties-common build-essential \
            python3 python3-pip python3-venv python3-psutil python3-yaml python3-dev \
            lm-sensors pciutils usbutils jq unzip
    elif command -v dnf >/dev/null 2>&1; then
        log_info "Detected DNF package manager (RHEL/Fedora/Rocky/Alma/CentOS Stream)..."
        dnf install -y epel-release || true
        dnf install -y curl wget git htop tmux ncdu ufw smartmontools fail2ban net-tools \
            ca-certificates gnupg gcc gcc-c++ make python3 python3-pip python3-devel \
            lm_sensors pciutils usbutils jq unzip
    elif command -v yum >/dev/null 2>&1; then
        log_info "Detected YUM package manager (CentOS/Oracle Linux)..."
        yum install -y epel-release || true
        yum install -y curl wget git htop tmux ncdu ufw smartmontools fail2ban net-tools \
            ca-certificates gnupg gcc gcc-c++ make python3 python3-pip python3-devel \
            lm_sensors pciutils usbutils jq unzip
    elif command -v pacman >/dev/null 2>&1; then
        log_info "Detected Pacman package manager (Arch Linux/Manjaro)..."
        pacman -Sy --noconfirm curl wget git htop tmux ncdu ufw smartmontools fail2ban \
            net-tools ca-certificates base-devel python python-pip python-psutil python-yaml \
            lm_sensors pciutils usbutils jq unzip
    elif command -v zypper >/dev/null 2>&1; then
        log_info "Detected Zypper package manager (openSUSE/SLES)..."
        zypper refresh
        zypper install -y curl wget git htop tmux ufw smartmontools fail2ban net-tools \
            ca-certificates-mozilla gcc gcc-c++ make python3 python3-pip python3-devel \
            python3-psutil python3-PyYAML libsensors4 pciutils usbutils jq unzip
    elif command -v apk >/dev/null 2>&1; then
        log_info "Detected APK package manager (Alpine Linux)..."
        apk update
        apk add curl wget git htop tmux ufw smartmontools fail2ban net-tools ca-certificates \
            build-base python3 py3-pip py3-psutil py3-yaml lm-sensors pciutils usbutils jq unzip
    else
        log_warn "Unknown package manager. Attempting Python pip fallback..."
    fi

    log_info "Setting up dedicated Python virtual environment in /opt/serverdeck/venv..."
    mkdir -p /opt/serverdeck
    if [[ ! -d "/opt/serverdeck/venv" ]]; then
        python3 -m venv /opt/serverdeck/venv 2>/dev/null || true
    fi

    if [[ -x "/opt/serverdeck/venv/bin/pip" ]]; then
        /opt/serverdeck/venv/bin/pip install -q --upgrade pip 2>/dev/null || true
        /opt/serverdeck/venv/bin/pip install -q pyyaml psutil discord.py 2>/dev/null || true
    else
        python3 -m pip install -q --break-system-packages pyyaml psutil discord.py 2>/dev/null || \
        python3 -m pip install -q pyyaml psutil discord.py 2>/dev/null || true
    fi

    log_info "Configuring hardware thermal sensors (sensors-detect)..."
    if command -v sensors-detect >/dev/null 2>&1; then
        yes "" | sensors-detect >/dev/null 2>&1 || true
    fi

    log_success "All essential tools and Python environment installed successfully!"
}

ensure_essentials_ready() {
    if ! command -v python3 >/dev/null 2>&1 || ! python3 -c "import psutil, yaml" >/dev/null 2>&1 || ! command -v ufw >/dev/null 2>&1; then
        log_info "Base dependencies missing. Executing essential tools setup first..."
        install_essentials
    fi
}

# 2. OpenSSH Server
install_ssh() {
    log_step "2/16: OpenSSH Server Configuration"
    
    log_info "Installing openssh-server..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server

    log_info "Enabling and starting SSH daemon..."
    systemctl enable ssh >/dev/null 2>&1 || systemctl enable sshd >/dev/null 2>&1 || true
    systemctl restart ssh >/dev/null 2>&1 || systemctl restart sshd >/dev/null 2>&1 || true

    if systemctl is-active --quiet ssh || systemctl is-active --quiet sshd; then
        log_success "OpenSSH Server is active and listening on port 22!"
    else
        log_warn "Could not confirm SSH daemon status. Check systemctl status ssh."
    fi

    # Allow SSH in UFW
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 22/tcp >/dev/null 2>&1 || true
        log_info "Added UFW firewall rule for port 22 (SSH)."
    fi
}

# 3. MariaDB / MySQL Database
install_mariadb() {
    log_step "3/16: Installing and Securing MariaDB Database"
    
    log_info "Installing mariadb-server and mariadb-client..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y mariadb-server mariadb-client

    log_info "Starting MariaDB service..."
    systemctl enable --now mariadb

    # Safe default hardening
    log_info "Applying database security hardening..."
    mariadb -u root << 'EOSQL'
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOSQL

    log_success "MariaDB installed and hardened successfully!"

    echo -e "\n${C_CYAN}Would you like to create a new database and user (e.g. for Pterodactyl / apps)? [y/N]:${C_RESET} "
    read -r -t 15 create_db || create_db="n"
    if [[ "${create_db,,}" =~ ^(y|yes)$ ]]; then
        echo -n "Database name [serverdeck_db]: "
        read -r db_name
        db_name="${db_name:-serverdeck_db}"

        echo -n "Database username [serverdeck_user]: "
        read -r db_user
        db_user="${db_user:-serverdeck_user}"

        echo -n "Database password: "
        read -rs db_pass
        echo ""

        if [[ -n "$db_pass" ]]; then
            mariadb -u root << EOSQL
CREATE DATABASE IF NOT EXISTS \`${db_name}\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${db_user}'@'127.0.0.1' IDENTIFIED BY '${db_pass}';
CREATE USER IF NOT EXISTS '${db_user}'@'localhost' IDENTIFIED BY '${db_pass}';
GRANT ALL PRIVILEGES ON \`${db_name}\`.* TO '${db_user}'@'127.0.0.1';
GRANT ALL PRIVILEGES ON \`${db_name}\`.* TO '${db_user}'@'localhost';
FLUSH PRIVILEGES;
EOSQL
            log_success "Database '${db_name}' and user '${db_user}' created successfully!"
        fi
    fi
}

# 4. Docker Engine & Docker Compose
install_docker() {
    log_step "4/16: Installing Official Docker Engine & Docker Compose"
    
    if command -v docker >/dev/null 2>&1; then
        log_info "Docker is already installed ($(docker --version))."
    else
        log_info "Fetching official Docker GPG signing key..."
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/${DISTRO_ID}/gpg -o /etc/apt/keyrings/docker.asc
        chmod a+r /etc/apt/keyrings/docker.asc

        log_info "Adding official Docker APT repository..."
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${DISTRO_ID} \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null

        apt-get update -y
        log_info "Installing Docker CE, CLI, Containerd and Compose Plugin..."
        DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi

    log_info "Enabling Docker daemon service..."
    systemctl enable --now docker

    # Add regular user to docker group
    SUDO_REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo '')}"
    if [[ -n "$SUDO_REAL_USER" && "$SUDO_REAL_USER" != "root" ]]; then
        usermod -aG docker "$SUDO_REAL_USER" || true
        log_info "Added user '${SUDO_REAL_USER}' to docker group."
    fi

    log_success "Docker Engine and Docker Compose configured successfully!"
}

# 5. Nginx Web Server & SSL Certificates (Certbot)
install_nginx() {
    log_step "5/16: Installing Nginx Web Server & Certbot SSL"
    
    log_info "Installing nginx, certbot, and python3-certbot-nginx..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y nginx certbot python3-certbot-nginx
    systemctl enable --now nginx

    if command -v ufw >/dev/null 2>&1; then
        ufw allow 80/tcp >/dev/null 2>&1 || true
        ufw allow 443/tcp >/dev/null 2>&1 || true
        log_info "Opened ports 80 and 443 in UFW for Nginx."
    fi

    log_success "Nginx and Certbot SSL installed and active!"
}

# 6. Apache2 Web Server & SSL Certificates (Certbot)
install_apache() {
    log_step "6/16: Installing Apache2 Web Server & Certbot SSL"
    
    log_info "Installing apache2, certbot, and python3-certbot-apache..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y apache2 certbot python3-certbot-apache
    systemctl enable --now apache2

    if command -v ufw >/dev/null 2>&1; then
        ufw allow 80/tcp >/dev/null 2>&1 || true
        ufw allow 443/tcp >/dev/null 2>&1 || true
        log_info "Opened ports 80 and 443 in UFW for Apache2."
    fi

    log_success "Apache2 and Certbot SSL installed and active!"
}

# 7. Samba SMB/CIFS File Sharing Server
install_samba() {
    log_step "7/16: Installing and Configuring Samba SMB/CIFS"
    
    log_info "Installing samba, smbclient, and cifs-utils..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y samba smbclient cifs-utils
    
    mkdir -p /srv/serverdeck_share
    chmod 0777 /srv/serverdeck_share
    
    if ! grep -q "\[serverdeck_share\]" /etc/samba/smb.conf 2>/dev/null; then
        cat << 'EOF' >> /etc/samba/smb.conf

[serverdeck_share]
   path = /srv/serverdeck_share
   browseable = yes
   read only = no
   guest ok = yes
   create mask = 0777
   directory mask = 0777
EOF
    fi

    systemctl enable --now smbd
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 445/tcp >/dev/null 2>&1 || true
        ufw allow 139/tcp >/dev/null 2>&1 || true
    fi
    log_success "Samba SMB configured! Shared directory /srv/serverdeck_share is available on LAN."
}

# 8. Cockpit Web GUI Console
install_cockpit() {
    log_step "8/16: Installing Cockpit Web GUI Console"
    
    log_info "Installing cockpit, cockpit-networkmanager, cockpit-system..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y cockpit cockpit-networkmanager cockpit-system
    systemctl enable --now cockpit.socket

    if command -v ufw >/dev/null 2>&1; then
        ufw allow 9090/tcp >/dev/null 2>&1 || true
    fi
    log_success "Cockpit Web Console active! Open in browser: https://YOUR_IP:9090"
}

# 9. Portainer CE Docker Management Web UI
install_portainer() {
    log_step "9/16: Deploying Portainer CE (Docker Management UI)"
    
    if ! command -v docker >/dev/null 2>&1; then
        install_docker
    fi

    docker volume create portainer_data >/dev/null 2>&1 || true
    docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always \
        -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:latest >/dev/null 2>&1 || true

    if command -v ufw >/dev/null 2>&1; then
        ufw allow 9443/tcp >/dev/null 2>&1 || true
        ufw allow 8000/tcp >/dev/null 2>&1 || true
    fi
    log_success "Portainer CE deployed successfully! Open in browser: https://YOUR_IP:9443"
}

# 10. WireGuard VPN & Fail2ban Security
install_vpn() {
    log_step "10/16: Installing WireGuard VPN & Fail2ban Security"
    
    DEBIAN_FRONTEND=noninteractive apt-get install -y wireguard wireguard-tools fail2ban iptables
    systemctl enable --now fail2ban

    if command -v ufw >/dev/null 2>&1; then
        ufw allow 51820/udp >/dev/null 2>&1 || true
    fi
    log_success "WireGuard VPN and Fail2ban installed and activated!"
}

# 11. Java 21 & Node.js / PM2 Runtime
install_runtime() {
    log_step "11/16: Installing OpenJDK 21, Node.js & PM2"
    
    DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-21-jre-headless nodejs npm
    npm install -g pm2 >/dev/null 2>&1 || true

    if command -v ufw >/dev/null 2>&1; then
        ufw allow 25565/tcp >/dev/null 2>&1 || true
        ufw allow 3000/tcp >/dev/null 2>&1 || true
    fi
    log_success "OpenJDK 21, Node.js, and PM2 process manager installed successfully!"
}

# 12. Backup Utilities (Rclone, BorgBackup, Restic)
install_backup() {
    log_step "12/16: Installing Rclone, BorgBackup & Restic Suite"
    
    DEBIAN_FRONTEND=noninteractive apt-get install -y rclone borgbackup restic rsync tar
    log_success "Backup toolset (Rclone, Borg, Restic) installed successfully!"
}

# 13. Prometheus Node Exporter
install_metrics() {
    log_step "13/16: Installing Prometheus Node Exporter"
    
    DEBIAN_FRONTEND=noninteractive apt-get install -y prometheus-node-exporter
    systemctl enable --now prometheus-node-exporter

    if command -v ufw >/dev/null 2>&1; then
        ufw allow 9100/tcp >/dev/null 2>&1 || true
    fi
    log_success "Prometheus Node Exporter active on port 9100!"
}

# 14. Pterodactyl Panel & Wings Installer
install_pterodactyl() {
    log_step "14/16: Pterodactyl Panel & Wings Setup Wizard"
    
    echo -e "${C_YELLOW}Pterodactyl requires MariaDB, PHP 8.2/8.3, Nginx, Redis, and Docker.${C_RESET}"
    echo -e "${C_CYAN}Available installation options:${C_RESET}"
    echo -e "  [1] Launch official community autoinstaller (Panel + Wings + SSL)"
    echo -e "  [2] Install core dependencies (Nginx, PHP, Composer, Redis, Certbot)"
    echo -e "  [3] Skip this step"
    echo -n "Select option [1-3]: "
    read -r ptero_choice

    case "$ptero_choice" in
        1)
            log_info "Launching official Pterodactyl Installer script..."
            bash <(curl -s https://pterodactyl-installer.se)
            ;;
        2)
            install_nginx
            log_info "Installing Redis..."
            DEBIAN_FRONTEND=noninteractive apt-get install -y redis-server
            systemctl enable --now redis-server
            log_success "Web server dependencies and Redis installed successfully!"
            ;;
        *)
            log_info "Skipped Pterodactyl setup."
            ;;
    esac

    if command -v ufw >/dev/null 2>&1; then
        ufw allow 80/tcp >/dev/null 2>&1 || true
        ufw allow 443/tcp >/dev/null 2>&1 || true
        ufw allow 8080/tcp >/dev/null 2>&1 || true
        ufw allow 2022/tcp >/dev/null 2>&1 || true
    fi
}

# 15. UFW Firewall Configuration
configure_ufw() {
    log_step "15/16: UFW Firewall Setup & Policy Hardening"
    
    if ! command -v ufw >/dev/null 2>&1; then
        apt-get install -y ufw
    fi

    log_info "Setting default policies (Deny Incoming, Allow Outgoing)..."
    ufw default deny incoming >/dev/null 2>&1
    ufw default allow outgoing >/dev/null 2>&1

    log_info "Allowing standard serverdeck services..."
    for p in 22 80 443 3306 5432 6379 445 139 9090 9443 3000 3001 8000 8080 2022 9100 19999; do
        ufw allow "${p}/tcp" >/dev/null 2>&1 || true
    done
    ufw allow 53/tcp >/dev/null 2>&1 || true
    ufw allow 53/udp >/dev/null 2>&1 || true
    ufw allow 51820/udp >/dev/null 2>&1 || true

    log_info "Enabling UFW firewall..."
    ufw --force enable

    log_success "UFW firewall activated and secured!"
}

# 16. ServerDeck Integration
# 16. ServerDeck Discord Bot Systemd Service Auto-Start
setup_discord_bot() {
    log_step "Installing ServerDeck Discord Bot Systemd Service"
    
    local svc_file="/etc/systemd/system/serverdeck-bot.service"
    local local_svc="${SCRIPT_DIR}/serverdeck-bot.service"
    
    mkdir -p /etc/serverdeck
    mkdir -p /var/lib/serverdeck
    
    id -u serverdeck >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin -d /var/lib/serverdeck serverdeck 2>/dev/null || true
    usermod -aG docker serverdeck >/dev/null 2>&1 || true

    chown -R root:serverdeck /etc/serverdeck
    chmod 750 /etc/serverdeck
    chown -R serverdeck:serverdeck /var/lib/serverdeck
    chmod 770 /var/lib/serverdeck

    if [[ ! -f /etc/serverdeck/config.yaml ]]; then
        if [[ -f "${SCRIPT_DIR}/config.yaml" ]]; then
            cp "${SCRIPT_DIR}/config.yaml" /etc/serverdeck/config.yaml
        elif [[ -f "${SCRIPT_DIR}/serverdeck/templates/config.yaml" ]]; then
            cp "${SCRIPT_DIR}/serverdeck/templates/config.yaml" /etc/serverdeck/config.yaml
        fi
        chmod 644 /etc/serverdeck/config.yaml
    fi

    if [[ ! -f /etc/serverdeck/bot.yaml ]]; then
        if [[ -f "${SCRIPT_DIR}/bot.yaml" ]]; then
            cp "${SCRIPT_DIR}/bot.yaml" /etc/serverdeck/bot.yaml
        elif [[ -f "${SCRIPT_DIR}/serverdeck/templates/bot.yaml" ]]; then
            cp "${SCRIPT_DIR}/serverdeck/templates/bot.yaml" /etc/serverdeck/bot.yaml
        fi
        chmod 640 /etc/serverdeck/bot.yaml
        chown root:serverdeck /etc/serverdeck/bot.yaml
    fi

    if [[ ! -f /etc/serverdeck/.env ]]; then
        if [[ -f "${SCRIPT_DIR}/.env" ]]; then
            cp "${SCRIPT_DIR}/.env" /etc/serverdeck/.env
        elif [[ -f "${SCRIPT_DIR}/.env.example" ]]; then
            cp "${SCRIPT_DIR}/.env.example" /etc/serverdeck/.env
        fi
        chmod 640 /etc/serverdeck/.env
        chown root:serverdeck /etc/serverdeck/.env
    fi

    if [[ -f "$local_svc" ]]; then
        cp -f "$local_svc" "$svc_file"
    else
        cat << 'EOF' > "$svc_file"
[Unit]
Description=ServerDeck Autonomous Discord Bot Daemon
After=network.target network-online.target docker.service mariadb.service
Wants=network-online.target

[Service]
Type=simple
User=serverdeck
Group=serverdeck
WorkingDirectory=/var/lib/serverdeck
EnvironmentFile=-/etc/serverdeck/.env
ExecStart=/usr/local/bin/serverdeck-bot
Restart=always
RestartSec=5s
Environment=PYTHONUNBUFFERED=1

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadOnlyPaths=/etc/serverdeck
ReadWritePaths=/var/lib/serverdeck
CapabilityBoundingSet=

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    fi

    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl enable serverdeck-bot.service >/dev/null 2>&1 || true
    log_success "ServerDeck Discord Bot service registered and enabled for boot auto-start!"
    log_info "Configure your bot secrets in /etc/serverdeck/.env or bot.yaml"
    log_info "Start anytime using: systemctl start serverdeck-bot or serverdeck --service start bot"
}

setup_serverdeck_pulse() {
    log_step "16/16: Registering ServerDeck Globally"
    
    APP_PY="${SCRIPT_DIR}/app.py"
    if [[ ! -f "$APP_PY" ]]; then
        APP_PY="/home/pann/homelab/app.py"
    fi

    WRAPPER="/usr/local/bin/serverdeck"
    log_info "Creating global launcher: ${WRAPPER}..."
    cat << EOF > "$WRAPPER"
#!/usr/bin/env bash
if [[ -x /opt/serverdeck/venv/bin/python3 ]]; then
    exec /opt/serverdeck/venv/bin/python3 "${APP_PY}" "\$@"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/python3" ]]; then
    exec "${SCRIPT_DIR}/.venv/bin/python3" "${APP_PY}" "\$@"
else
    exec python3 "${APP_PY}" "\$@"
fi
EOF
    chmod +x "$WRAPPER"

    BOT_WRAPPER="/usr/local/bin/serverdeck-bot"
    log_info "Creating bot launcher: ${BOT_WRAPPER}..."
    cat << EOF > "$BOT_WRAPPER"
#!/usr/bin/env bash
if [[ -x /opt/serverdeck/venv/bin/python3 ]]; then
    exec /opt/serverdeck/venv/bin/python3 -m serverdeck.bot.main "\$@"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/python3" ]]; then
    exec "${SCRIPT_DIR}/.venv/bin/python3" -m serverdeck.bot.main "\$@"
else
    exec python3 -m serverdeck.bot.main "\$@"
fi
EOF
    chmod +x "$BOT_WRAPPER"

    if ! grep -q "alias serverdeck=" /root/.bashrc 2>/dev/null; then
        echo "alias serverdeck='serverdeck'" >> /root/.bashrc
        echo "alias pulse='serverdeck'" >> /root/.bashrc
    fi

    setup_discord_bot
    log_success "ServerDeck registered! Launch anytime using: serverdeck"
}

# Complete All-in-One Installation
install_all() {
    log_info "Starting full ServerDeck Ultimate Stack installation (All-in-One)..."
    install_essentials
    install_ssh
    install_mariadb
    install_docker
    install_nginx
    install_samba
    install_cockpit
    install_portainer
    install_vpn
    install_runtime
    install_backup
    install_metrics
    install_pterodactyl
    configure_ufw
    setup_serverdeck_pulse
    
    echo -e "\n${C_GREEN}${C_BOLD}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════════════════╗
║           SERVERDECK ULTIMATE STACK INSTALLED & CONFIGURED SUCCESSFULLY!           ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${C_RESET}"
}

# MAIN INTERACTIVE MENU
main_menu() {
    print_banner
    detect_distro
    echo -e "${C_CYAN}${C_BOLD}Select module to install:${C_RESET}"
    echo -e "  ${C_BOLD}[ 1]${C_RESET}   OpenSSH & SFTP Server (Install, enable service, port 22)"
    echo -e "  ${C_BOLD}[ 2]${C_RESET}   MariaDB / MySQL Database (Hardening & setup wizard)"
    echo -e "  ${C_BOLD}[ 3]${C_RESET}   Docker Engine & Docker Compose (Official repository)"
    echo -e "  ${C_BOLD}[ 4]${C_RESET}   Nginx Web Server & Certbot SSL (Ports 80/443)"
    echo -e "  ${C_BOLD}[ 5]${C_RESET}   Apache2 Web Server & Certbot SSL (Ports 80/443)"
    echo -e "  ${C_BOLD}[ 6]${C_RESET}   Samba SMB/CIFS File Server (Directory /srv/serverdeck_share)"
    echo -e "  ${C_BOLD}[ 7]${C_RESET}   Cockpit Web GUI Console (Browser management, Port 9090)"
    echo -e "  ${C_BOLD}[ 8]${C_RESET}   Portainer CE Docker Web UI (Port 9443)"
    echo -e "  ${C_BOLD}[ 9]${C_RESET}   WireGuard VPN, Tailscale & Fail2ban Security"
    echo -e "  ${C_BOLD}[10]${C_RESET}   Java 21 & Node.js / NPM / PM2 Runtime"
    echo -e "  ${C_BOLD}[11]${C_RESET}   Rclone, BorgBackup & Restic Suite (Backup solutions)"
    echo -e "  ${C_BOLD}[12]${C_RESET}   Prometheus Node Exporter (Telemetry, Port 9100)"
    echo -e "  ${C_BOLD}[13]${C_RESET}   Pterodactyl Panel & Wings (Game server manager)"
    echo -e "  ${C_BOLD}[14]${C_RESET}   Essential Tools & Python Runtime (curl, git, htop, psutil, ufw)"
    echo -e "  ${C_BOLD}[15]${C_RESET}   UFW Firewall Configuration (Default policies & ports)"
    echo -e "  ${C_BOLD}[16]${C_RESET} [*]  ${C_GREEN}${C_BOLD}Full ServerDeck Ultimate Installation (All-in-One stack)${C_RESET}"
    echo -e "  ${C_BOLD}[ 0]${C_RESET}   Exit"
    echo -e "${C_BLUE}───────────────────────────────────────────────────────────────────────────────────${C_RESET}"
    echo -n "Enter option [0-16]: "
    read -r choice

    case "$choice" in
        1) install_ssh ;;
        2) install_mariadb ;;
        3) install_docker ;;
        4) install_nginx ;;
        5) install_apache ;;
        6) install_samba ;;
        7) install_cockpit ;;
        8) install_portainer ;;
        9) install_vpn ;;
        10) install_runtime ;;
        11) install_backup ;;
        12) install_metrics ;;
        13) install_pterodactyl ;;
        14) install_essentials ;;
        15) configure_ufw ;;
        16) install_all ;;
        0) echo -e "\n${C_CYAN}Goodbye!${C_RESET}\n"; exit 0 ;;
        *) log_error "Invalid option: $choice"; exit 1 ;;
    esac
}

# CLI Flags Dispatcher (e.g. ./install.sh --all, ./install.sh --docker)
check_root

if [[ $# -gt 0 ]]; then
    print_banner
    detect_distro
    case "$1" in
        --banner|-b) exit 0 ;;
        --all|-a) install_all ;;
        --essentials) install_essentials ;;
        --ssh) install_ssh ;;
        --mariadb|--mysql) install_mariadb ;;
        --docker) install_docker ;;
        --nginx) install_nginx ;;
        --apache|--apache2) install_apache ;;
        --samba) install_samba ;;
        --cockpit) install_cockpit ;;
        --portainer) install_portainer ;;
        --vpn) install_vpn ;;
        --runtime|--java|--node) install_runtime ;;
        --backup) install_backup ;;
        --metrics) install_metrics ;;
        --pterodactyl|--ptero) install_pterodactyl ;;
        --ufw) configure_ufw ;;
        --pulse) setup_serverdeck_pulse ;;
        --help|-h)
            echo "Usage: $0 [OPTION]"
            echo "Options:"
            echo "  --banner, -b       Show ServerDeck ASCII banner and metadata"
            echo "  --all, -a          Install full ServerDeck Ultimate All-in-One stack"
            echo "  --essentials       Install base system tools & Python runtime"
            echo "  --ssh              Install and configure OpenSSH Server"
            echo "  --mariadb          Install MariaDB database"
            echo "  --docker           Install Docker Engine & Docker Compose"
            echo "  --nginx            Install Nginx Web Server & Certbot SSL"
            echo "  --apache           Install Apache2 Web Server & Certbot SSL"
            echo "  --samba            Install Samba SMB/CIFS file server"
            echo "  --cockpit          Install Cockpit Web Console (Port 9090)"
            echo "  --portainer        Deploy Portainer CE Docker UI (Port 9443)"
            echo "  --vpn              Install WireGuard VPN & Fail2ban"
            echo "  --runtime          Install Java 21, Node.js and PM2"
            echo "  --backup           Install backup toolset (Rclone, Borg, Restic)"
            echo "  --metrics          Install Prometheus Node Exporter"
            echo "  --pterodactyl      Run Pterodactyl Panel / Wings installer"
            echo "  --ufw              Configure UFW firewall rules"
            echo "  --pulse            Register global 'serverdeck' command"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use '$0 --help' to display available options."
            exit 1
            ;;
    esac
else
    main_menu
fi
