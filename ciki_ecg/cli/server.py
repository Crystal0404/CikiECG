import asyncio
import subprocess
import time
from asyncio import Event, CancelledError, Task, AbstractEventLoop
from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread

from cryptography.fernet import Fernet
from ping3 import ping

from ciki_ecg.cli.config import config
from ciki_ecg.cli.logutil import LOG
from ciki_ecg.data import Data


def _is_online() -> bool:
    try:
        status = ping(config().ip, timeout=config().timeout)
    except OSError:
        return False
    else:
        if status is None:
            return False
        else:
            return status is not False


class UdpServer:
    def __init__(self):
        configs = config()

        # AES instance
        self._fernet = Fernet(configs.aes_key)

        # config
        self._interval = configs.interval
        self._bind = (configs.server_bind.ip, configs.server_bind.port)
        self._clients = configs.clients
        self._fail_try = configs.fail_try
        self._should_shutdown = configs.shutdown
        self._shutdown_time = configs.shutdown_time

        # status
        self._online = True
        self._time = 0

    def start(self):
        """
        Start CLI
        :return: None
        """
        asyncio.run(self._async_main())
        LOG.info("bye~")

    async def _async_main(self):
        loop = asyncio.get_running_loop()
        broadcast_task = asyncio.create_task(self._async_broadcast())
        thread = Thread(target=self._input_thread, args=(broadcast_task, loop,), daemon=True)
        thread.start()
        await broadcast_task

    @staticmethod
    def _input_thread(task: Task, loop: AbstractEventLoop):
        while True:
            input_str = input()
            if input_str == "stop":
                loop.call_soon_threadsafe(task.cancel, ())
                break
            else:
                LOG.error("Unknown command")

    async def _async_broadcast(self):
        with socket(AF_INET, SOCK_DGRAM) as server:
            server.bind(self._bind)
            LOG.info(f"successfully started and bound to {self._bind[0]}:{self._bind[1]}")
            await self._broadcast_loop(server)

    async def _broadcast_loop(self, server: socket):
        event = Event()
        while True:
            self._refresh_status()
            self._send(server)
            self._check_shutdown_condition(event)
            if event.is_set(): break
            try:
                await asyncio.sleep(self._interval)
            except CancelledError:
                break

    def _send(self, server: socket):
        for e in self._clients:
            client = (e.ip, e.port)
            server.sendto(self._get_data(), client)

    def _check_shutdown_condition(self, event: Event):
        if self._time > self._fail_try:
            event.set()
            LOG.info("The server has not been powered for a long time, and the program is about to exit")
            if self._should_shutdown:
                self._shutdown()

    def _shutdown(self):
        LOG.info(f"The server will be down after {self._shutdown_time}s")
        subprocess.run(["shutdown", "/s", "/t", f"{self._shutdown_time}"])

    def _get_data(self) -> bytes:
        data = Data(online=self._online, time=self._time)
        data_byte = data.model_dump_json().encode("utf-8")
        token = self._fernet.encrypt_at_time(data_byte, int(time.time()))
        return token

    def _refresh_status(self):
        online = _is_online()

        if (self._time != 0) and online:
            LOG.info("The server is powered back")
        if (self._time == 0) and not online:
            LOG.warning("The server is detected to stop powering")

        if online:
            self._online = True
            self._time = 0
        else:
            self._online = False
            self._time += 1


INSTANCE = UdpServer()
