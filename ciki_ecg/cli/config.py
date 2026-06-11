import platform
from functools import cache
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, ConfigDict, ValidationError, field_validator

from ciki_ecg.cli.logutil import LOG

__all__ = ["config", "write_config"]
PATH = Path("config.json")
SHUTDOWN_TIME = {
    "Windows": 300,
    "Linux": 5
}


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
    interval: int = 100
    server_bind: Server = Field(default_factory=Server)
    fail_try: int = Field(default=3, ge=1, lt=0x7FFFFFFF)
    shutdown: bool = False
    shutdown_time: int = Field(default_factory=lambda: SHUTDOWN_TIME.get(platform.system(), 300))
    clients: list[Client] = Field(default_factory=list)
    aes_key: str = Field(default_factory=lambda: Fernet.generate_key().decode("utf-8"))

    @field_validator("aes_key")
    @classmethod
    def key_validation(cls, key: str):
        Fernet(key)  # If it doesn't work, a ValueError will pop up
        return key


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
