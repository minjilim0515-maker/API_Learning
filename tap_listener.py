import os
import re
import subprocess

def get_screen_resolution():
    """获取手机屏幕分辨率"""
    cmd = "adb shell wm size"
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    match = re.search(r'Physical size: (\d+)x(\d+)', result)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 1080, 2400 # 默认兜底分辨率

def listen_android_clicks():
    width, height = get_screen_resolution()
    print(f"检测到手机分辨率: {width} x {height}")
    print("正在初始化手机触控事件监听... 请在手机屏幕上点击...")
    print("=" * 50)

    # 1. 寻找触控屏幕对应的底层设备输入节点 (通常包含 ABS_MT_POSITION_X)
    # 这里直接使用带有 -l 参数的 getevent 过滤核心触控事件
    # 过滤出包含 ABS_MT_POSITION_X (横坐标) 和 ABS_MT_POSITION_Y (纵坐标) 的数据
    adb_cmd = ["adb", "shell", "getevent", "-l"]
    
    # 启动异步子进程读取 Log
    process = subprocess.Popen(adb_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)

    x_hex, y_hex = None, None

    # 2. 循环读取底层事件流
    while True:
        line = process.stdout.readline().decode('utf-8', errors='ignore')
        if not line:
            break
        
        # 匹配包含坐标的行 (不同的手机节点名字可能略有差异，通常匹配 POSITION_X/Y)
        if "ABS_MT_POSITION_X" in line:
            # 提取最后的十六进制值 (例如: 0000021a)
            match = re.search(r'([0-9a-fA-F]+)$', line.strip())
            if match:
                x_hex = match.group(1)
        
        elif "ABS_MT_POSITION_Y" in line:
            match = re.search(r'([0-9a-fA-F]+)$', line.strip())
            if match:
                y_hex = match.group(1)

        # 3. 当 X 和 Y 都拿到了，代表一次完整的触控点产生了
        if x_hex and y_hex:
            # 十六进制转十进制
            x_val = int(x_hex, 16)
            y_val = int(y_hex, 16)
            
            # 💡 注意：部分安卓底层上报的是触控板的物理采样值(比如0-4095)，需要映射或根据设备校准。
            # 大部分现代高版本系统处理后直接就是绝对坐标，或者是根据最大采样率缩放。
            # 这里先打印出底层抓到的原始坐标：
            print(f"【🔥 检测到触控】 原始十六进制: ({x_hex}, {y_hex}) -> 十进制像素坐标: ({x_val}, {y_val})")
            print(f" 🤖 对应自动化指令: adb shell input tap {x_val} {y_val}")
            print("-" * 50)
            
            # 清空缓存状态，等待下一次点击
            x_hex, y_hex = None, None

if __name__ == "__main__":
    try:
        listen_android_clicks()
    except KeyboardInterrupt:
        print("\n监听已终止。")