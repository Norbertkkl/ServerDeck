#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

import app
from serverdeck.core.i18n import i18n


def show_interactive_menu():
    app.print_banner()
    print("\nSelect a debug or inspection action:")
    print("  [ 1] Render Tab 1 (Hardware & System Vitals)")
    print("  [ 2] Render Tab 2 (Processes Table)")
    print("  [ 3] Render Tab 3 (Network Interfaces & Throughput)")
    print("  [ 4] Render Tab 4 (Hardware Sensors & Temperatures)")
    print("  [ 5] Render Tab 5 (Disks, Partitions & SMART Health)")
    print("  [ 6] Render Tab 6 (Kernel Memory & Core Services)")
    print("  [ 7] Render Tab 7 (Databases & Docker Containers)")
    print("  [ 8] Render Tab 8 (UFW Firewall Rules & Policies)")
    print("  [ 9] Render Tab 9 (Software Hub 38 Packages)")
    print("  [10] Render ALL 9 Tabs Sequentially")
    print("  [11] Run Full System Diagnostics & Health Check")
    print("  [12] Benchmark Telemetry Collector Latencies")
    print("  [13] Dump Full Telemetry JSON Snapshot")
    print("  [ 0] Exit")
    print("───────────────────────────────────────────────────────────────────────────────")

    try:
        choice = input("Enter option [0-13]: ").strip()
        if not choice or choice == "0":
            print("\nExiting debug utility.")
            return
        c_int = int(choice)
        if 1 <= c_int <= 9:
            app.render_static_tab(c_int)
        elif c_int == 10:
            for t in range(1, 10):
                app.render_static_tab(t)
        elif c_int == 11:
            app.run_diagnostics()
        elif c_int == 12:
            benchmark_collectors()
        elif c_int == 13:
            st = app.get_all_device_stats()
            print(json.dumps(st, indent=2, default=str))
        else:
            print(f"Invalid option: {choice}")
    except (KeyboardInterrupt, EOFError):
        print("\nExiting debug utility.")


def benchmark_collectors():
    print("\n[*] Benchmarking ServerDeck Telemetry Collectors (5 iterations each)...")
    tests = [
        ("Full Device Stats", app.get_all_device_stats),
        ("Process Table (limit=16)", lambda: app.get_detailed_processes(limit=16)),
        ("MariaDB / MySQL Query", app.get_mariadb_databases),
        ("Docker Container Inspection", app.get_docker_containers),
        ("Disks & Partition Layout", app.get_block_devices_and_partitions),
        ("Hardware Thermal Sensors", app.get_thermal_sensors),
        ("Software Hub (38 Packages)", lambda: app.get_software_hub_status(force=True)),
        ("UFW Firewall Rules", app.get_ufw_status),
    ]

    print("┌─────────────────────────────┬───────────┬───────────┬───────────┐")
    print("│ Collector Name              │ Min Lat   │ Avg Lat   │ Max Lat   │")
    print("├─────────────────────────────┼───────────┼───────────┼───────────┤")

    for name, fn in tests:
        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            try:
                fn()
            except Exception:
                pass
            times.append((time.perf_counter() - t0) * 1000)

        min_t = min(times)
        avg_t = sum(times) / len(times)
        max_t = max(times)
        print(f"│ {name:<27} │ {min_t:7.2f}ms │ {avg_t:7.2f}ms │ {max_t:7.2f}ms │")

    print("└─────────────────────────────┴───────────┴───────────┴───────────┘\n")


def main():
    parser = argparse.ArgumentParser(
        prog="debug.py",
        description="ServerDeck Developer & Admin Diagnostic Utility."
    )
    parser.add_argument("-b", "--banner", action="store_true", help="Print official ServerDeck ASCII banner")
    parser.add_argument("-d", "--diag", "--diagnostics", action="store_true", help="Run full diagnostic suite")
    parser.add_argument("-t", "--tab", type=int, choices=list(range(1, 10)), help="Render static frame of specific tab (1-9)")
    parser.add_argument("-a", "--all-tabs", action="store_true", help="Render all 9 tabs sequentially")
    parser.add_argument("--bench", "--benchmark", action="store_true", help="Benchmark telemetry collector latencies")
    parser.add_argument("-s", "--snapshot", action="store_true", help="Dump telemetry JSON snapshot")

    args = parser.parse_args()

    if args.banner:
        app.print_banner()
    elif args.diag:
        app.run_diagnostics()
    elif args.tab is not None:
        app.render_static_tab(args.tab)
    elif args.all_tabs:
        for t in range(1, 10):
            app.render_static_tab(t)
    elif args.bench:
        benchmark_collectors()
    elif args.snapshot:
        st = app.get_all_device_stats()
        print(json.dumps(st, indent=2, default=str))
    else:
        show_interactive_menu()


if __name__ == "__main__":
    main()
