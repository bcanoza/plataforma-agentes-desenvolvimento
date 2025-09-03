"""Modelo exemplo para logs da aplicação."""
from pydantic import BaseModel

class AppLog(BaseModel):
    id: int
    level: str
    message: str
