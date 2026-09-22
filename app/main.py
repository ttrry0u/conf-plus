from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .database import Base, engine
from .routers import (
    abstracts,
    auth,
    conferences,
    fees,
    hotels,
    invitations,
    mailings,
    ratings,
    registrations,
    reports,
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Конф+",
    description="Система управления конференциями, докладами, спикерами, участниками и оценками (MVP).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальная обработка ошибок БД (по ТЗ, Рис 6)
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка базы данных. Попробуйте позже."},
    )


# Глобальная обработка прочих ошибок (по ТЗ, Рис 6)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера. Пожалуйста, попробуйте позже."},
    )


# Создание таблиц (для MVP; в проде — Alembic-миграции)
Base.metadata.create_all(bind=engine)

# Подключение роутеров
app.include_router(auth.router)
app.include_router(conferences.router)
app.include_router(registrations.router)
app.include_router(abstracts.router)
app.include_router(ratings.router)
app.include_router(invitations.router)
app.include_router(fees.router)
app.include_router(hotels.router)
app.include_router(mailings.router)
app.include_router(reports.router)


@app.get("/health", tags=["Служебные"])
def health():
    return {"status": "ok"}


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)