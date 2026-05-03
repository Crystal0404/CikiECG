from ciki_ecg.mcdr import CONFIG
from ciki_ecg.data import Data
from ciki_ecg.mcdr.event import *
from socket import socket, AF_INET, SOCK_DGRAM
from pydantic import ValidationError
from mcdreforged import *
from asyncio import CancelledError, Task
from threading import Thread, Event

import asyncio


class UdpClient:
    def __init__(self):
        self.event = Event()

        self.si = PluginServerInterface.get_instance()
        self.client = (CONFIG.ip, CONFIG.port)

        self.online = True
        self.time = 0

        self.thread = Thread(target=self._thread_entry, daemon=True, name="CikiECG")

    def start(self):
        self.thread.start()

    def shutdown_with_blocking(self):
        self._shutdown()
        self.thread.join()

    def _shutdown(self):
        self.event.set()

    def _thread_entry(self):
        asyncio.run(self._async_main())

    async def _async_main(self):
        self.si.logger.info("Start the listening task")
        task = asyncio.create_task(self._receive_loop())
        asyncio.create_task(self._await_stop_signal(task))
        await task
        self.si.logger.info("Stop the listening task")

    async def _await_stop_signal(self, task: Task):
        await asyncio.to_thread(self.event.wait)
        task.cancel()

    async def _receive_loop(self):
        with socket(AF_INET, SOCK_DGRAM) as s:
            s.bind(self.client)
            await self._handle_datagram_loop(s)

    async def _handle_datagram_loop(self, s: socket):
        loop = asyncio.get_running_loop()
        while True:
            try:
                b_data, _ = await loop.sock_recvfrom(s, 1024)
            except CancelledError:
                break
            data = self.get_data(b_data)
            if data is None: continue
            self._refresh_status(data)
            self._check_close_server()

    def _check_close_server(self):
        if self.online: return
        count = CONFIG.stop_count - self.time
        self.si.broadcast(
            RTextBase.format("服务器将于{}次重试失败后关闭", RText(count, color=RColor.red))
        )
        if count <= 0:
            self._shutdown()
            self.si.stop_exit()
            self.si.wait_until_stop()
            self.si.dispatch_event(SERVER_STOP, ())

    def _refresh_status(self, data: Data):
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
