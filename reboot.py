import subprocess
import time
import os

# --- 配置参数 ---
LOOP_COUNT = 100
WAIT_TIME = 120
TZ_LOG = "tzbsp.log"
DEVICE_ID = ""  # 如果有多个设备，请填写序列号，例如 "ZY22GXXXX"

def adb_command(command):
    """执行 adb 命令并返回输出"""
    # 如果指定了 DEVICE_ID，自动在 adb 后添加 -s 参数
    if DEVICE_ID and " -s " not in command:
        command = command.replace("adb ", f"adb -s {DEVICE_ID} ")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def wait_for_device():
    print("等待设备启动中...")
    while True:
        state = adb_command("adb get-state")
        if "device" in state:
            boot_completed = adb_command("adb shell getprop sys.boot_completed")
            if boot_completed == "1":
                print("设备已就绪。")
                break
        time.sleep(5)

def main():
    # 循环 100 轮重启测试
    for i in range(1, LOOP_COUNT + 1):
        print(f"\n--- 开始第 {i}/{LOOP_COUNT} 轮测试 ---")
        
        wait_for_device()
        adb_command("adb root")
        time.sleep(2)
        
        # 异步抓取 TrustZone 日志
        print(f"正在抓取 TZ 日志...")
        tz_process = subprocess.Popen(
            f"adb {'-s ' + DEVICE_ID if DEVICE_ID else ''} shell \"cat /proc/tzdbg/log\" >> {TZ_LOG}", 
            shell=True
        )

        print(f"保持运行 {WAIT_TIME} 秒...")
        time.sleep(WAIT_TIME)

        print("执行重启...")
        tz_process.terminate()
        adb_command("adb reboot")
        
        # 等待设备掉线
        time.sleep(10)

    # --- 100 轮循环结束后执行的操作 ---
    print("\n" + "="*30)
    print("100 轮测试完成，准备触发 Bug2Go 报告...")
    print("="*30)
    
    # 等待最后一轮重启后的系统就绪
    wait_for_device()
    adb_command("adb root")
    time.sleep(2)

    # 启动 Bug2Go Activity
    print("启动 Bug2Go...")
    adb_command(f'adb shell "am start-activity -n com.motorola.bug2go/.StartReportActivity"')
    time.sleep(3)
    
    # 模拟按下 Home 键返回桌面（通常是为了触发后台抓取逻辑）
    print("返回桌面，Bug2Go 正在后台工作...")
    adb_command('adb shell "input keyevent 3"')
    
    # 等待 10 分钟以便生成报告
    print("等待 600 秒以完成报告生成...")
    time.sleep(600)
    
    print("所有流程已结束。")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户已停止测试。")
