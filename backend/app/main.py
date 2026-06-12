import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import accounts, auth, contacts, emails, graph, labels, sync
from .services.sync_service import sync_all_accounts

logging.basicConfig(level=logging.INFO)

scheduler = AsyncIOScheduler()


async def _sync_job() -> None:
    await asyncio.to_thread(sync_all_accounts)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler.add_job(
        _sync_job,
        "interval",
        minutes=settings.sync_interval_minutes,
        id="imap_sync",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Unimail", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(emails.router)
app.include_router(contacts.router)
app.include_router(sync.router)
app.include_router(graph.router)
app.include_router(labels.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
