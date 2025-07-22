import os
import socket
import threading
import time

from mcdreforged.api.decorator import event_listener
from mcdreforged.minecraft.rtext.style import RColor
from mcdreforged.minecraft.rtext.text import RText, RTextBase
from mcdreforged.plugin.si.plugin_server_interface import PluginServerInterface
from mcstatus import JavaServer
from ping3 import ping

from ciki_ecg.constant import POWER_OFF, POWER_ON, SERVER_STOP, COMPUTER_STOP

config = {
    "ping": {
        "ip": "192.168.0.1",
        "timeout": 4,
        "interval_time": 180,
        "failed_try": 1
    },
    "backup": True,
    "close_server": {
        "enable": True,
        "try": 1
    },
    "shutdown": {
        "enable": False,
        "wait_time": 60
    },
    "server": []
}
default_config = config.copy()
backup_condition = threading.Condition()
backup_is_run = False


def heart(event):
    thread = None
    backup = False
    flag = False
    close_server_try = config.get("close_server").get("try")

    def start_thread():
        nonlocal thread
        if thread is None:
            thread = threading.Thread(target=__worker, daemon=True, args=(event,), name="CIkiECG")
            thread.start()

    def __worker(work_event: threading.Event):
        nonlocal backup, close_server_try, flag
        global backup_is_run
        while not work_event.is_set():
            if not try_ping():
                if not flag:
                    PluginServerInterface.get_instance().broadcast(
                        RTextBase.format("{}: 检测到服务器停电!", RText("警告", color=RColor.red))
                    )
                    PluginServerInterface.get_instance().dispatch_event(POWER_OFF, ())
                    flag = True

                if (not backup) and config.get("backup"):
                    PluginServerInterface.get_instance().broadcast(
                        "开始自动备份"
                    )
                    PluginServerInterface.get_instance().execute_command("!!qb make 停电备份")
                    backup_is_run = True
                    backup = True

                if config.get("close_server").get("enable"):
                    close_server_try -= 1
                    if close_server_try <= 0:
                        for i in range(5, 0, -1):
                            PluginServerInterface.get_instance().broadcast(
                                RTextBase.format("服务器将在{}秒后自动关闭", RText(str(i), color=RColor.red))
                            )
                            time.sleep(1)
                        PluginServerInterface.get_instance().broadcast(
                            RText("服务器即将关闭", color=RColor.red)
                        )
                        close()
                        break
                    else:
                        PluginServerInterface.get_instance().broadcast(
                            RTextBase.format("服务器将在{}次尝试后关闭", RText(str(close_server_try), color=RColor.red))
                        )

            else:
                if flag:
                    PluginServerInterface.get_instance().broadcast(
                        RText("服务器恢复供电, 取消操作", color=RColor.green)
                    )
                    PluginServerInterface.get_instance().dispatch_event(POWER_ON, ())
                reset()
            work_event.wait(timeout=config.get("ping").get("interval_time"))

    def reset():
        nonlocal backup, close_server_try, flag
        backup = False
        flag = False
        close_server_try = config.get("close_server").get("try")

    def close():
        global backup_is_run
        with backup_condition:
            while backup_is_run:
                backup_condition.wait(timeout=300)
            PluginServerInterface.get_instance().stop()
            PluginServerInterface.get_instance().wait_until_stop()
            PluginServerInterface.get_instance().dispatch_event(SERVER_STOP, ())

            if config.get("shutdown").get("enable"):
                while True:
                    num = 0
                    for e in config.get("server"):
                        if not server_is_online(e):
                            num += 1
                    if num == len(config.get("server")):
                        break
                    time.sleep(5)
                os.system("shutdown -s -t {}".format(str(config.get("shutdown").get("wait_time"))))
                PluginServerInterface.get_instance().dispatch_event(COMPUTER_STOP, (config.get("shutdown").get("wait_time"),))

            PluginServerInterface.get_instance().exit()

    return start_thread


stop_event = threading.Event()
main_heart = heart(stop_event)


def on_load(server: PluginServerInterface, prev_module):
    global config
    config = server.load_config_simple("CikiECG.json", default_config=default_config)
    main_heart()


def on_unload(server: PluginServerInterface):
    global stop_event
    stop_event.set()


@event_listener("quick_backup_multi.backup_done")
def backup_done(server: PluginServerInterface, arg1, arg2):
    global backup_is_run
    with backup_condition:
        backup_condition.notify_all()
    backup_is_run = False


def is_save() -> bool:
    server_ping = ping(config.get("ping").get("ip"), timeout=config.get("ping").get("timeout"))
    if server_ping is False:
        return False
    elif server_ping is None:
        return False
    else:
        return True


def try_ping() -> bool:
    if is_save():
        return True
    else:
        for i in range(config.get("ping").get("failed_try")):
            if is_save():
                return True
            time.sleep(1)
        return False


def server_is_online(ip: str) -> bool:
    try:
        java_server = JavaServer.lookup(ip)
        java_server.status()
        return True
    except ConnectionRefusedError:
        return False
    except socket.gaierror:
        return False
