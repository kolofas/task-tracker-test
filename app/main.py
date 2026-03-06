from fastapi import FastAPI
from sqlalchemy import text

from app.db import get_session
from app.api.tasks import router as tasks_router

app = FastAPI(title="Task Tracker")


@app.get("/health/db")
async def health_db():
    async for session in get_session():
        await session.execute(text("SELECT 1"))
        return {"db": "ok"}
    
app.include_router(tasks_router)