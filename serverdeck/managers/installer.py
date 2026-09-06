import os
import time
import threading
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from serverdeck.core.state import (
    find_bin, _software_hub_cache, _portainer_compose_cache, STATE_LOCK
)

def check_service_active(svc: str) -> bool:
    if find_bin("systemctl"):
        try:
            res = subprocess.run(
                ["systemctl", "is-active", svc],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=0.8
            )
            return res.stdout.strip() == "active"
        except Exception:
            pass
    return False

def get_software_hub_status(force: bool = False) -> Dict[str, Any]:
    global _software_hub_cache, _portainer_compose_cache
    now = time.time()
    with STATE_LOCK:
        if not force and (now - _software_hub_cache["time"] < 15.0) and _software_hub_cache["data"]:
            return _software_hub_cache["data"]

    services_to_check = [
        "ssh", "sshd", "vsftpd", "mariadb", "mysql", "docker", "nginx", "apache2", "httpd",
        "smbd", "samba", "cockpit", "tailscaled", "fail2ban", "prometheus-node-exporter",
        "redis-server", "redis", "postgresql", "caddy", "netdata", "cloudflared", "ufw"
    ]
    active_map: Dict[str, bool] = {}
    if find_bin("systemctl"):
        try:
            res = subprocess.run(
                ["systemctl", "is-active"] + services_to_check,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=1.5
            )
            lines = res.stdout.strip().splitlines()
            for idx, svc in enumerate(services_to_check):
                if idx < len(lines):
                    active_map[svc] = (lines[idx].strip() == "active")
        except Exception:
            pass

    with STATE_LOCK:
        if force or (now - _portainer_compose_cache["time"] >= 30.0):
            portainer_active = False
            if find_bin("docker"):
                try:
                    p_res = subprocess.run(
                        ["docker", "ps", "--filter", "name=portainer", "--format", "{{.Names}}"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        timeout=1.5
                    )
                    portainer_active = bool(p_res.stdout.strip())
                except Exception:
                    pass

            compose_installed = False
            compose_ver = "N/A"
            if find_bin("docker-compose"):
                compose_installed = True
            elif find_bin("docker"):
                try:
                    c_res = subprocess.run(
                        ["docker", "compose", "version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        timeout=1.0
                    )
                    if c_res.returncode == 0:
                        compose_installed = True
                        compose_ver = c_res.stdout.strip().split()[-1]
                except Exception:
                    pass

            _portainer_compose_cache["time"] = now
            _portainer_compose_cache["portainer"] = portainer_active
            _portainer_compose_cache["compose"] = compose_installed
            _portainer_compose_cache["compose_ver"] = compose_ver

    py_ver = "N/A"
    if find_bin("python3"):
        try:
            p_out = subprocess.run(["python3", "--version"], stdout=subprocess.PIPE, text=True, timeout=0.8).stdout.strip()
            py_ver = p_out.split()[-1] if p_out else "Installed"
        except Exception:
            pass

    node_ver = "N/A"
    if find_bin("node"):
        try:
            node_ver = subprocess.run(["node", "--version"], stdout=subprocess.PIPE, text=True, timeout=0.8).stdout.strip()
        except Exception:
            pass

    java_ver = "N/A"
    if find_bin("java"):
        try:
            j_out = subprocess.run(["java", "-version"], stderr=subprocess.PIPE, text=True, timeout=0.8).stderr.strip()
            first_line = j_out.splitlines()[0] if j_out else ""
            java_ver = first_line.replace('openjdk version', '').replace('java version', '').replace('"', '').strip()
        except Exception:
            pass

    def check_pkg(bin_name: str, svc_names: Optional[List[str]] = None) -> Tuple[bool, bool]:
        installed = bool(find_bin(bin_name))
        active = False
        if svc_names:
            active = any(active_map.get(s, False) for s in svc_names)
        return installed, active

    packages = {}
    packages["1"] = check_pkg("sshd", ["ssh", "sshd"])
    packages["2"] = check_pkg("vsftpd", ["vsftpd"])
    packages["3"] = check_pkg("mariadb", ["mariadb", "mysql"])
    packages["4"] = check_pkg("docker", ["docker"])
    packages["5"] = (_portainer_compose_cache["compose"], False)
    packages["6"] = check_pkg("nginx", ["nginx"])
    packages["7"] = check_pkg("apache2", ["apache2", "httpd"])
    packages["8"] = check_pkg("psql", ["postgresql"])
    packages["9"] = check_pkg("redis-server", ["redis-server", "redis"])
    packages["10"] = check_pkg("ufw", ["ufw"])
    packages["11"] = check_pkg("wg", ["wg-quick@wg0"])
    packages["12"] = check_pkg("fail2ban-client", ["fail2ban"])
    packages["13"] = check_pkg("cockpit-bridge", ["cockpit"])
    packages["14"] = check_pkg("cloudflared", ["cloudflared"])
    packages["15"] = check_pkg("caddy", ["caddy"])
    packages["16"] = check_pkg("smbd", ["smbd", "samba"])
    packages["17"] = (_portainer_compose_cache["portainer"], _portainer_compose_cache["portainer"])
    packages["18"] = (os.path.exists("/opt/AdGuardHome/AdGuardHome"), check_service_active("AdGuardHome"))
    packages["19"] = check_pkg("node")
    packages["20"] = check_pkg("go")
    packages["21"] = check_pkg("rustc")
    packages["22"] = check_pkg("php")
    packages["23"] = check_pkg("python3")
    packages["24"] = check_pkg("java")
    packages["25"] = (os.path.exists("/bin/zsh") or os.path.exists("/usr/bin/zsh"), False)
    packages["26"] = check_pkg("htop")
    packages["27"] = check_pkg("tmux")
    packages["28"] = check_pkg("fastfetch") or check_pkg("neofetch")
    packages["29"] = check_pkg("certbot")
    packages["30"] = check_pkg("git")
    packages["31"] = (os.path.exists("/opt/uptime-kuma"), check_service_active("uptime-kuma"))
    packages["32"] = check_pkg("netdata", ["netdata"])
    packages["33"] = check_pkg("node_exporter", ["prometheus-node-exporter"])
    packages["34"] = check_pkg("grafana-server", ["grafana-server"])
    packages["35"] = check_pkg("wings", ["wings"])
    packages["36"] = (os.path.exists("/var/www/pterodactyl"), False)
    packages["37"] = check_pkg("tailscale", ["tailscaled"])
    packages["38"] = check_pkg("sftp", ["ssh", "sshd"])

    hub_data = {
        "packages": packages,
        "python_ver": py_ver,
        "node_ver": node_ver,
        "java_ver": java_ver,
        "active_count": sum(1 for inst, act in packages.values() if act or inst)
    }

    with STATE_LOCK:
        _software_hub_cache["time"] = now
        _software_hub_cache["data"] = hub_data
    return hub_data

def get_installer_actions() -> List[Tuple[str, str, str]]:
    return [
        ("1", "OpenSSH Server", "Install openssh-server, enable ssh service and generate host keys"),
        ("2", "SFTP Server & vsftpd", "Secure FTP/SFTP file transfer server configuration"),
        ("3", "MariaDB / MySQL Server", "Install MariaDB database engine & configure secure defaults"),
        ("4", "Docker Engine CE", "Official Docker CE container engine with systemd daemon"),
        ("5", "Docker Compose Plugin", "Docker-compose v2 plugin for service orchestration"),
        ("6", "Nginx Web Server", "High-performance HTTP/Reverse Proxy server"),
        ("7", "Apache2 Web Server", "Classic Apache2 HTTP server with mpm_event"),
        ("8", "PostgreSQL Database", "Object-relational database system with client tools"),
        ("9", "Redis In-Memory Store", "In-memory data structure store & cache broker"),
        ("10", "UFW Firewall Suite", "Uncomplicated Firewall with preconfigured port safety"),
        ("11", "WireGuard VPN", "Fast, modern, secure VPN tunnel kernel module & tools"),
        ("12", "Fail2Ban Protection", "Intrusion prevention framework against brute-force attacks"),
        ("13", "Cockpit Web Console", "Web-based graphical administration interface for Linux"),
        ("14", "Cloudflare Tunnel (cloudflared)", "Zero Trust secure tunnel connector without port forwarding"),
        ("15", "Caddy Web Server", "Automatic HTTPS web server written in Go"),
        ("16", "Samba Windows Share", "SMB/CIFS file sharing daemon for LAN environments"),
        ("17", "Portainer CE Docker Web GUI", "Web UI for managing Docker containers and volumes"),
        ("18", "AdGuard Home DNS Ad-Blocker", "Network-wide software for blocking ads & tracking"),
        ("19", "Node.js & NPM Toolchain", "V8 JavaScript runtime engine with Node Package Manager"),
        ("20", "Go (Golang) Compiler", "Fast, statically typed compiled programming language"),
        ("21", "Rust & Cargo Toolchain", "Memory-safe systems programming language and package manager"),
        ("22", "PHP 8.x Runtime & CLI", "Server-side scripting language with common extensions"),
        ("23", "Python3 Development Kit", "Python 3, python3-pip, python3-venv and build tools"),
        ("24", "Java OpenJDK Runtime", "Default Java SE Development Kit and JRE environment"),
        ("25", "Zsh & Oh-My-Zsh Framework", "Advanced interactive shell with customizable themes"),
        ("26", "Htop Process Viewer", "Interactive real-time process viewer and system monitor"),
        ("27", "Tmux Terminal Multiplexer", "Terminal session manager with detaching and splits"),
        ("28", "Fastfetch / Neofetch System Info", "Fast, modern CLI system information display tool"),
        ("29", "Certbot Let's Encrypt Client", "Free automated TLS/SSL certificate generator"),
        ("30", "Git Version Control System", "Distributed version control system for source code"),
        ("31", "Uptime Kuma Monitor", "Self-hosted monitoring tool with status pages and alerts"),
        ("32", "Netdata Real-Time Health", "Real-time performance monitoring web dashboard"),
        ("33", "Prometheus Node Exporter", "Hardware and OS metrics exporter for Prometheus"),
        ("34", "Grafana Metrics Dashboard", "Operational dashboard for analytics and visualization"),
        ("35", "Pterodactyl Wings Daemon", "Next-gen game server management daemon in Go"),
        ("36", "Pterodactyl Panel Web UI", "Game server control panel written in PHP/Laravel"),
        ("37", "Tailscale Mesh VPN", "Zero-config VPN using WireGuard protocol"),
        ("38", "Samba / NFS Client Utilities", "Client packages to mount remote Windows SMB/NFS shares")
    ]

class PythonInstallerManager:
    def __init__(self):
        self.is_running = False
        self.active_action = ""
        self.active_pkg_name = ""
        self.output_lines: List[str] = []
        self.return_code = 0
        self._thread: Optional[threading.Thread] = None

    def log(self, text: str):
        self.output_lines.append(text)
        if len(self.output_lines) > 80:
            self.output_lines.pop(0)

    def start_action(self, action_id: str, mode: str = "install"):
        if self.is_running:
            return
        self.is_running = True
        self.active_action = f"{mode.upper()}: #{action_id}"
        self.output_lines = [f"[*] Starting {mode} for package #{action_id}..."]
        self.return_code = 0
        self._thread = threading.Thread(target=self._worker, args=(action_id, mode), daemon=True)
        self._thread.start()

    def _worker(self, action_id: str, mode: str):
        try:
            if mode == "uninstall":
                self._run_uninstall_logic(action_id)
            elif mode == "restart":
                self._run_restart_logic(action_id)
            else:
                self._run_install_logic(action_id)
            get_software_hub_status(force=True)
        finally:
            self.is_running = False

    def _run_cmd(self, cmd_args: List[str]) -> bool:
        self.log(f"$ {' '.join(cmd_args)}")
        try:
            proc = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    clean = line.strip()
                    if clean:
                        self.log(f"  {clean[:72]}")
                proc.stdout.close()
            proc.wait()
            self.return_code = proc.returncode
            return proc.returncode == 0
        except Exception as e:
            self.log(f"  [ERROR] {e}")
            self.return_code = 1
            return False

    def _run_install_logic(self, action_id: str):
        has_apt = bool(find_bin("apt-get"))
        has_dnf = bool(find_bin("dnf"))
        pkg_manager = "apt" if has_apt else ("dnf" if has_dnf else "unknown")

        def apt_install(pkgs: List[str]):
            env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
            subprocess.run(["apt-get", "update", "-qq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
            return self._run_cmd(["apt-get", "install", "-y", "-q"] + pkgs)

        def dnf_install(pkgs: List[str]):
            return self._run_cmd(["dnf", "install", "-y"] + pkgs)

        def install_pkgs(pkgs: List[str]):
            if pkg_manager == "apt":
                return apt_install(pkgs)
            elif pkg_manager == "dnf":
                return dnf_install(pkgs)
            self.log(f"Unsupported package manager on this Linux system.")
            return False

        if action_id == "1":
            install_pkgs(["openssh-server"])
            self._run_cmd(["systemctl", "enable", "--now", "ssh"])
        elif action_id == "2":
            install_pkgs(["vsftpd"])
            self._run_cmd(["systemctl", "enable", "--now", "vsftpd"])
        elif action_id == "3":
            install_pkgs(["mariadb-server", "mariadb-client"] if pkg_manager == "apt" else ["mariadb-server"])
            self._run_cmd(["systemctl", "enable", "--now", "mariadb"])
        elif action_id == "4":
            install_pkgs(["docker.io", "containerd"] if pkg_manager == "apt" else ["docker", "containerd"])
            self._run_cmd(["systemctl", "enable", "--now", "docker"])
        elif action_id == "5":
            install_pkgs(["docker-compose-v2", "docker-compose-plugin"] if pkg_manager == "apt" else ["docker-compose"])
        elif action_id == "6":
            install_pkgs(["nginx"])
            self._run_cmd(["systemctl", "enable", "--now", "nginx"])
        elif action_id == "7":
            install_pkgs(["apache2"] if pkg_manager == "apt" else ["httpd"])
            svc = "apache2" if pkg_manager == "apt" else "httpd"
            self._run_cmd(["systemctl", "enable", "--now", svc])
        elif action_id == "8":
            install_pkgs(["postgresql", "postgresql-contrib"])
            self._run_cmd(["systemctl", "enable", "--now", "postgresql"])
        elif action_id == "9":
            install_pkgs(["redis-server"] if pkg_manager == "apt" else ["redis"])
            svc = "redis-server" if pkg_manager == "apt" else "redis"
            self._run_cmd(["systemctl", "enable", "--now", svc])
        elif action_id == "10":
            install_pkgs(["ufw"])
            self._run_cmd(["ufw", "--force", "enable"])
        elif action_id == "11":
            install_pkgs(["wireguard", "wireguard-tools"])
        elif action_id == "12":
            install_pkgs(["fail2ban"])
            self._run_cmd(["systemctl", "enable", "--now", "fail2ban"])
        elif action_id == "13":
            install_pkgs(["cockpit"])
            self._run_cmd(["systemctl", "enable", "--now", "cockpit.socket"])
        elif action_id == "14":
            self.log("Installing Cloudflared agent...")
            if pkg_manager == "apt":
                self._run_cmd(["curl", "-fsSL", "https://pkg.cloudflare.com/cloudflare-main.gpg", "-o", "/usr/share/keyrings/cloudflare-main.gpg"])
                self._run_cmd(["apt-get", "install", "-y", "cloudflared"])
            else:
                self._run_cmd(["dnf", "install", "-y", "cloudflared"])
        elif action_id == "15":
            install_pkgs(["caddy"])
            self._run_cmd(["systemctl", "enable", "--now", "caddy"])
        elif action_id == "16":
            install_pkgs(["samba", "samba-common-bin"] if pkg_manager == "apt" else ["samba"])
            self._run_cmd(["systemctl", "enable", "--now", "smbd"])
        elif action_id == "17":
            self.log("Deploying Portainer Community Edition container...")
            self._run_cmd(["docker", "volume", "create", "portainer_data"])
            self._run_cmd([
                "docker", "run", "-d", "-p", "9000:9000", "-p", "9443:9443",
                "--name", "portainer", "--restart", "always",
                "-v", "/var/run/docker.sock:/var/run/docker.sock",
                "-v", "portainer_data:/data",
                "portainer/portainer-ce:latest"
            ])
        elif action_id == "18":
            self.log("Installing AdGuard Home...")
            self._run_cmd(["curl", "-s -S -L", "https://raw.githubusercontent.com/AdguardTeam/AdGuardHome/master/scripts/install.sh", "-o", "/tmp/ag_install.sh"])
            self._run_cmd(["bash", "/tmp/ag_install.sh"])
        elif action_id == "19":
            install_pkgs(["nodejs", "npm"])
        elif action_id == "20":
            install_pkgs(["golang-go"] if pkg_manager == "apt" else ["golang"])
        elif action_id == "21":
            install_pkgs(["rustc", "cargo"])
        elif action_id == "22":
            install_pkgs(["php", "php-cli", "php-common", "php-curl", "php-mbstring", "php-mysql", "php-xml"])
        elif action_id == "23":
            install_pkgs(["python3", "python3-pip", "python3-venv", "python3-dev", "build-essential"])
        elif action_id == "24":
            install_pkgs(["default-jdk"] if pkg_manager == "apt" else ["java-latest-openjdk-devel"])
        elif action_id == "25":
            install_pkgs(["zsh", "curl", "git"])
        elif action_id == "26":
            install_pkgs(["htop"])
        elif action_id == "27":
            install_pkgs(["tmux"])
        elif action_id == "28":
            install_pkgs(["neofetch"] if pkg_manager == "apt" else ["fastfetch"])
        elif action_id == "29":
            install_pkgs(["certbot"])
        elif action_id == "30":
            install_pkgs(["git"])
        elif action_id == "31":
            self.log("Deploying Uptime Kuma Container...")
            self._run_cmd(["docker", "volume", "create", "uptime-kuma"])
            self._run_cmd(["docker", "run", "-d", "--restart=always", "-p", "3001:3001", "-v", "uptime-kuma:/app/data", "--name", "uptime-kuma", "louislam/uptime-kuma:1"])
        elif action_id == "32":
            self.log("Installing Netdata One-Line Agent...")
            self._run_cmd(["curl", "-Ss", "https://get.netdata.cloud/kickstart.sh", "-o", "/tmp/netdata-kickstart.sh"])
            self._run_cmd(["bash", "/tmp/netdata-kickstart.sh", "--non-interactive"])
        elif action_id == "33":
            install_pkgs(["prometheus-node-exporter"])
            self._run_cmd(["systemctl", "enable", "--now", "prometheus-node-exporter"])
        elif action_id == "34":
            install_pkgs(["grafana"] if pkg_manager == "apt" else ["grafana"])
            self._run_cmd(["systemctl", "enable", "--now", "grafana-server"])
        elif action_id == "35":
            self.log("Installing Pterodactyl Wings daemon...")
            self._run_cmd(["curl", "-L", "-o", "/usr/local/bin/wings", "https://github.com/pterodactyl/wings/releases/latest/download/wings_linux_amd64"])
            self._run_cmd(["chmod", "u+x", "/usr/local/bin/wings"])
        elif action_id == "36":
            self.log("Setting up Pterodactyl Panel dependencies...")
            install_pkgs(["php", "php-cli", "php-gd", "php-mysql", "php-pdo", "php-mbstring", "php-tokenizer", "php-bcmath", "php-xml", "php-fpm", "curl", "tar", "unzip", "git", "nginx"])
        elif action_id == "37":
            self.log("Installing Tailscale...")
            self._run_cmd(["curl", "-fsSL", "https://tailscale.com/install.sh", "-o", "/tmp/tailscale.sh"])
            self._run_cmd(["sh", "/tmp/tailscale.sh"])
        elif action_id == "38":
            install_pkgs(["cifs-utils", "nfs-common"] if pkg_manager == "apt" else ["cifs-utils", "nfs-utils"])
        else:
            self.log(f"No specific installer procedure defined for action #{action_id}.")

    def _run_uninstall_logic(self, action_id: str):
        has_apt = bool(find_bin("apt-get"))
        has_dnf = bool(find_bin("dnf"))
        pkg_manager = "apt" if has_apt else ("dnf" if has_dnf else "unknown")

        def remove_pkgs(pkgs: List[str], svcs: Optional[List[str]] = None):
            if svcs:
                for s in svcs:
                    self._run_cmd(["systemctl", "disable", "--now", s])
            if pkg_manager == "apt":
                return self._run_cmd(["apt-get", "remove", "-y", "-q"] + pkgs)
            elif pkg_manager == "dnf":
                return self._run_cmd(["dnf", "remove", "-y"] + pkgs)
            return False

        if action_id == "1":
            remove_pkgs(["openssh-server"], ["ssh", "sshd"])
        elif action_id == "2":
            remove_pkgs(["vsftpd"], ["vsftpd"])
        elif action_id == "3":
            remove_pkgs(["mariadb-server", "mariadb-client"] if pkg_manager == "apt" else ["mariadb-server"], ["mariadb", "mysql"])
        elif action_id == "4":
            remove_pkgs(["docker.io", "containerd"] if pkg_manager == "apt" else ["docker", "containerd"], ["docker"])
        elif action_id == "5":
            remove_pkgs(["docker-compose-v2", "docker-compose-plugin"] if pkg_manager == "apt" else ["docker-compose"])
        elif action_id == "6":
            remove_pkgs(["nginx"], ["nginx"])
        elif action_id == "7":
            remove_pkgs(["apache2"] if pkg_manager == "apt" else ["httpd"], ["apache2", "httpd"])
        elif action_id == "8":
            remove_pkgs(["postgresql", "postgresql-contrib"], ["postgresql"])
        elif action_id == "9":
            remove_pkgs(["redis-server"] if pkg_manager == "apt" else ["redis"], ["redis-server", "redis"])
        elif action_id == "10":
            self._run_cmd(["ufw", "--force", "disable"])
            remove_pkgs(["ufw"])
        elif action_id == "17":
            self._run_cmd(["docker", "rm", "-f", "portainer"])
        elif action_id == "31":
            self._run_cmd(["docker", "rm", "-f", "uptime-kuma"])
        else:
            self.log(f"Removing package #{action_id}...")
            actions_list = get_installer_actions()
            pkg_name = actions_list[int(action_id)-1][1].lower() if int(action_id) <= len(actions_list) else ""
            if pkg_name:
                first_word = pkg_name.split()[0]
                remove_pkgs([first_word])

    def _run_restart_logic(self, action_id: str):
        svc_map = {
            "1": ["ssh", "sshd"],
            "2": ["vsftpd"],
            "3": ["mariadb", "mysql"],
            "4": ["docker"],
            "6": ["nginx"],
            "7": ["apache2", "httpd"],
            "8": ["postgresql"],
            "9": ["redis-server", "redis"],
            "10": ["ufw"],
            "11": ["smbd", "samba"],
            "12": ["cockpit"],
            "13": ["fail2ban"],
            "14": ["caddy"],
            "32": ["netdata"],
            "33": ["prometheus-node-exporter"],
            "34": ["grafana-server"],
            "35": ["wings"],
            "37": ["tailscaled"]
        }
        if action_id == "17":
            self.log("Restarting Portainer container...")
            self._run_cmd(["docker", "restart", "portainer"])
        elif action_id == "31":
            self.log("Restarting Uptime Kuma container...")
            self._run_cmd(["docker", "restart", "uptime-kuma"])
        elif action_id in svc_map:
            for s in svc_map[action_id]:
                self.log(f"Restarting service {s}...")
                self._run_cmd(["systemctl", "restart", s])
        else:
            self.log(f"No specific background service defined to restart for #{action_id}.")
