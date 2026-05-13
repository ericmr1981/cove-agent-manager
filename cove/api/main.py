import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cove.api.routes import config, health, sessions, websocket
from cove.session_store.service import SessionStoreService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database tables exist
    try:
        store = SessionStoreService()
        await store.create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning("Could not create tables on startup: %s", e)
    yield


app = FastAPI(title="Cove Agent Manager", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")
