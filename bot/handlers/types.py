from dataclasses import dataclass
from datetime import datetime
from aiogram import Router

router = Router()


@dataclass
class DummyEvent:
    id: str
    name: str
    details: str
    date: datetime
    time: datetime
    is_public: bool = False
