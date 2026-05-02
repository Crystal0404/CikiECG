from pydantic import BaseModel, Field, ConfigDict, ValidationError
from functools import cache
from ciki_ecg.cli.logutil import LOG
from pathlib import Path

__all__ = ["config", "write_config"]


class Client(BaseModel):
    model_config = ConfigDict(strict=True)

    ip: str
    port: int


class Server(BaseModel):
    model_config = ConfigDict(strict=True)

    ip: str = "127.0.0.1"
    port: int = 8888

class Config(BaseModel):
    model_config = ConfigDict(strict=True)

    ip: str = "192.168.0.1"
    timeout: int = 5
    interval: int = 180
    server_bind: Server = Field(default_factory=Server)
    fail_try: int = 3
    shutdown: bool = False
    shutdown_time: int = 600
    clients: list[Client] = Field(default_factory=list)


PATH = Path("config.json")


@cache
def config() -> Config:
    if not PATH.exists():
        LOG.error("Config file not found!")
        raise FileNotFoundError

    with PATH.open("r", encoding="utf-8") as f:
        data = f.read()

    try:
        return Config.model_validate_json(data)
    except ValidationError as e:
        LOG.error("Config file parsing error. Please check it or use 'init' to regenerate.")
        raise e


def write_config():
    with PATH.open("w", encoding="utf-8") as f:
        f.write(Config().model_dump_json(indent=2))
    LOG.info("Successfully created config file!")

if __name__ == "__main__":
    print(config())
