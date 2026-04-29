from pydantic import BaseModel, ConfigDict


class Data(BaseModel):
    model_config = ConfigDict(strict=True)

    online: bool
    time: int