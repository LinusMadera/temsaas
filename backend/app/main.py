import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from config import SOFTWARE_NAME
from database import close_db, get_db, init_db
from fastapi import BackgroundTasks, FastAPI
from routers import auth, legal, payment, protected, profile
from utils.s3 import init_s3


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_s3()

    asyncio.create_task(cleanup_expired_sessions())

    yield
    close_db()

async def cleanup_expired_sessions():
    while True:
        try:
            db = get_db()
            db.sessions.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
            await asyncio.sleep(60)

app = FastAPI(
    lifespan=lifespan,
    title=f"{SOFTWARE_NAME} API",
    description=f"{SOFTWARE_NAME} backend API service",
    version="alpha",
    redoc_url="/redoc",
    docs_url="/swagger"
    )

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(payment.router, prefix="/payment", tags=["Payment"])
app.include_router(protected.router, prefix="/test", tags=["Test (Restricted Routes)"])
app.include_router(legal.router, prefix="/legal", tags=["Legal"])
app.include_router(profile.router, prefix="/user", tags=["User Profile"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
