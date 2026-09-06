#!/usr/bin/env python3
import asyncio
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands, tasks
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
BOT_CONFIG_FILE = BASE_DIR / "bot.yaml"
GLOBAL_CONFIG_FILE = BASE_DIR / "config.yaml"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from app import (
        THEMES,
        THEME_KEYS,
        docker_container_action,
        format_bytes,
        format_uptime,
        get_all_device_stats,
        get_detailed_processes,
        get_docker_containers,
        get_mariadb_databases,
        get_mariadb_users,
        get_ufw_status,
    )
    from core.i18n import i18n
except ImportError:
    from serverdeck.app import (
        THEMES,
        THEME_KEYS,
        docker_container_action,
        format_bytes,
        format_uptime,
        get_all_device_stats,
        get_detailed_processes,
        get_docker_containers,
        get_mariadb_databases,
        get_mariadb_users,
        get_ufw_status,
    )
    from serverdeck.core.i18n import i18n

_last_net_time: float = 0.0
_last_net_bytes: Tuple[int, int] = (0, 0)
_cached_rx_speed: float = 0.0
_cached_tx_speed: float = 0.0

def get_live_network_speeds(net_interfaces: List[Dict[str, Any]]) -> Tuple[float, float]:
    global _last_net_time, _last_net_bytes, _cached_rx_speed, _cached_tx_speed
    now = time.time()
    total_rx = sum(i.get("bytes_recv", 0) for i in net_interfaces)
    total_tx = sum(i.get("bytes_sent", 0) for i in net_interfaces)

    if _last_net_time > 0:
        dt = max(0.1, now - _last_net_time)
        rx_diff = max(0, total_rx - _last_net_bytes[0])
        tx_diff = max(0, total_tx - _last_net_bytes[1])
        _cached_rx_speed = rx_diff / dt
        _cached_tx_speed = tx_diff / dt

    _last_net_time = now
    _last_net_bytes = (total_rx, total_tx)
    return _cached_rx_speed, _cached_tx_speed

def get_mariadb_telemetry() -> Dict[str, Any]:
    has_mariadb = shutil.which("mariadb") is not None or shutil.which("mysql") is not None
    if not has_mariadb:
        return {"available": False, "databases": [], "total_count": 0, "sys_count": 0, "total_size_mb": 0.0}

    dbs = get_mariadb_databases()
    users = get_mariadb_users()
    tot_size = sum(d.get("size_mb", 0.0) for d in dbs)
    sys_cnt = sum(1 for d in dbs if d.get("is_system"))

    return {
        "available": True,
        "databases": dbs,
        "users": users,
        "total_count": len(dbs),
        "sys_count": sys_cnt,
        "total_size_mb": tot_size
    }

def load_bot_config() -> Dict[str, Any]:
    if BOT_CONFIG_FILE.exists():
        try:
            with open(BOT_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"[warn] Error parsing bot.yaml: {e}")
    return {}

def format_replacements() -> Dict[str, str]:
    stats = get_all_device_stats()
    dmi = stats.get("dmi", {})
    sys_info = stats.get("system", {})
    cpu = stats.get("cpu", {})
    mem = stats.get("memory", {})
    disks = stats.get("disks", [])
    net = stats.get("network", [])
    ports = stats.get("ports", [])
    dns = stats.get("dns", [])
    drives = stats.get("physical_drives", [])
    sensors = stats.get("sensors", [])
    procs_summary = stats.get("processes", {})
    top_procs = get_detailed_processes(limit=6)

    proc_lines = ["PID    USER     CPU%  MEM%  COMMAND"]
    for p in top_procs:
        proc_lines.append(f"{p['pid']:<6} {p['user'][:7]:<7} {p['cpu_percent']:>5.1f} {p['memory_percent']:>5.1f} {p['name'][:16]}")
    top_procs_str = "\n".join(proc_lines)

    top_cpu_p = f"{top_procs[0]['name']} ({top_procs[0]['cpu_percent']}%)" if top_procs else "N/A"
    by_mem = sorted(top_procs, key=lambda x: x.get("memory_percent", 0), reverse=True)
    top_mem_p = f"{by_mem[0]['name']} ({by_mem[0]['memory_percent']}%)" if by_mem else "N/A"

    root_disk = disks[0] if disks else {}
    part_summaries = []
    for d in disks[:3]:
        part_summaries.append(f"{d.get('mountpoint', '/')}: {format_bytes(d.get('used', 0)).strip()}/{format_bytes(d.get('total', 0)).strip()} ({d.get('percent', 0.0)}%)")
    part_summary_str = " | ".join(part_summaries) if part_summaries else "N/A"

    primary_net = net[0] if net else {}
    primary_ip = primary_net.get("ip", "127.0.0.1")
    primary_iface = primary_net.get("name", "eth0")

    containers = get_docker_containers()
    has_docker = shutil.which("docker") is not None
    docker_status_str = "Running" if has_docker else "Not Installed"
    docker_running_cnt = sum(1 for c in containers if c.get("state") == "running")

    has_mariadb = shutil.which("mariadb") is not None or shutil.which("mysql") is not None
    mariadb_dbs = get_mariadb_databases() if has_mariadb else []
    mariadb_users = get_mariadb_users() if has_mariadb else []

    ufw_st = get_ufw_status()
    ufw_rules = ufw_st.get("rules", [])
    cpu_temp_val = f"{sensors[0]['current']:.1f} C" if sensors else "N/A"

    smart_overall = "PASSED"
    for drv in drives:
        if drv.get("smart", {}).get("health") not in ("PASSED", "OK"):
            smart_overall = "DEGRADED"

    now_dt = time.strftime("%Y-%m-%d %H:%M:%S")
    date_str = time.strftime("%Y-%m-%d")
    time_str = time.strftime("%H:%M:%S")
    curr_lang = i18n.current_lang.upper() if hasattr(i18n, 'current_lang') else "EN"

    return {
        "{hostname}": str(sys_info.get("hostname", platform.node())),
        "{os_distro}": f"{sys_info.get('distro', 'Linux')} ({sys_info.get('arch', 'x86_64')})",
        "{kernel}": str(sys_info.get("kernel", platform.release())),
        "{architecture}": str(sys_info.get("arch", platform.machine())),
        "{uptime}": str(sys_info.get("uptime_str", "N/A")),
        "{boot_time}": str(sys_info.get("boot_time", "N/A")),
        "{motherboard_vendor}": str(dmi.get("board_vendor", "N/A")),
        "{motherboard_model}": str(dmi.get("board_name", dmi.get("product_name", "N/A"))),
        "{bios_vendor}": str(dmi.get("bios_vendor", "N/A")),
        "{bios_version}": f"{dmi.get('bios_version', 'N/A')} ({dmi.get('bios_date', 'N/A')})",
        "{virtualization}": str(cpu.get("virtualization", "None")),
        "{logged_in_users}": ", ".join(sys_info.get("logged_in_users", [])) or "None (Headless)",

        "{cpu_model}": str(cpu.get("model", platform.processor() or "CPU")),
        "{cpu_percent}": f"{cpu.get('usage_percent', 0.0):.1f}",
        "{cpu_cores_physical}": str(cpu.get("cores_physical", cpu.get("cores_logical", 1))),
        "{cpu_cores_logical}": str(cpu.get("cores_logical", 1)),
        "{cpu_freq_current}": f"{cpu.get('freq_current_mhz', 0.0):.1f}",
        "{cpu_freq_min}": f"{cpu.get('freq_min_mhz', 0.0):.1f}",
        "{cpu_freq_max}": f"{cpu.get('freq_max_mhz', 0.0):.1f}",
        "{cpu_governor}": str(cpu.get("scaling_governor", "N/A")),
        "{cpu_temperature}": cpu_temp_val,

        "{ram_used}": format_bytes(mem.get("ram_used", 0)).strip(),
        "{ram_free}": format_bytes(mem.get("ram_free", 0)).strip(),
        "{ram_total}": format_bytes(mem.get("ram_total", 0)).strip(),
        "{ram_percent}": f"{mem.get('ram_percent', 0.0):.1f}",
        "{ram_cached}": format_bytes(mem.get("cached", 0)).strip(),
        "{ram_buffers}": format_bytes(mem.get("buffers", 0)).strip(),
        "{ram_slab}": format_bytes(mem.get("slab", 0)).strip(),
        "{ram_dirty}": format_bytes(mem.get("dirty", 0)).strip(),
        "{swap_used}": format_bytes(mem.get("swap_used", 0)).strip(),
        "{swap_free}": format_bytes(mem.get("swap_free", 0)).strip(),
        "{swap_total}": format_bytes(mem.get("swap_total", 0)).strip(),
        "{swap_percent}": f"{mem.get('swap_percent', 0.0):.1f}",

        "{disk_used}": format_bytes(root_disk.get("used", 0)).strip(),
        "{disk_free}": format_bytes(root_disk.get("free", 0)).strip(),
        "{disk_total}": format_bytes(root_disk.get("total", 0)).strip(),
        "{disk_percent}": f"{root_disk.get('percent', 0.0):.1f}",
        "{disk_mount}": str(root_disk.get("mountpoint", "/")),
        "{disk_read_speed}": f"{format_bytes(0).strip()}/s",
        "{disk_write_speed}": f"{format_bytes(0).strip()}/s",
        "{disk_partitions_summary}": part_summary_str,
        "{smart_health_status}": smart_overall,
        "{smart_drives_count}": str(len(drives)),

        "{net_rx_speed}": f"{format_bytes(get_live_network_speeds(net)[0]).strip()}/s",
        "{net_tx_speed}": f"{format_bytes(get_live_network_speeds(net)[1]).strip()}/s",
        "{net_rx_total}": format_bytes(primary_net.get("bytes_recv", 0)).strip(),
        "{net_tx_total}": format_bytes(primary_net.get("bytes_sent", 0)).strip(),
        "{primary_ip}": str(primary_ip),
        "{primary_iface}": str(primary_iface),
        "{dns_servers}": ", ".join(dns) if dns else "N/A",
        "{listening_ports_count}": str(len(ports)),

        "{load_1m}": f"{sys_info.get('load_avg', (0,0,0))[0]:.2f}",
        "{load_5m}": f"{sys_info.get('load_avg', (0,0,0))[1]:.2f}",
        "{load_15m}": f"{sys_info.get('load_avg', (0,0,0))[2]:.2f}",
        "{total_processes}": str(procs_summary.get("total_processes", len(top_procs))),
        "{file_descriptors}": f"{sys_info.get('file_descriptors_alloc', 0)} / {sys_info.get('file_descriptors_max', 0)}",
        "{entropy_available}": str(sys_info.get("entropy_avail", "N/A")),
        "{top_processes}": top_procs_str,
        "{top_cpu_process}": top_cpu_p,
        "{top_mem_process}": top_mem_p,

        "{docker_status}": docker_status_str,
        "{docker_containers_total}": str(len(containers)),
        "{docker_containers_running}": str(docker_running_cnt),
        "{mariadb_status}": "Active" if has_mariadb else "Not Installed",
        "{mariadb_databases_count}": str(len(mariadb_dbs)),
        "{mariadb_users_count}": str(len(mariadb_users)),
        "{ufw_status}": "Active" if ufw_st.get("active") else "Disabled",
        "{ufw_rules_count}": str(len(ufw_rules)),

        "{timestamp}": now_dt,
        "{date}": date_str,
        "{time}": time_str,
        "{app_name}": "ServerDeck",
        "{language}": curr_lang,

        "{naglowek_raportu}": "ServerDeck - Raport Telemetrii Systemowej",
        "{tresc_raportu_host}": "Zbiorczy raport wydajnosci urzadzenia",
        "{pole_cpu}": "Uzycie CPU",
        "{pole_ram}": "Pamiec RAM",
        "{pole_dysk}": "Przestrzen Dyskowa",
        "{pole_uptime}": "Czas Pracy (Uptime)",
        "{pole_obciazenie}": "Srednie Obciazenie",
        "{pole_procesy}": "Liczba Procesow",
        "{pole_siec}": "Siec i IP",
        "{pole_kontenery_i_bazy}": "Kontenery i Bazy",
        "{pole_zapora}": "Zapora Ogniowa UFW",
        "{pole_top_procesy}": "Najbardziej Obciazajace Procesy",
        "{stopka_raportu}": "ServerDeck Telemetria"
    }

def build_discord_embed(template_type: str = "system_report", extra_replacements: Optional[Dict[str, str]] = None) -> discord.Embed:
    cfg = load_bot_config()
    replacements = format_replacements()
    if extra_replacements:
        replacements.update(extra_replacements)

    lang = i18n.current_lang if hasattr(i18n, 'current_lang') and i18n.current_lang in ("en", "pl") else "en"
    templates = cfg.get("embed_templates", {}).get(template_type, {})
    tpl = templates.get(lang, templates.get("en", {}))

    title = tpl.get("title", "ServerDeck Telemetry Report")
    description = tpl.get("description", "Performance metrics for {hostname}")
    color_hex = tpl.get("color_hex", "#00f0ff")
    footer_text = tpl.get("footer", "ServerDeck | {timestamp}")

    for k, v in replacements.items():
        title = title.replace(k, str(v))
        description = description.replace(k, str(v))
        footer_text = footer_text.replace(k, str(v))

    color_int = int(color_hex.lstrip("#"), 16)
    embed = discord.Embed(title=title, description=description, color=color_int)

    for f in tpl.get("fields", []):
        f_name = f.get("name", "")
        f_val = f.get("value", "")
        for k, v in replacements.items():
            f_name = f_name.replace(k, str(v))
            f_val = f_val.replace(k, str(v))
        embed.add_field(name=f_name, value=f_val, inline=f.get("inline", True))

    embed.set_footer(text=footer_text)
    return embed

cfg = load_bot_config()
bot_settings = cfg.get("bot_settings", {})
prefix = bot_settings.get("command_prefix", "!")
token = bot_settings.get("bot_token", "").strip()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)
tree = bot.tree

last_dashboard_msg_id: Optional[int] = None
last_alert_times: Dict[str, float] = {}

def is_authorized(user_id: int, user_roles: Optional[List[discord.Role]] = None) -> bool:
    c = load_bot_config()
    bs = c.get("bot_settings", {})
    allowed_users = bs.get("allowed_user_ids", [])
    admin_roles = bs.get("admin_role_ids", [])

    if not allowed_users and not admin_roles:
        return True
    if user_id in allowed_users:
        return True
    if user_roles and admin_roles:
        for r in user_roles:
            if r.id in admin_roles:
                return True
    return False

@bot.event
async def on_ready():
    print(f"[info] ServerDeck Discord Bot logged in as {bot.user} (ID: {bot.user.id})")
    if bot_settings.get("enable_slash_commands", True):
        try:
            synced = await tree.sync()
            print(f"[info] Synced {len(synced)} Slash Commands globally.")
        except Exception as e:
            print(f"[warn] Failed to sync slash commands: {e}")

    if not live_dashboard_task.is_running():
        live_dashboard_task.start()
    if not watchdog_alarm_task.is_running():
        watchdog_alarm_task.start()

@tasks.loop(seconds=30)
async def live_dashboard_task():
    global last_dashboard_msg_id
    c = load_bot_config()
    bs = c.get("bot_settings", {})
    channel_id = bs.get("status_channel_id", 0)
    interval = max(10, bs.get("live_dashboard_interval_seconds", 30))
    live_dashboard_task.change_interval(seconds=interval)

    if not channel_id:
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        return

    try:
        embed = build_discord_embed(template_type="system_report")
        if last_dashboard_msg_id:
            try:
                msg = await channel.fetch_message(last_dashboard_msg_id)
                await msg.edit(embed=embed)
                return
            except (discord.NotFound, discord.HTTPException):
                last_dashboard_msg_id = None

        msg = await channel.send(embed=embed)
        last_dashboard_msg_id = msg.id
    except Exception as e:
        print(f"[warn] Failed to update live dashboard: {e}")

@tasks.loop(seconds=15)
async def watchdog_alarm_task():
    c = load_bot_config()
    bs = c.get("bot_settings", {})
    alerts_channel_id = bs.get("alerts_channel_id", 0)
    thresholds = c.get("alert_thresholds", {})
    cooldown = 300.0
    now = time.time()

    if not alerts_channel_id:
        return

    channel = bot.get_channel(alerts_channel_id)
    if not channel:
        return

    stats = get_all_device_stats()
    cpu_pct = stats.get("cpu", {}).get("usage_percent", 0.0)
    ram_pct = stats.get("memory", {}).get("ram_percent", 0.0)
    disks = stats.get("disks", [])
    disk_pct = disks[0].get("percent", 0.0) if disks else 0.0

    cpu_limit = thresholds.get("cpu_percent", 90.0)
    if cpu_pct >= cpu_limit and (now - last_alert_times.get("cpu", 0) > cooldown):
        last_alert_times["cpu"] = now
        embed = build_discord_embed("alert_notification", extra_replacements={
            "{alert_message}": f"High CPU Load Detected ({cpu_pct:.1f}%)",
            "{current_value}": f"{cpu_pct:.1f}%",
            "{threshold_value}": f"{cpu_limit:.1f}%"
        })
        await channel.send(embed=embed)

    ram_limit = thresholds.get("ram_percent", 90.0)
    if ram_pct >= ram_limit and (now - last_alert_times.get("ram", 0) > cooldown):
        last_alert_times["ram"] = now
        embed = build_discord_embed("alert_notification", extra_replacements={
            "{alert_message}": f"Critical RAM Allocation ({ram_pct:.1f}%)",
            "{current_value}": f"{ram_pct:.1f}%",
            "{threshold_value}": f"{ram_limit:.1f}%"
        })
        await channel.send(embed=embed)

    disk_limit = thresholds.get("disk_percent", 90.0)
    if disk_pct >= disk_limit and (now - last_alert_times.get("disk", 0) > cooldown):
        last_alert_times["disk"] = now
        embed = build_discord_embed("alert_notification", extra_replacements={
            "{alert_message}": f"Disk Storage Critical on Root Partition ({disk_pct:.1f}%)",
            "{current_value}": f"{disk_pct:.1f}%",
            "{threshold_value}": f"{disk_limit:.1f}%"
        })
        await channel.send(embed=embed)

@bot.command(name="status")
async def cmd_status(ctx: commands.Context):
    embed = build_discord_embed("system_report")
    await ctx.send(embed=embed)

@tree.command(name="status", description="Display ServerDeck system telemetry report")
async def slash_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    embed = build_discord_embed("system_report")
    await interaction.followup.send(embed=embed)

@bot.command(name="docker")
async def cmd_docker(ctx: commands.Context, action: Optional[str] = None, target: Optional[str] = None):
    if action and not is_authorized(ctx.author.id, getattr(ctx.author, "roles", None)):
        await ctx.send("Access Denied: You do not have permission to execute container actions.")
        return

    containers = get_docker_containers()
    if not action:
        embed = discord.Embed(title="ServerDeck Docker Containers", color=0x00f0ff)
        if not containers:
            embed.description = "No active Docker containers detected on system."
        else:
            for c in containers[:15]:
                status_icon = "[RUNNING]" if c.get("state") == "running" else "[STOPPED]"
                embed.add_field(
                    name=f"{c['name']} ({c['id'][:8]})",
                    value=f"State: {status_icon} | Image: `{c['image']}` | Ports: `{c.get('ports') or 'None'}`",
                    inline=False
                )
        await ctx.send(embed=embed)
        return

    if action in ("start", "stop", "restart") and target:
        found = [c for c in containers if c["name"] == target or c["id"].startswith(target)]
        if not found:
            await ctx.send(f"Container `{target}` not found on system.")
            return
        cid = found[0]["id"]
        ok, msg = docker_container_action(cid, action)
        color = 0x00ff9d if ok else 0xf43f5e
        embed = discord.Embed(title=f"Docker Action: {action.upper()}", description=msg, color=color)
        await ctx.send(embed=embed)

@tree.command(name="docker", description="Inspect and manage Docker containers")
@app_commands.describe(action="Action to perform (list, start, stop, restart)", target="Container name or ID")
async def slash_docker(interaction: discord.Interaction, action: Optional[str] = "list", target: Optional[str] = None):
    if action != "list" and not is_authorized(interaction.user.id, getattr(interaction.user, "roles", None)):
        await interaction.response.send_message("Access Denied: You do not have permission to execute container actions.", ephemeral=True)
        return

    containers = get_docker_containers()
    if action == "list" or not target:
        embed = discord.Embed(title="ServerDeck Docker Containers", color=0x00f0ff)
        if not containers:
            embed.description = "No active Docker containers detected on system."
        else:
            for c in containers[:15]:
                status_icon = "[RUNNING]" if c.get("state") == "running" else "[STOPPED]"
                embed.add_field(
                    name=f"{c['name']} ({c['id'][:8]})",
                    value=f"State: {status_icon} | Image: `{c['image']}` | Ports: `{c.get('ports') or 'None'}`",
                    inline=False
                )
        await interaction.response.send_message(embed=embed)
        return

    found = [c for c in containers if c["name"] == target or c["id"].startswith(target)]
    if not found:
        await interaction.response.send_message(f"Container `{target}` not found.", ephemeral=True)
        return
    cid = found[0]["id"]
    ok, msg = docker_container_action(cid, action)
    color = 0x00ff9d if ok else 0xf43f5e
    embed = discord.Embed(title=f"Docker Action: {action.upper()}", description=msg, color=color)
    await interaction.response.send_message(embed=embed)

@bot.command(name="db")
async def cmd_db(ctx: commands.Context):
    db_data = get_mariadb_telemetry()
    embed = discord.Embed(
        title=i18n.t("bot.db_title", "ServerDeck Database Engine"),
        color=0x00f0ff
    )
    if not db_data.get("available", False):
        embed.description = i18n.t("bot.db_unavailable", "MariaDB service is not running.")
    else:
        embed.add_field(
            name="Databases",
            value=f"Total: `{db_data['total_count']}` | System: `{db_data['sys_count']}`",
            inline=True
        )
        embed.add_field(
            name="Total Size",
            value=f"`{db_data['total_size_mb']:.2f} MB`",
            inline=True
        )
        db_list_text = "\n".join([f"• `{db['name']}` ({db['size_mb']} MB, {db['tables']} tables)" for db in db_data['databases'][:8]])
        embed.add_field(name="Schemas", value=db_list_text or "None", inline=False)

        users = db_data.get("users", [])
        if users:
            u_lines = "\n".join([f"• `{u['user']}`@`{u['host']}` ({'System' if u.get('is_system') else 'Standard'})" for u in users[:6]])
            embed.add_field(name=f"User Accounts ({len(users)})", value=u_lines or "None", inline=False)

    await ctx.send(embed=embed)

@tree.command(name="db", description="Inspect MariaDB/MySQL databases and status")
async def slash_db(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    try:
        db_data = get_mariadb_telemetry()
        embed = discord.Embed(
            title=i18n.t("bot.db_title", "ServerDeck Database Engine"),
            color=0x00f0ff
        )
        if not db_data.get("available", False):
            embed.description = i18n.t("bot.db_unavailable", "MariaDB service is not running.")
        else:
            embed.add_field(
                name="Databases",
                value=f"Total: `{db_data['total_count']}` | System: `{db_data['sys_count']}`",
                inline=True
            )
            embed.add_field(
                name="Total Size",
                value=f"`{db_data['total_size_mb']:.2f} MB`",
                inline=True
            )
            db_list_text = "\n".join([f"• `{db['name']}` ({db['size_mb']} MB, {db['tables']} tables)" for db in db_data['databases'][:8]])
            embed.add_field(name="Schemas", value=db_list_text or "None", inline=False)

            users = db_data.get("users", [])
            if users:
                u_lines = "\n".join([f"• `{u['user']}`@`{u['host']}` ({'System' if u.get('is_system') else 'Standard'})" for u in users[:6]])
                embed.add_field(name=f"User Accounts ({len(users)})", value=u_lines or "None", inline=False)

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(content=f"Error inspecting databases: `{str(e)}`")

@bot.command(name="restart")
async def cmd_restart(ctx: commands.Context, service_name: str):
    if not is_authorized(ctx.author.id, getattr(ctx.author, "roles", None)):
        await ctx.send("Access Denied: You do not have permission to restart services.")
        return

    containers = get_docker_containers()
    found_c = [c for c in containers if c["name"] == service_name or c["id"].startswith(service_name)]
    if found_c:
        ok, msg = docker_container_action(found_c[0]["id"], "restart")
        color = 0x00ff9d if ok else 0xf43f5e
        await ctx.send(embed=discord.Embed(title="Container Restart", description=msg, color=color))
        return

    try:
        res = subprocess.run(["systemctl", "restart", service_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10.0)
        if res.returncode == 0:
            await ctx.send(embed=discord.Embed(title="Service Restart", description=f"Successfully restarted service `{service_name}`", color=0x00ff9d))
        else:
            await ctx.send(embed=discord.Embed(title="Service Restart Error", description=f"Failed to restart service `{service_name}` (Exit code: {res.returncode})", color=0xf43f5e))
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Service Restart Error", description=f"Error executing restart: {e}", color=0xf43f5e))

@tree.command(name="restart", description="Restart a service or Docker container (Admin only)")
@app_commands.describe(service_name="Name of systemd service or Docker container")
async def slash_restart(interaction: discord.Interaction, service_name: str):
    if not is_authorized(interaction.user.id, getattr(interaction.user, "roles", None)):
        await interaction.response.send_message("Access Denied: You do not have permission to restart services.", ephemeral=True)
        return

    containers = get_docker_containers()
    found_c = [c for c in containers if c["name"] == service_name or c["id"].startswith(service_name)]
    if found_c:
        ok, msg = docker_container_action(found_c[0]["id"], "restart")
        color = 0x00ff9d if ok else 0xf43f5e
        await interaction.response.send_message(embed=discord.Embed(title="Container Restart", description=msg, color=color))
        return

    try:
        res = subprocess.run(["systemctl", "restart", service_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10.0)
        if res.returncode == 0:
            await interaction.response.send_message(embed=discord.Embed(title="Service Restart", description=f"Successfully restarted service `{service_name}`", color=0x00ff9d))
        else:
            await interaction.response.send_message(embed=discord.Embed(title="Service Restart Error", description=f"Failed to restart service `{service_name}`", color=0xf43f5e))
    except Exception as e:
        await interaction.response.send_message(embed=discord.Embed(title="Service Restart Error", description=f"Error: {e}", color=0xf43f5e))

@bot.command(name="alert")
async def cmd_alert(ctx: commands.Context):
    c = load_bot_config()
    thresholds = c.get("alert_thresholds", {})
    stats = get_all_device_stats()
    cpu_pct = stats.get("cpu", {}).get("usage_percent", 0.0)
    ram_pct = stats.get("memory", {}).get("ram_percent", 0.0)
    disks = stats.get("disks", [])
    disk_pct = disks[0].get("percent", 0.0) if disks else 0.0

    embed = discord.Embed(title="ServerDeck Hardware Watchdog Thresholds", color=0x00f0ff)
    embed.add_field(name="CPU Threshold", value=f"Current: `{cpu_pct:.1f}%` / Limit: `{thresholds.get('cpu_percent', 90.0)}%`", inline=True)
    embed.add_field(name="RAM Threshold", value=f"Current: `{ram_pct:.1f}%` / Limit: `{thresholds.get('ram_percent', 90.0)}%`", inline=True)
    embed.add_field(name="Disk Threshold", value=f"Current: `{disk_pct:.1f}%` / Limit: `{thresholds.get('disk_percent', 90.0)}%`", inline=True)
    embed.set_footer(text=f"ServerDeck | {time.strftime('%Y-%m-%d %H:%M:%S')}")
    await ctx.send(embed=embed)

@tree.command(name="alert", description="Show current hardware sensor readings and configured thresholds")
async def slash_alert(interaction: discord.Interaction):
    c = load_bot_config()
    thresholds = c.get("alert_thresholds", {})
    stats = get_all_device_stats()
    cpu_pct = stats.get("cpu", {}).get("usage_percent", 0.0)
    ram_pct = stats.get("memory", {}).get("ram_percent", 0.0)
    disks = stats.get("disks", [])
    disk_pct = disks[0].get("percent", 0.0) if disks else 0.0

    embed = discord.Embed(title="ServerDeck Hardware Watchdog Thresholds", color=0x00f0ff)
    embed.add_field(name="CPU Threshold", value=f"Current: `{cpu_pct:.1f}%` / Limit: `{thresholds.get('cpu_percent', 90.0)}%`", inline=True)
    embed.add_field(name="RAM Threshold", value=f"Current: `{ram_pct:.1f}%` / Limit: `{thresholds.get('ram_percent', 90.0)}%`", inline=True)
    embed.add_field(name="Disk Threshold", value=f"Current: `{disk_pct:.1f}%` / Limit: `{thresholds.get('disk_percent', 90.0)}%`", inline=True)
    embed.set_footer(text=f"ServerDeck | {time.strftime('%Y-%m-%d %H:%M:%S')}")
    await interaction.response.send_message(embed=embed)

@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    embed = discord.Embed(
        title="ServerDeck Discord Bot Commands",
        description="Monitoring and management tools for Linux servers.",
        color=0x00f0ff
    )
    embed.add_field(name="`!status` / `/status`", value="Display live server telemetry embed (CPU, RAM, Disks, Net, Top Procs)", inline=False)
    embed.add_field(name="`!docker` / `/docker`", value="List and manage Docker containers (`!docker start/stop/restart <name>`)", inline=False)
    embed.add_field(name="`!db` / `/db`", value="Inspect MariaDB databases, schemas, sizes, and user accounts", inline=False)
    embed.add_field(name="`!restart <name>` / `/restart`", value="Restart a systemd service or Docker container (Admin only)", inline=False)
    embed.add_field(name="`!alert` / `/alert`", value="View current resource readings and alert threshold limits", inline=False)
    embed.set_footer(text=f"ServerDeck | Prefix: {prefix}")
    await ctx.send(embed=embed)

@tree.command(name="help", description="Display ServerDeck bot commands and guide")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="ServerDeck Discord Bot Commands",
        description="Monitoring and management tools for Linux servers.",
        color=0x00f0ff
    )
    embed.add_field(name="`/status`", value="Display live server telemetry embed (CPU, RAM, Disks, Net, Top Procs)", inline=False)
    embed.add_field(name="`/docker`", value="List and manage Docker containers (`/docker action:restart target:nginx`)", inline=False)
    embed.add_field(name="`/db`", value="Inspect MariaDB databases, schemas, sizes, and user accounts", inline=False)
    embed.add_field(name="`/restart <name>`", value="Restart a systemd service or Docker container (Admin only)", inline=False)
    embed.add_field(name="`/alert`", value="View current resource readings and alert threshold limits", inline=False)
    embed.set_footer(text=f"ServerDeck | Prefix: {prefix}")
    await interaction.response.send_message(embed=embed)

def main():
    global token
    c = load_bot_config()
    bs = c.get("bot_settings", {})
    token = bs.get("bot_token", "").strip()

    if not token:
        print("[notice] ServerDeck Discord Bot is not running: 'bot_token' is empty in bot.yaml.")
        print("[notice] To activate the Discord Bot:")
        print("  1. Create a Discord Bot Application at https://discord.com/developers/applications")
        print("  2. Paste your bot token into bot.yaml under 'bot_token'")
        print("  3. Start the bot: serverdeck-bot or python3 bot/main.py")
        return

    print("[info] Starting ServerDeck Discord Bot Daemon...")
    try:
        bot.run(token)
    except Exception as e:
        print(f"[err] Bot run error: {e}")

if __name__ == "__main__":
    main()
