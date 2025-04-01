from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from src.configurations.database import create_db_and_tables, global_init
from src.routers import v1_router
from icecream import ic


@asynccontextmanager
async def lifespan(app: FastAPI):
    ic("I am here!")
    global_init()
    await create_db_and_tables()
    yield


# Само приложение fastApi. именно оно запускается сервером и служит точкой входа
# в нем можно указать разные параметры для сваггера и для ручек (эндпоинтов).
app = FastAPI(
    title="Book Library App",
    description="Учебное приложение для MTS Shad",
    version="0.0.1",
    default_response_class=ORJSONResponse,
    responses={404: {"description": "Not found!"}},  # Подключаем быстрый сериализатор
    lifespan=lifespan,
)


app.include_router(v1_router)
