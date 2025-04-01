import pytest
import pytest_asyncio
from sqlalchemy import select
from src.models.books import Book
from src.models.sellers import Seller
from fastapi import status
from icecream import ic
from src.configurations.security import get_password_hash
from typing import Dict, Any
import uuid


@pytest_asyncio.fixture
async def test_seller(db_session, request) -> Seller:
    """Фикстура для создания тестового продавца"""
    # Создаем уникальный email для каждого теста с коротким UUID
    unique_email = f"book{str(uuid.uuid4())[:6]}@example.com"
    
    seller = Seller(
        first_name="John",
        last_name="Doe",
        email=unique_email,
        password=get_password_hash("secret123"),
    )
    db_session.add(seller)
    await db_session.commit()
    return seller


@pytest_asyncio.fixture
async def auth_headers(test_seller, async_client) -> dict[str, str]:
    """Фикстура для получения заголовков авторизации"""
    response = await async_client.post(
        "/api/v1/token/",
        data={"username": test_seller.email, "password": "secret123"},
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(
            redirect_url,
            data={"username": test_seller.email, "password": "secret123"},
        )
    
    # Отладочная информация
    print(f"Auth response status: {response.status_code}")
    print(f"Auth response content: {response.content}")
    
    assert response.status_code == status.HTTP_200_OK, f"Failed to obtain token: {response.content}"
    
    token_data = response.json()
    assert "access_token" in token_data, f"No access_token in response: {token_data}"
    token = token_data["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Тест на ручку создания книги
@pytest.mark.asyncio
async def test_create_book(db_session, async_client, test_seller, auth_headers):
    """Тест создания книги"""
    book_data = {
        "title": "New Book",
        "author": "New Author",
        "year": 2024,
        "pages": 150,
        "seller_id": test_seller.id
    }
    
    response = await async_client.post("/api/v1/books/", json=book_data, headers=auth_headers)
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(redirect_url, json=book_data, headers=auth_headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    
    created_book = response.json()
    assert created_book["title"] == book_data["title"]
    assert created_book["author"] == book_data["author"]
    assert created_book["year"] == book_data["year"]
    assert created_book["pages"] == book_data["pages"]
    assert created_book["seller_id"] == test_seller.id
    
    # Проверяем, что книга действительно создана в базе
    book_query = select(Book).where(Book.id == created_book["id"])
    result = await db_session.execute(book_query)
    book_in_db = result.scalar_one()
    assert book_in_db is not None


@pytest.mark.asyncio
async def test_create_book_unauthorized(async_client, test_seller):
    """Тест создания книги без авторизации"""
    data = {
        "title": "Clean Architecture",
        "author": "Robert Martin",
        "pages": 300,
        "year": 2025,
        "seller_id": test_seller.id
    }
    response = await async_client.post("/api/v1/books/", json=data)
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(redirect_url, json=data)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_book_with_old_year(async_client, test_seller, auth_headers):
    data = {
        "title": "Clean Architecture",
        "author": "Robert Martin",
        "pages": 300,
        "year": 1986,
        "seller_id": test_seller.id
    }
    response = await async_client.post(
        "/api/v1/books/",
        json=data,
        headers=auth_headers
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(redirect_url, json=data, headers=auth_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# Тест на ручку получения списка книг
@pytest.mark.asyncio
async def test_get_books(db_session, async_client, test_seller):
    """Тест получения списка книг"""
    # Создаем тестовые книги
    book1 = Book(
        title="Book 1",
        author="Author 1",
        year=2024,
        pages=100,
        seller_id=test_seller.id
    )
    book2 = Book(
        title="Book 2",
        author="Author 2",
        year=2023,
        pages=200,
        seller_id=test_seller.id
    )
    db_session.add_all([book1, book2])
    await db_session.commit()

    response = await async_client.get("/api/v1/books/")
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.get(redirect_url)
    
    assert response.status_code == status.HTTP_200_OK
    
    books = response.json()["books"]
    # Фильтруем только книги текущего продавца
    seller_books = [book for book in books if book["seller_id"] == test_seller.id]
    assert len(seller_books) >= 2
    assert all(book["seller_id"] == test_seller.id for book in seller_books)


# Тест на ручку получения одной книги
@pytest.mark.asyncio
async def test_get_single_book(db_session, async_client, test_seller):
    """Тест получения информации об одной книге"""
    # Создаем тестовую книгу
    book = Book(
        title="Test Book",
        author="Test Author",
        year=2024,
        pages=100,
        seller_id=test_seller.id
    )
    db_session.add(book)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/books/{book.id}/")
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.get(redirect_url)
    
    assert response.status_code == status.HTTP_200_OK
    
    book_data = response.json()
    assert book_data["title"] == book.title
    assert book_data["author"] == book.author
    assert book_data["year"] == book.year
    assert book_data["pages"] == book.pages
    assert book_data["seller_id"] == test_seller.id


# Тест на ручку обновления книги
@pytest.mark.asyncio
async def test_update_book(db_session, async_client, test_seller, auth_headers):
    """Тест обновления информации о книге"""
    # Создаем тестовую книгу
    book = Book(
        title="Old Title",
        author="Old Author",
        year=2023,
        pages=100,
        seller_id=test_seller.id
    )
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)  # Обновляем объект из базы

    update_data = {
        "title": "New Title",
        "author": "New Author",
        "year": 2024,
        "pages": 150,
        "id": book.id,
        "seller_id": test_seller.id
    }

    response = await async_client.put(
        f"/api/v1/books/{book.id}/",
        json=update_data,
        headers=auth_headers
    )

    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.put(redirect_url, json=update_data, headers=auth_headers)

    print(f"Update response status: {response.status_code}")
    print(f"Update response content: {response.content}")
    
    assert response.status_code == status.HTTP_200_OK

    updated_book = response.json()
    assert updated_book["title"] == update_data["title"]
    assert updated_book["author"] == update_data["author"]
    assert updated_book["year"] == update_data["year"]
    assert updated_book["pages"] == update_data["pages"]
    assert updated_book["seller_id"] == test_seller.id

    # Проверяем, что изменения сохранились в базе - получаем книгу по GET запросу
    get_response = await async_client.get(
        f"/api/v1/books/{book.id}/",
        headers=auth_headers
    )
    
    # Проверяем редирект
    if get_response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = get_response.headers.get("location")
        get_response = await async_client.get(redirect_url, headers=auth_headers)
        
    assert get_response.status_code == status.HTTP_200_OK
    book_in_db = get_response.json()
    assert book_in_db["title"] == update_data["title"]
    assert book_in_db["author"] == update_data["author"]
    assert book_in_db["year"] == update_data["year"]
    assert book_in_db["pages"] == update_data["pages"]


@pytest.mark.asyncio
async def test_update_book_unauthorized(db_session, async_client, test_seller):
    """Тест обновления книги без авторизации"""
    book = Book(
        author="Pushkin",
        title="Eugeny Onegin",
        year=2024,
        pages=104,
        seller_id=test_seller.id
    )
    db_session.add(book)
    await db_session.commit()

    response = await async_client.put(
        f"/api/v1/books/{book.id}/",
        json={
            "title": "Mziri",
            "author": "Lermontov",
            "pages": 100,
            "year": 2024,
            "id": book.id,
            "seller_id": test_seller.id
        }
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.put(
            redirect_url,
            json={
                "title": "Mziri",
                "author": "Lermontov",
                "pages": 100,
                "year": 2024,
                "id": book.id,
                "seller_id": test_seller.id
            }
        )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_delete_book(db_session, async_client, test_seller, auth_headers):
    """Тест удаления книги"""
    # Создаем тестовую книгу
    book = Book(
        title="Test Book",
        author="Test Author",
        year=2024,
        pages=100,
        seller_id=test_seller.id
    )
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)  # Обновляем объект из базы

    book_id = book.id  # Сохраняем ID книги
    
    response = await async_client.delete(
        f"/api/v1/books/{book_id}/",
        headers=auth_headers
    )

    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.delete(redirect_url, headers=auth_headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Проверяем, что книга удалена из базы
    # Убедимся, что мы сделали коммит изменений после удаления
    await db_session.commit()
    
    # Используем чистый запрос без объекта book
    db_book = await db_session.get(Book, book_id)
    assert db_book is None


@pytest.mark.asyncio
async def test_delete_book_unauthorized(db_session, async_client, test_seller):
    """Тест удаления книги без авторизации"""
    book = Book(
        author="Lermontov",
        title="Mtziri",
        pages=510,
        year=2024,
        seller_id=test_seller.id
    )
    db_session.add(book)
    await db_session.commit()

    response = await async_client.delete(f"/api/v1/books/{book.id}/")
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.delete(redirect_url)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_delete_book_wrong_seller(db_session, async_client, auth_headers):
    """Тест удаления книги другого продавца"""
    # Создаем другого продавца с уникальным email
    import uuid
    other_seller_email = f"other{uuid.uuid4().hex[:6]}@example.com"
    
    other_seller = Seller(
        first_name="Jane",
        last_name="Smith",
        email=other_seller_email,
        password=get_password_hash("other_password"),
    )
    db_session.add(other_seller)
    await db_session.commit()
    await db_session.refresh(other_seller)

    # Создаем книгу для другого продавца
    other_book = Book(
        title="Other Book",
        author="Other Author",
        year=2024,
        pages=200,
        seller_id=other_seller.id
    )
    db_session.add(other_book)
    await db_session.commit()
    await db_session.refresh(other_book)

    # Пытаемся удалить книгу другого продавца
    response = await async_client.delete(
        f"/api/v1/books/{other_book.id}/",
        headers=auth_headers
    )

    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.delete(redirect_url, headers=auth_headers)
    
    # Должен быть 403 Forbidden
    assert response.status_code == status.HTTP_403_FORBIDDEN
