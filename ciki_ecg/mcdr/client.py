from threading import Thread, Event
from ciki_ecg.mcdr import CONFIG
from ciki_ecg.data import Data
from ciki_ecg.mcdr.event import *
from socket import socket, AF_INET, SOCK_DGRAM
from pydantic import ValidationError
from mcdreforged import *


class UdpClient:
    def __init__(self):
        self.event = Event()
        self.si = PluginServerInterface.get_instance()
        self.online = True
        self.time = 0

        self.thread = Thread(target=self.start_subscription, daemon=True)

    def stop(self):
        self.event.set()
        self.thread.join()

    def run(self):
        self.thread.start()
        self.si.logger.info("start the subscription thread")

    def start_subscription(self):
        with socket(AF_INET, SOCK_DGRAM) as s:
            s.bind((CONFIG.ip, CONFIG.port))
            s.setblocking(False)
            self.subscription_loop(s)

    def subscription_loop(self, s: socket):
        while True:
            try:
                data, _ = s.recvfrom(1024)
            except BlockingIOError:
                self.event.wait(timeout=5)
                if self.event.is_set():
                    self.si.logger.info("stop the subscription thread")
                    break
                else:
                    continue
            data = self.get_data(data)
            if data is None: continue
            self.refresh_status(data)
            self.check_close_condition()

    def check_close_condition(self):
        if self.online: return
        count = CONFIG.stop_time - self.time
        self.si.broadcast(
            RTextBase.format("服务器将于{}次重试失败后关闭", RText(count, color=RColor.red))
        )
        if count <= 0:
            self.event.set()
            self.si.stop_exit()
            self.si.wait_until_stop()
            self.si.dispatch_event(SERVER_STOP, ())


    def refresh_status(self, data: Data):
        if self.online and not data.online:
            self.si.broadcast(
                RTextBase.format("{}: 检测到服务器停电!", RText("警告", color=RColor.red))
            )
            self.si.dispatch_event(POWER_OFF, ())
        if not self.online and data.online:
            self.si.broadcast(RText("服务器恢复供电", color=RColor.green))
            self.si.dispatch_event(POWER_ON, ())

        self.online = data.online
        self.time = data.time

    @staticmethod
    def get_data(data: bytes) -> Data | None:
        data_str = data.decode("utf-8")
        try:
            return Data.model_validate_json(data_str)
        except ValidationError:
            return None

INSTANCE = UdpClient()
