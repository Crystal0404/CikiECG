from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Decrypt(BaseModel):
    model_config = ConfigDict(strict=True)

    aes_key: str = ""
    ttl: int = 5

    @field_validator("aes_key")
    @classmethod
    def key_validation(cls, key: str):
        if key == "":
            return key
        else:
            Fernet(key)  # If it doesn't work, a ValueError will pop up
            return key


class Config(BaseModel):
    model_config = ConfigDict(strict=True)

    ip: str = "127.0.0.1"
    port: int = 8889
    backup: bool = False
    backup_command: str = "!!qb make"
    stop: bool = True
    stop_count: int = 3
    timeout: int | None = None
    decrypt: Decrypt = Field(default_factory=Decrypt)
