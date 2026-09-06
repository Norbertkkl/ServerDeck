import os
import json
import time
import socket
import http.client
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from serverdeck.core.state import _docker_containers_cache, STATE_LOCK

class DockerUnixConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float = 2.0):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock

def query_docker_api(endpoint: str, method: str = "GET", timeout: float = 2.0) -> Tuple[bool, Any]:
    sock_path = "/var/run/docker.sock"
    if not os.path.exists(sock_path):
        return False, "Docker socket not found (/var/run/docker.sock)"

    conn = None
    try:
        conn = DockerUnixConnection(sock_path, timeout=timeout)
        conn.request(method, endpoint)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        if resp.status in (200, 201, 204):
            if data and data.strip():
                try:
                    return True, json.loads(data)
                except Exception:
                    return True, data
            return True, None
        return False, f"Docker API HTTP {resp.status}: {data[:60]}"
    except (PermissionError, ConnectionRefusedError, socket.timeout) as e:
        return False, f"Docker socket error: {e}"
    except Exception as e:
        return False, f"Docker query failed: {e}"
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

def get_docker_containers(force: bool = False) -> List[Dict[str, Any]]:
    global _docker_containers_cache
    now = time.time()
    with STATE_LOCK:
        if not force and (now - _docker_containers_cache["time"] < 2.0) and _docker_containers_cache["containers"]:
            return _docker_containers_cache["containers"]

    containers = []
    ok, data = query_docker_api("/containers/json?all=1")
    if ok and isinstance(data, list):
        for c in data:
            c_id = c.get("Id", "")[:12]
            names = c.get("Names", [])
            name = names[0].lstrip("/") if names else "unnamed"
            image = c.get("Image", "")[:20]
            status = c.get("State", "") or c.get("Status", "")
            created = c.get("Created", 0)

            ports_list = []
            for p in c.get("Ports", []):
                pub = p.get("PublicPort")
                priv = p.get("PrivatePort")
                proto = p.get("Type", "tcp")
                if pub:
                    ports_list.append(f"{pub}->{priv}/{proto}")
                elif priv:
                    ports_list.append(f"{priv}/{proto}")
            port_str = ", ".join(ports_list[:2]) if ports_list else "none"

            containers.append({
                "id": c_id,
                "name": name[:18],
                "image": image,
                "status": status[:10],
                "ports": port_str[:16],
                "created": created
            })

    with STATE_LOCK:
        _docker_containers_cache["time"] = now
        _docker_containers_cache["containers"] = containers
    return containers

def docker_container_action(container_id: str, action: str = "restart") -> Tuple[bool, str]:
    if action not in ("start", "stop", "restart"):
        return False, f"Invalid container action: {action}"
    endpoint = f"/containers/{container_id}/{action}"
    ok, err = query_docker_api(endpoint, method="POST", timeout=6.0)
    get_docker_containers(force=True)
    if ok:
        return True, f"Container {container_id} {action}ed successfully"
    return False, f"Failed to {action} container {container_id}: {err}"

def docker_container_delete(container_id: str) -> Tuple[bool, str]:
    endpoint = f"/containers/{container_id}?force=1"
    ok, err = query_docker_api(endpoint, method="DELETE", timeout=6.0)
    get_docker_containers(force=True)
    if ok:
        return True, f"Container {container_id} removed"
    return False, f"Failed to delete container: {err}"

def deploy_docker_template(template_id: str) -> Tuple[bool, str]:
    templates = {
        "1": ("nginx", ["docker", "run", "-d", "--name", "nginx-srv", "-p", "80:80", "--restart", "unless-stopped", "nginx:alpine"]),
        "2": ("redis", ["docker", "run", "-d", "--name", "redis-srv", "-p", "6379:6379", "--restart", "unless-stopped", "redis:alpine"]),
        "3": ("postgres", ["docker", "run", "-d", "--name", "postgres-srv", "-p", "5432:5432", "-e", "POSTGRES_PASSWORD=postgres", "--restart", "unless-stopped", "postgres:alpine"]),
        "4": ("mariadb", ["docker", "run", "-d", "--name", "mariadb-srv", "-p", "3306:3306", "-e", "MARIADB_ROOT_PASSWORD=root", "--restart", "unless-stopped", "mariadb:latest"]),
        "5": ("portainer", ["docker", "run", "-d", "--name", "portainer-ce", "-p", "9000:9000", "-v", "/var/run/docker.sock:/var/run/docker.sock", "--restart", "always", "portainer/portainer-ce:latest"]),
        "6": ("uptime-kuma", ["docker", "run", "-d", "--name", "uptime-kuma", "-p", "3001:3001", "--restart", "always", "louislam/uptime-kuma:1"]),
        "7": ("adguard-home", ["docker", "run", "-d", "--name", "adguard-home", "-p", "3000:3000/tcp", "-p", "53:53/udp", "--restart", "always", "adguard/adguardhome:latest"]),
        "8": ("nodejs", ["docker", "run", "-d", "--name", "node-app", "-p", "8080:8080", "--restart", "unless-stopped", "node:alpine"])
    }
    if template_id not in templates:
        return False, "Invalid template selection."

    name, cmd = templates[template_id]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30.0)
        get_docker_containers(force=True)
        if res.returncode == 0:
            return True, f"Deployed stack {name} successfully!"
        return False, f"Deploy error: {res.stderr.strip()[:65]}"
    except Exception as e:
        return False, f"Deployment failed: {e}"

