from .appointments import router as appointments_router
from .users import router as users_router
from .events import router as events_router
from .calendar_states import router as calendar_states_router


__all__ = [
    "appointments_router",
    "users_router",
    "events_router",
    "calendar_states_router",
]

def register_handlers(dp):
    dp.include_router(users_router)
    dp.include_router(events_router)
    dp.include_router(appointments_router)
    dp.include_router(calendar_states_router)


