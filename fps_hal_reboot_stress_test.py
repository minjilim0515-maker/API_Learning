# -*- coding: utf-8 -*-

import subprocess
import time
from datetime import datetime

from common.moto_utils import (
    wait_device,
    wait_boot_completed,
    start_stress,
    unlock_device,
    wait_ce_ready,
    check_fingerprint,
    bug2go,
    log,
)


def reboot_stress(loop=20, pin="1234"):
    for i in range(loop):
        log(f"\n========== 第{i+1}轮 ==========")

        log("执行重启...")
        subprocess.call("adb reboot", shell=True)

        wait_device()

        if not wait_boot_completed():
            continue
        start_stress()
        time.sleep(3)

        unlock_device(pin)

        if not wait_ce_ready():
            log("解锁失败，本轮跳过")
            continue

        time.sleep(5)

        hw, hal, svc = check_fingerprint()

        if hw and hal and svc:
            log("本轮正常 ✅")
        else:
            log("发现异常 ❌")
            bug2go()
            log("日志已保存")
            input("👉 暂停中，回车继续...")

        time.sleep(3)


if __name__ == "__main__":
    # 直接运行 bug2go 调试用，或调用 reboot_stress
    reboot_stress(loop=1000, pin="1234")
