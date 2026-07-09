#!/usr/bin/env python3
"""Real-time Android RAM usage monitor based on `adb shell dumpsys meminfo`.

This script polls the device memory info from ADB, parses the RAM-related fields
from `dumpsys meminfo`, and visualizes the current memory usage ratio in real time.

Usage:
    python memory_monitor.py
    python memory_monitor.py --interval 2 --history 60
    python memory_monitor.py --mode plot
"""

import argparse
import os
import re
import subprocess
import sys
import time
from collections import deque
from typing import Optional, Dict, Deque

try:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
except Exception:  # pragma: no cover - optional dependency
    plt = None
    FuncAnimation = None


class MemInfoError(RuntimeError):
    pass


def run_adb(args: list[str]) -> str:
    for attempt in range(2):
        try:
            completed = subprocess.run(
                ["adb", *args],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise MemInfoError("adb is not installed or not available on PATH") from exc

        if completed.returncode == 0:
            return completed.stdout

        output = (completed.stderr or completed.stdout).strip()
        if attempt == 0 and any(token in output.lower() for token in ["server version", "daemon not running", "device offline", "no devices", "not found"]):
            subprocess.run(["adb", "kill-server"], capture_output=True, text=True, check=False)
            subprocess.run(["adb", "start-server"], capture_output=True, text=True, check=False)
            continue

        raise MemInfoError(output or "adb command failed")

    raise MemInfoError("adb command failed after retry")


def parse_size_to_kb(text: str) -> Optional[float]:
    """Parse values like '3752 MB', '2,048 KB', or '7,628,788K' into KB."""
    match = re.search(r"([0-9,\.]+)\s*([KMGTP]?B)?", text, flags=re.IGNORECASE)
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    unit = (match.group(2) or "K").upper()
    if unit == "K" or unit == "KB":
        return amount
    if unit == "MB":
        return amount * 1024
    if unit == "GB":
        return amount * 1024 * 1024
    if unit == "TB":
        return amount * 1024 * 1024 * 1024
    return None


def parse_meminfo(output: str, proc_output: Optional[str] = None) -> Dict[str, float]:
    total_kb: Optional[float] = None
    free_kb: Optional[float] = None
    used_kb: Optional[float] = None
    swap_kb: Optional[float] = None
    available_kb: Optional[float] = None
    cached_kb: Optional[float] = None
    kernel_kb: Optional[float] = None
    reclaimable_kb: Optional[float] = None

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Total RAM:"):
            total_kb = parse_size_to_kb(stripped.split(":", 1)[1])
        elif stripped.startswith("Free RAM:"):
            free_kb = parse_size_to_kb(stripped.split(":", 1)[1])
        elif stripped.startswith("Used RAM:"):
            used_kb = parse_size_to_kb(stripped.split(":", 1)[1])
        elif stripped.startswith("Swap:"):
            swap_kb = parse_size_to_kb(stripped.split(":", 1)[1])
        elif "cached pss" in stripped or "cached kernel" in stripped or "free" in stripped:
            if "cached pss" in stripped:
                cached_kb = parse_size_to_kb(stripped.split("(", 1)[1].split("K cached pss", 1)[0])
            if "cached kernel" in stripped:
                kernel_kb = parse_size_to_kb(stripped.split("cached kernel", 1)[0].split("+")[-1])
            if "free" in stripped and stripped.endswith("free)"):
                reclaimable_kb = parse_size_to_kb(stripped.split("+")[-1].split("K free", 1)[0])

    if total_kb is None or total_kb <= 0:
        if proc_output is None:
            proc_output = run_adb(["shell", "cat", "/proc/meminfo"])

        proc_total = None
        proc_free = None
        proc_available = None
        for line in proc_output.splitlines():
            if line.startswith("MemTotal:"):
                proc_total = parse_size_to_kb(line.split(":", 1)[1])
            elif line.startswith("MemFree:"):
                proc_free = parse_size_to_kb(line.split(":", 1)[1])
            elif line.startswith("MemAvailable:"):
                proc_available = parse_size_to_kb(line.split(":", 1)[1])

        if proc_total is not None and proc_total > 0:
            total_kb = proc_total
            if proc_free is None:
                proc_free = proc_total * 0.1
            free_kb = proc_free
            if proc_available is not None:
                available_kb = proc_available

    if total_kb is None or total_kb <= 0:
        if proc_output is None:
            proc_output = run_adb(["shell", "cat", "/proc/meminfo"])

        proc_total = None
        proc_free = None
        for line in proc_output.splitlines():
            if line.startswith("MemTotal:"):
                proc_total = parse_size_to_kb(line.split(":", 1)[1])
            elif line.startswith("MemFree:"):
                proc_free = parse_size_to_kb(line.split(":", 1)[1])
            elif line.startswith("MemAvailable:") and proc_free is None:
                proc_free = parse_size_to_kb(line.split(":", 1)[1])

        if proc_total is not None and proc_total > 0:
            total_kb = proc_total
            if proc_free is None:
                proc_free = proc_total * 0.1
            free_kb = proc_free

    if total_kb is not None and free_kb is not None:
        used_kb = total_kb - free_kb
    elif used_kb is None and total_kb is not None and free_kb is not None:
        used_kb = total_kb - free_kb
    if free_kb is None and total_kb is not None and used_kb is not None:
        free_kb = total_kb - used_kb

    if total_kb is None or total_kb <= 0:
        raise MemInfoError("Unable to parse total RAM from dumpsys or /proc/meminfo output")

    if available_kb is None and free_kb is not None and total_kb is not None:
        available_kb = max(free_kb, 0)

    usage_ratio = (used_kb or 0) / total_kb
    return {
        "total_kb": total_kb,
        "used_kb": used_kb or 0,
        "free_kb": free_kb or 0,
        "available_kb": available_kb or free_kb or 0,
        "cached_kb": cached_kb or 0,
        "kernel_kb": kernel_kb or 0,
        "reclaimable_kb": reclaimable_kb or 0,
        "swap_kb": swap_kb or 0,
        "usage_ratio": usage_ratio,
    }


def fetch_meminfo() -> Dict[str, float]:
    dumpsys_output = ""
    proc_output = ""
    dumpsys_error = None

    try:
        dumpsys_output = run_adb(["shell", "dumpsys", "meminfo"])
    except MemInfoError as exc:
        dumpsys_error = str(exc)

    try:
        proc_output = run_adb(["shell", "cat", "/proc/meminfo"])
    except MemInfoError:
        proc_output = ""

    if not dumpsys_output and not proc_output:
        raise MemInfoError(dumpsys_error or "Unable to read memory info from device")

    return parse_meminfo(dumpsys_output, proc_output)


def format_kb(value_kb: float) -> str:
    mb = value_kb / 1024.0
    return f"{mb:.1f} MB"


def render_text(stats: Dict[str, float], history: Deque[float]) -> str:
    used_ratio = stats["usage_ratio"]
    bar_width = 30
    filled = int(round(used_ratio * bar_width))
    filled = max(0, min(bar_width, filled))
    bar = "█" * filled + "░" * (bar_width - filled)

    spark = ""
    if history:
        recent = list(history)[-12:]
        if len(recent) > 1:
            spark = "".join("▁▂▃▄▅▆▇█"[int(round(v * 7))] for v in recent)

    swap_text = ""
    if stats.get("swap_kb", 0) > 0:
        swap_text = f"Swap : {format_kb(stats['swap_kb'])}\n"

    available_text = f"Available : {format_kb(stats['available_kb'])}\n"
    cached_text = f"Cached    : {format_kb(stats['cached_kb'])}\n" if stats.get("cached_kb", 0) > 0 else ""
    kernel_text = f"Kernel    : {format_kb(stats['kernel_kb'])}\n" if stats.get("kernel_kb", 0) > 0 else ""
    reclaimable_text = f"Reclaim   : {format_kb(stats['reclaimable_kb'])}\n" if stats.get("reclaimable_kb", 0) > 0 else ""

    return (
        f"RAM usage: {used_ratio * 100:5.1f}%\n"
        f"[{bar}]\n"
        f"Used      : {format_kb(stats['used_kb'])}\n"
        f"Free      : {format_kb(stats['free_kb'])}\n"
        f"{available_text}"
        f"{cached_text}"
        f"{kernel_text}"
        f"{reclaimable_text}"
        f"Total     : {format_kb(stats['total_kb'])}\n"
        f"{swap_text}"
        f"Trend     : {spark}"
    )


def run_text_mode(interval: float, history_limit: int) -> None:
    history: Deque[float] = deque(maxlen=history_limit)
    try:
        while True:
            try:
                stats = fetch_meminfo()
            except MemInfoError as exc:
                os.system("cls" if os.name == "nt" else "clear")
                sys.stdout.write(f"Waiting for device...\n{exc}\n")
                sys.stdout.flush()
                time.sleep(interval)
                continue

            history.append(stats["usage_ratio"])
            os.system("cls" if os.name == "nt" else "clear")
            sys.stdout.write(render_text(stats, history))
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


def run_plot_mode(interval: float, history_limit: int) -> None:
    if plt is None or FuncAnimation is None:
        raise MemInfoError("matplotlib is not available; install it or use the default text mode")

    history: Deque[float] = deque(maxlen=history_limit)
    fig, ax = plt.subplots(figsize=(8, 4))
    line, = ax.plot([], [], lw=2, color="#4c78a8")
    ax.set_ylim(0, 1.0)
    ax.set_xlim(0, history_limit)
    ax.set_title("Android RAM Usage")
    ax.set_ylabel("Usage Ratio")
    ax.set_xlabel("Samples")

    def update(frame):
        try:
            stats = fetch_meminfo()
            history.append(stats["usage_ratio"])
        except MemInfoError as exc:
            ax.set_title(f"Waiting for device... {exc}")
            return line,

        xs = list(range(len(history)))
        ys = list(history)
        line.set_data(xs, ys)
        ax.set_xlim(0, max(history_limit, len(history)))
        ax.set_ylim(0, 1.0)
        ax.set_title(f"Android RAM Usage  {stats['usage_ratio'] * 100:5.1f}%")
        return line,

    animation = FuncAnimation(fig, update, interval=int(interval * 1000), blit=False)
    plt.tight_layout()
    plt.show()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live Android RAM usage monitor")
    parser.add_argument("--interval", type=float, default=1.0, help="Refresh interval in seconds (default: 1.0)")
    parser.add_argument("--history", type=int, default=60, help="Number of samples to keep for trend view")
    parser.add_argument("--mode", choices=["text", "plot"], default="text", help="Visualization mode")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.interval <= 0:
        raise SystemExit("--interval must be greater than 0")

    try:
        if args.mode == "plot":
            run_plot_mode(args.interval, args.history)
        else:
            run_text_mode(args.interval, args.history)
    except MemInfoError as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
