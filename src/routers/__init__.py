from fastapi import APIRouter

from .v1.books import books_router
from .sellers import router as sellers_router
from .auth import router as auth_router

v1_router = APIRouter(tags=["v1"], prefix="/api/v1")

v1_router.include_router(books_router)
v1_router.include_router(sellers_router)
v1_router.include_router(auth_router)
