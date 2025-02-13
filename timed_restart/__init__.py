import time
import json
import os
import threading
import datetime
from mcdreforged.api.all import *

PLUGIN_METADATA = {
    'id': 'timed_restart',
    'version': '1.3.0',
    'name': 'Timed Restart',
    'description': '定时重启服务器，支持时区设置、提前预警和配置热加载',
    'author': 'QingMo'
}

# 配置文件路径
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# 服务器实例
server_instance: PluginServerInterface = None

# 默认配置（如果 config.json 不存在）
default_config = {
    "restart_times": ["06:00", "12:00", "18:00", "00:00"],  # 24小时制
    "warning_minutes": [5, 3, 1],  # 预警时间（分钟）
    "timezone": 8  # 默认东八区
}

# 变量存储配置
restart_times = []
warning_minutes = []
timezone_offset = 8  # 默认东八区


def load_config():
    """ 加载配置文件 """
    global restart_times, warning_minutes, timezone_offset
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        restart_times[:] = default_config["restart_times"]
        warning_minutes[:] = default_config["warning_minutes"]
        timezone_offset = default_config["timezone"]
        return

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            restart_times[:] = config.get("restart_times", default_config["restart_times"])
            warning_minutes[:] = config.get("warning_minutes", default_config["warning_minutes"])
            timezone_offset = config.get("timezone", default_config["timezone"])
            server_instance.logger.info(
                f"配置文件已加载：{restart_times}，预警时间：{warning_minutes}，时区：UTC{timezone_offset}"
            )
    except Exception as e:
        server_instance.logger.warning(f"配置文件加载失败，使用默认值：{e}")
        restart_times[:] = default_config["restart_times"]
        warning_minutes[:] = default_config["warning_minutes"]
        timezone_offset = default_config["timezone"]


def get_local_time():
    """ 获取当前时区的时间（格式 HH:MM） """
    utc_now = datetime.datetime.utcnow()
    local_time = utc_now + datetime.timedelta(hours=timezone_offset)
    return local_time.strftime("%H:%M")


def check_restart_schedule():
    """ 定时检查是否需要重启 """
    while True:
        now = get_local_time()
        for restart_time in restart_times:
            for warning in warning_minutes:
                warning_time = calculate_warning_time(restart_time, warning)
                if now == warning_time:
                    server_instance.say(f"服务器将在 {warning} 分钟后重启，请保存进度！")
                    server_instance.logger.info(f"发送重启预警：{warning} 分钟后重启")

            if now == restart_time:
                warn_and_restart()
                time.sleep(60)  # 避免重复触发

        time.sleep(10)  # 每 10 秒检查一次


def calculate_warning_time(restart_time, warning_minutes):
    """ 计算预警触发时间 """
    restart_hour, restart_minute = map(int, restart_time.split(":"))
    warning_time = datetime.datetime(2000, 1, 1, restart_hour, restart_minute) - datetime.timedelta(minutes=warning_minutes)
    return warning_time.strftime("%H:%M")


def warn_and_restart():
    """ 发送最终重启通知并执行重启 """
    server_instance.say("服务器正在重启...")
    time.sleep(2)  # 确保消息发送完毕
    server_instance.restart()


def on_load(server: PluginServerInterface, old_module):
    global server_instance
    server_instance = server
    server.logger.info("TimedRestart 插件已加载！")

    # 读取配置
    load_config()

    # 启动定时器线程
    restart_thread = threading.Thread(target=check_restart_schedule, daemon=True)
    restart_thread.start()

    # 注册命令
    server.register_command(
        Literal('!restart').then(
            Literal('reload').runs(run_reload_command)
        )
    )


def run_reload_command(source: CommandSource):
    """ 重新加载配置 """
    load_config()
    source.reply(f"TimedRestart 配置已重新加载！当前时区：UTC{timezone_offset}")
