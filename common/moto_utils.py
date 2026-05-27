# -*- coding: utf-8 -*-
import subprocess
import time
import os
from datetime import datetime
import threading

# 日志文件放在项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(PROJECT_ROOT, "fp_check.log")


# ========================
# 基础工具
# ========================
def run_cmd(cmd):
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
        return result.decode("utf-8", errors="ignore").strip()
    except:
        return ""


def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ========================
# 设备控制
# ========================
def wait_device():
    log("等待设备连接...")
    subprocess.call("adb wait-for-device", shell=True)
    time.sleep(5)


# ✅ ✅ 修复1：只等 boot_completed
def wait_boot_completed(timeout=120):
    log("等待 boot_completed...")

    start = time.time()
    while time.time() - start < timeout:
        boot = run_cmd("adb shell getprop sys.boot_completed").strip()

        if boot == "1":
            log("boot_completed ✅")
            return True

        time.sleep(2)

    log("boot 超时 ❌")
    return False


# ========================
# 🔓 解锁（提前执行）
# ========================
def unlock_device(pin="1234"):
    log("尝试解锁设备...")
    # input home keyevent 3
    run_cmd("adb shell input keyevent 3")
    time.sleep(1)

    run_cmd("adb shell input swipe 300 1000 300 300")
    time.sleep(1)

    run_cmd(f"adb shell input text {pin}")
    time.sleep(1)

    run_cmd("adb shell input keyevent 66")
    time.sleep(2)

    log("已执行解锁操作")


# ✅ ✅ 更可靠：CE判断
def is_ce_ready():
    val = run_cmd("adb shell getprop sys.user.0.ce_available")
    return val.strip() == "true"


def wait_ce_ready(timeout=30):
    log("等待用户解锁完成（CE ready）...")

    start = time.time()
    while time.time() - start < timeout:
        if is_ce_ready():
            log("CE 已可用 ✅")
            return True

        time.sleep(1)

    log("CE 未 ready ❌")
    return False


# ========================
# 指纹检测
# ========================
def check_fingerprint():
    log("检测指纹模块...")

    fp = run_cmd("adb shell dumpsys fingerprint")
    hw = "FingerprintProvider" in fp

    hal = run_cmd("adb shell ps -ef | grep fingerprint")
    hal_ok = len(hal) > 0

    svc = run_cmd("adb shell service list | grep -i fingerprint")
    svc_ok = len(svc) > 0

    log(f"[RESULT] HAL: {'PASS' if hal_ok else 'FAIL'}")
    log(f"[RESULT] Service: {'PASS' if svc_ok else 'FAIL'}")

    return hw, hal_ok, svc_ok


# ========================
# 🔥 压力模块
# ========================
def cpu_stress():
    run_cmd("adb shell 'while true; do :; done' &")


def io_stress():
    run_cmd("adb shell 'dd if=/dev/zero of=/data/local/tmp/test bs=1M count=200' &")


def capture():
    log("启动相机并触发快门...")
    run_cmd("adb shell am start -W -a android.media.action.IMAGE_CAPTURE")
    time.sleep(1)
    run_cmd("adb shell input keyevent 27")
    time.sleep(1)


def start_stress():
    log("🔥 启动压力")

    threading.Thread(target=cpu_stress).start()
    threading.Thread(target=io_stress).start()
    threading.Thread(target=capture).start()


# 当复现问题时调用：截屏并 pull 到脚本所在目录，然后启动 Bug2Go
def bug2go(device=None, wait_after=600):
    log("开始 bug2go 流程：截屏并 pull 到项目根目录")
    time.sleep(3)
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote = f"/sdcard/screenshot_{current_time}.png"

    adb_prefix = f"adb -s {device} " if device else "adb "

    # 在设备上截屏
    run_cmd(f'{adb_prefix}shell screencap -p {remote}')
    time.sleep(3)

    # 本地路径：项目根目录
    local = os.path.join(PROJECT_ROOT, f"screenshot_{current_time}.png")

    # pull 到本地项目根目录
    log(f"pull {remote} -> {local}")
    run_cmd(f'{adb_prefix}pull {remote} "{local}"')
    time.sleep(10)

    # 启动 Bug2Go Activity 并回到桌面
    run_cmd(f'{adb_prefix}shell am start-activity -n com.motorola.bug2go/.StartReportActivity')
    time.sleep(3)
    run_cmd(f'{adb_prefix}shell input keyevent 3')
    time.sleep(wait_after)
