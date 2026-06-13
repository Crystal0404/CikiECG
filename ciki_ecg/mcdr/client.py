import asyncio
import time
from asyncio import CancelledError, Task, TaskGroup
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread, Event

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.padding import PKCS7
from mcdreforged import *
from pydantic import ValidationError

from ciki_ecg.data import Data
from ciki_ecg.mcdr import CONFIG
from ciki_ecg.mcdr.event import *


class UdpClient:
    def __init__(self):
        # AES instance
        self._ttl = CONFIG.decrypt.ttl
        self._fernet = Fernet(CONFIG.decrypt.aes_key)

        # config and mcdr
        self._si = PluginServerInterface.get_instance()
        self._client = (CONFIG.ip, CONFIG.port)
        self._timeout = CONFIG.timeout
        self._should_stop = CONFIG.stop
        self._stop_count = CONFIG.stop_count

        # status
        self._online = True
        self._time = 0

        # threading
        self._event = Event()
        self._thread = Thread(target=self._thread_entry, daemon=True, name="CikiECG")

        # error log
        self._first = True

    def start(self):
        """
        Start receiving
        :return: None
        """
        self._thread.start()

    def shutdown_with_blocking(self):
        """
        Stop receiving and block until fully stopped
        :return: None
        """
        self._shutdown()
        if self._thread.is_alive():
            self._thread.join()

    def _shutdown(self):
        self._event.set()

    def _thread_entry(self):
        asyncio.run(self._async_main())

    async def _async_main(self):
        self._si.logger.info(self._si.rtr("ciki_ecg.task_start"))
        async with TaskGroup() as tg:
            task = tg.create_task(self._receive_loop())
            tg.create_task(self._await_stop_signal(task))
        self._si.logger.info(self._si.rtr("ciki_ecg.task_stop"))

    async def _await_stop_signal(self, task: Task):
        await asyncio.to_thread(self._event.wait)
        task.cancel()

    async def _receive_loop(self):
        with socket(AF_INET, SOCK_DGRAM) as s:
            s.bind(self._client)
            await self._handle_datagram_loop(s)

    async def _handle_datagram_loop(self, s: socket):
        while True:
            try:
                async with asyncio.timeout(self._timeout):
                    data = await self._recv(s)
            except TimeoutError:
                self._si.logger.warning(self._si.rtr("ciki_ecg.timeout", self._timeout))
                self._stop_server()
                break
            except CancelledError:
                break
            else:
                self._refresh_status(data)
                self._check_close_server()

    async def _recv(self, s: socket) -> Data:
        loop = asyncio.get_running_loop()
        while True:
            b_data, _ = await loop.sock_recvfrom(s, 1024)
            data = self._get_data(b_data)
            if data is not None:
                return data

    def _check_close_server(self):
        if self._online or not self._should_stop: return

        count = self._stop_count - self._time
        if count > 0:
            self._si.broadcast(
                self._si.rtr("ciki_ecg.stop_try", RText(count, color=RColor.red))
            )
        else:
            self._si.broadcast(RText(self._si.rtr("ciki_ecg.stop"), color=RColor.red))
            self._stop_server()

    def _stop_server(self):
        self._shutdown()
        self._si.stop_exit()
        self._si.wait_until_stop()
        self._si.dispatch_event(SERVER_STOP, ())

    def _refresh_status(self, data: Data):
        if self._online and not data.online:
            self._si.broadcast(
                RTextBase.format(
                    "{}: {}",
                    RText(self._si.rtr("ciki_ecg.warning"), color=RColor.red),
                    self._si.rtr("ciki_ecg.power_off")
                )
            )
            self._si.dispatch_event(POWER_OFF, ())
        if not self._online and data.online:
            self._si.broadcast(RText(self._si.rtr("ciki_ecg.power_on"), color=RColor.green))
            self._si.dispatch_event(POWER_ON, ())

        self._online = data.online
        self._time = data.time

    def _get_data(self, data: bytes) -> Data | None:
        try:
            padder_data_byte = self._fernet.decrypt_at_time(data, self._ttl, int(time.time()))
            unpadder = PKCS7(304).unpadder()
            data_byte = unpadder.update(padder_data_byte)
            data_byte += unpadder.finalize()
            data = Data.model_validate_json(data_byte)
        except InvalidToken:
            return None
        except (ValueError, ValidationError):
            if self._first:
                self._first = False
                self._si.logger.error(self._si.rtr("ciki_ecg.parsing_error"))
            return None
        else:
            self._first = True
            return data


INSTANCE = UdpClient()
