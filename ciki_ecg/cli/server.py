from ciki_ecg.cli.config import config
from ciki_ecg.cli.logutil import LOG
from ciki_ecg.data import Data
from ping3 import ping
from threading import Thread, Event
from socket import socket, AF_INET, SOCK_DGRAM
from subprocess import run

import signal


def is_online() -> bool:
    status = ping(config().ip, timeout=config().timeout)
    if status is None:
        return False
    else:
        return status is not False

class UdpServer:
    def __init__(self):
        self.event = Event()
        self.interval = config().interval
        self.bind = (config().server_bind.ip, config().server_bind.port)
        self.clients = config().clients
        self.fail_try = config().fail_try
        self.should_shutdown = config().shutdown
        self.shutdown_time = config().shutdown_time

        # server status
        self.online = True
        self.time = 0

        # signal
        signal.signal(signal.SIGINT, self.__signal_handler)

    def __signal_handler(self, *args, **kwargs): # noqa
        self.event.set()
        LOG.info("bye~")

    def run(self):
        send_thread = Thread(target=self.start_broadcast, daemon=True)
        send_thread.start()
        input_thread = Thread(target=self.handle_input, daemon=True)
        input_thread.start()
        send_thread.join()


    def handle_input(self):
        while True:
            i = input()
            if i == "stop":
                self.event.set()
                LOG.info("bye~")
                break
            else:
                LOG.error("unknown instructions")

    def start_broadcast(self):
        with socket(AF_INET, SOCK_DGRAM) as server_socket:
            server_socket.bind(self.bind)
            LOG.info(f"successfully started and bound to {self.bind[0]}:{self.bind[1]}")
            self.broadcast_loop(server_socket)

    def broadcast_loop(self, server: socket):
        while True:
            self.refresh_status()
            self.send(server)
            self.check_shutdown_condition()
            self.event.wait(self.interval)
            if self.event.is_set(): break

    def send(self, server: socket):
        for e in self.clients:
            client = (e.ip, e.port)
            server.sendto(self.get_data(), client)

    def check_shutdown_condition(self):
        if self.time > self.fail_try:
            self.event.set()
            LOG.info("The server has not been powered for a long time, and the program is about to exit")
            if self.should_shutdown:
                self.shutdown_server()

    def shutdown_server(self):
        LOG.info(f"The server will be down after {self.shutdown_time}s")
        run(["shutdown", "/s", "/t", f"{self.shutdown_time}"])

    def refresh_status(self):
        online = is_online()

        if (self.time != 0) and online:
            LOG.info("The server is powered back")

        if (self.time == 0) and not online:
            LOG.warning("The server is detected to stop powering")

        if online:
            self.online = True
            self.time = 0
        else:
            self.online = False
            self.time += 1


    def get_data(self) -> bytes:
        data = Data(online=self.online, time=self.time)
        return data.model_dump_json().encode("utf-8")

if __name__ == "__main__":
    s = UdpServer()
    s.run()
