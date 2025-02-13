import time
import json
import os
import threading
import datetime
from mcdreforged.api.all import *
from mcdreforged.api.command import SimpleCommandBuilder, Integer, Text, GreedyText

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

# 默认配置
default_config = {
    "restart_times": ["06:00", "12:00", "18:00", "00:00"],  # 24小时制
    "warning_minutes": [5, 3, 1],  # 预警时间（分钟）
    "timezone": 8  # 默认东八区
}

# 变量存储配置
restart_times = []
warning_minutes = []
timezone_offset = 8  # 默认东八区


def translate(server: PluginServerInterface, key: str, **kwargs):
    """ 读取 yml 文件中的翻译文本 """
    return server.rtr(key, **kwargs)


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
                translate(server_instance, "timed_restart.system.config_loaded",
                          restart_times=restart_times, warning_minutes=warning_minutes, timezone=timezone_offset)
            )
    except Exception as e:
        server_instance.logger.warning(
            translate(server_instance, "timed_restart.system.error_loading_config", error=str(e))
        )
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
                    server_instance.say(translate(server_instance, "timed_restart.system.restart_warning", minutes=warning))
                    server_instance.logger.info(translate(server_instance, "timed_restart.system.log_restart_warning", minutes=warning))

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
    server_instance.say(translate(server_instance, "timed_restart.system.restart_now"))
    time.sleep(2)  # 确保消息发送完毕
    server_instance.restart()


def on_load(server: PluginServerInterface, old_module):
    global server_instance
    builder = SimpleCommandBuilder()
    server_instance = server

    load_config()
    server.logger.info(translate(server, "timed_restart.system.plugin_loaded"))

    restart_thread = threading.Thread(target=check_restart_schedule, daemon=True)
    restart_thread.start()

    # server.register_command(
    #     Literal('!!timed_restart')
    #     .then(Literal('reload').runs(run_reload_command))
    #     .then(Literal('help').runs(show_help))
    #     .then(Literal('list').runs(show_restart_times))
    #     .then(Literal('add').then(Argument(Text).runs(add_restart_time)))
    #     .then(Literal('remove').then(Argument(Text).runs(remove_restart_time)))
    # )

    # 注册命令
    builder.command('!!timed_restart reload', run_reload_command)
    builder.command('!!timed_restart help', show_help)
    builder.command('!!timed_restart list', show_restart_times)
    builder.command('!!timed_restart add <time>', add_restart_time)
    builder.command('!!timed_restart remove <time>', remove_restart_time)
    builder.command('!!timed_restart timezone <timezone>', set_timezone)

    # 定义参数
    builder.arg('time', Text)
    builder.arg('timezone', Text)

    # 注册命令
    builder.register(server)

def show_help(source: CommandSource):
    """ 显示帮助信息 """
    help_text = str(translate(source.get_server(), "timed_restart.cmd.help"))  # 转换为字符串
    for line in help_text.split("\n"):
        source.reply(RText(line))  # 确保输出格式正确

def show_restart_times(source: CommandSource):
    """ 显示所有重启时间 """
    times_str = ", ".join(restart_times)
    source.reply(translate(server_instance, 'timed_restart.system.list_restart_times', times=times_str))


def add_restart_time(source: CommandSource, time: str):
    """ 添加新的重启时间 """
    global restart_times

    # 检查time是否是字典格式，如果是，提取出'time'键的值
    if isinstance(time, dict) and 'time' in time:
        time = time['time']

    # 如果time是字符串并且不在restart_times中，则添加到列表中
    if time not in restart_times:
        restart_times.append(time)
        save_config()
        source.reply(translate(server_instance, 'timed_restart.system.add_restart_time', time=time))
    else:
        source.reply(translate(server_instance, 'timed_restart.system.restart_time_exists', time=time))


def remove_restart_time(source: CommandSource, time: str):
    """ 删除已设定的重启时间 """
    global restart_times

    # 检查time是否是字典格式，如果是，提取出'time'键的值
    if isinstance(time, dict) and 'time' in time:
        time = time['time']

    # 如果time在restart_times中，则移除它
    if time in restart_times:
        restart_times.remove(time)
        save_config()
        source.reply(translate(server_instance, 'timed_restart.system.remove_restart_time', time=time))
    else:
        source.reply(translate(server_instance, 'timed_restart.system.restart_time_not_exists', time=time))


def set_timezone(source: CommandSource, timezone: str):
    """ 设置新的时区 """
    global timezone_offset  # 确保更新全局变量

    # 检查time是否是字典格式，如果是，提取出'time'键的值
    if isinstance(timezone, dict) and 'timezone' in timezone:
        timezone = timezone['timezone']

    try:
        # 尝试将时区转换为整数
        new_timezone = int(timezone)

        # 检查时区是否合法，假设时区范围是 -12 到 +12
        if new_timezone < -12 or new_timezone > 12:
            source.reply(translate(server_instance, 'timed_restart.system.invalid_timezone'))
            return

        # 更新时区
        timezone_offset = new_timezone  # 更新全局时区变量
        save_config()  # 保存配置文件

        # 回复用户
        source.reply(translate(server_instance, 'timed_restart.system.set_timezone', timezone=new_timezone))

    except ValueError:
        # 如果时区转换失败，返回错误信息
        source.reply(translate(server_instance, 'timed_restart.system.invalid_timezone_format'))

def save_config():
    """ 保存配置到文件 """
    config = {
        "restart_times": restart_times,
        "warning_minutes": warning_minutes,
        "timezone": timezone_offset
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def run_reload_command(source: CommandSource):
    """ 重新加载配置 """
    load_config()
    source.reply(translate(source.get_server(), "timed_restart.system.reload_success", timezone=timezone_offset))
