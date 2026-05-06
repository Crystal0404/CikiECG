import asyncio
import time
from asyncio import CancelledError, Task
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread, Event

from cryptography.fernet import Fernet, InvalidToken
from mcdreforged import *
from pydantic import ValidationError

from ciki_ecg.data import Data
from ciki_ecg.mcdr import CONFIG
from ciki_ecg.mcdr.event import *


class UdpClient:
    def __init__(self):
        self.ttl = CONFIG.decrypt.ttl
        self.fernet = Fernet(CONFIG.decrypt.aes_key)

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
        if self.thread.is_alive():
            self.thread.join()

    def _shutdown(self):
        self.event.set()

    def _thread_entry(self):
        asyncio.run(self._async_main())

    async def _async_main(self):
        self.si.logger.info(self.si.rtr("ciki_ecg.task_start", self.client[0], self.client[1]))
        task = asyncio.create_task(self._receive_loop())
        asyncio.create_task(self._await_stop_signal(task))
        await task
        self.si.logger.info(self.si.rtr("ciki_ecg.task_stop"))

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
            self.si.rtr("ciki_ecg.stop", RText(count, color=RColor.red))
        )
        if count <= 0:
            self._shutdown()
            self.si.stop_exit()
            self.si.wait_until_stop()
            self.si.dispatch_event(SERVER_STOP, ())

    def _refresh_status(self, data: Data):
        if self.online and not data.online:
            self.si.broadcast(
                RTextBase.format(
                    "{}: {}",
                    RText(self.si.rtr("ciki_ecg.warning"), color=RColor.red),
                    self.si.rtr("ciki_ecg.power_off")
                )
            )
            self.si.dispatch_event(POWER_OFF, ())
        if not self.online and data.online:
            self.si.broadcast(RText(self.si.rtr("ciki_ecg.power_on"), color=RColor.green))
            self.si.dispatch_event(POWER_ON, ())

        self.online = data.online
        self.time = data.time

    def get_data(self, data: bytes) -> Data | None:
        try:
            data_str = self.fernet.decrypt_at_time(data, self.ttl, int(time.time())).decode("utf-8")
            data = Data.model_validate_json(data_str)
        except (InvalidToken, ValidationError):
            return None
        else:
            return data


INSTANCE = UdpClient()
