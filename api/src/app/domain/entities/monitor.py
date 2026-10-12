from pydantic import BaseModel


class Monitor(BaseModel):
    name: str
    version: str
