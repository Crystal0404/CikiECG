from pydantic import BaseModel, ConfigDict

class Config(BaseModel):
    model_config = ConfigDict(strict=True)

    ip: str = "127.0.0.1"
    port: int = 8889
    backup: bool = False
    backup_command: str = "!!qb make"
    stop: bool = True
    stop_count: int = 3