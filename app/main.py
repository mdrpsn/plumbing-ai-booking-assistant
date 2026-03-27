from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.bookings import router as bookings_router
from app.api.routes.health import router as health_router
from app.api.routes.leads import router as leads_router
from app.api.routes.messages import router as messages_router
from app.core.config import get_settings
from app.db.session import initialize_database


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


app.include_router(health_router)
app.include_router(leads_router)
app.include_router(bookings_router)
app.include_router(messages_router)
