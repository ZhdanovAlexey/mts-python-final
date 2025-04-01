# Для импорта из корневого модуля
# import sys
# sys.path.append("..")
# from main import app

from typing import Annotated
from fastapi import APIRouter, Depends, Response, status, HTTPException
from sqlalchemy import select
from src.models.books import Book
from src.models.sellers import Seller
from src.schemas import IncomingBook, ReturnedAllbooks, ReturnedBook
from icecream import ic
from sqlalchemy.ext.asyncio import AsyncSession
from src.configurations import get_async_session
from src.configurations.security import get_current_seller

books_router = APIRouter(tags=["books"], prefix="/books")

# CRUD - Create, Read, Update, Delete

DBSession = Annotated[AsyncSession, Depends(get_async_session)]


# Ручка для создания записи о книге в БД. Возвращает созданную книгу.
@books_router.post(
    "/", response_model=ReturnedBook, status_code=status.HTTP_201_CREATED
)
async def create_book(
    book: IncomingBook,
    session: DBSession,
    current_seller: Annotated[Seller, Depends(get_current_seller)],
):
    # Создаем книгу с привязкой к продавцу
    new_book = Book(
        title=book.title,
        author=book.author,
        year=book.year,
        pages=book.pages,
        seller_id=current_seller.id,
    )

    session.add(new_book)
    await session.flush()

    return new_book


# Ручка, возвращающая все книги
@books_router.get("/", response_model=ReturnedAllbooks)
async def get_all_books(session: DBSession):
    query = select(Book)
    result = await session.execute(query)
    books = result.scalars().all()
    return {"books": books}


# Ручка для получения книги по ее ИД
@books_router.get("/{book_id}", response_model=ReturnedBook)
async def get_book(book_id: int, session: DBSession):
    if result := await session.get(Book, book_id):
        return result

    return Response(status_code=status.HTTP_404_NOT_FOUND)


# Ручка для удаления книги
@books_router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    session: DBSession,
    current_seller: Annotated[Seller, Depends(get_current_seller)],
):
    deleted_book = await session.get(Book, book_id)
    ic(deleted_book)

    if not deleted_book:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    
    if deleted_book.seller_id != current_seller.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this book"
        )
    
    await session.delete(deleted_book)


# Ручка для обновления данных о книге
@books_router.put("/{book_id}", response_model=ReturnedBook)
async def update_book(
    book_id: int,
    new_book_data: ReturnedBook,
    session: DBSession,
    current_seller: Annotated[Seller, Depends(get_current_seller)],
):
    if updated_book := await session.get(Book, book_id):
        if updated_book.seller_id != current_seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this book"
            )
        
        updated_book.author = new_book_data.author
        updated_book.title = new_book_data.title
        updated_book.year = new_book_data.year
        updated_book.pages = new_book_data.pages

        await session.flush()

        return updated_book

    return Response(status_code=status.HTTP_404_NOT_FOUND)
