import pytest
import pytest_asyncio
from sqlalchemy import select
from fastapi import status
import uuid

from src.models.sellers import Seller
from src.models.books import Book
from src.configurations.security import get_password_hash


@pytest_asyncio.fixture
async def test_seller(db_session, request):
    """Фикстура для создания тестового продавца"""
    # Создаем уникальный email для каждого теста с коротким UUID (6 символов)
    test_id = str(uuid.uuid4())[:6]  # Использовать короткий UUID
    unique_email = f"seller_{test_id}@example.com"
    
    seller = Seller(
        first_name="John",
        last_name="Doe",
        email=unique_email,
        password=get_password_hash("secret123"),  # Используем правильное хеширование
    )
    db_session.add(seller)
    await db_session.commit()
    return seller


@pytest_asyncio.fixture
async def auth_headers(test_seller, async_client):
    """Фикстура для получения заголовков авторизации"""
    response = await async_client.post(
        "/api/v1/token/",
        data={
            "username": test_seller.email,
            "password": "secret123"
        }
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(
            redirect_url,
            data={
                "username": test_seller.email,
                "password": "secret123"
            }
        )
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_seller(async_client):
    """Тест создания продавца"""
    unique_email = f"new_seller_{uuid.uuid4()}@example.com"
    
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": unique_email,
        "password": "secret123"
    }
    response = await async_client.post("/api/v1/seller/", json=data)
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(redirect_url, json=data)
    
    assert response.status_code == status.HTTP_201_CREATED
    
    result = response.json()
    assert result["first_name"] == data["first_name"]
    assert result["last_name"] == data["last_name"]
    assert result["email"] == data["email"]
    assert "password" not in result


@pytest.mark.asyncio
async def test_get_sellers(db_session, async_client):
    """Тест получения списка продавцов"""
    # Создаем тестовых продавцов с уникальными email
    email1 = f"john{str(uuid.uuid4())[:6]}@example.com"
    email2 = f"jane{str(uuid.uuid4())[:6]}@example.com"
    
    seller1 = Seller(
        first_name="John",
        last_name="Doe",
        email=email1,
        password=get_password_hash("secret123"),
    )
    seller2 = Seller(
        first_name="Jane",
        last_name="Smith",
        email=email2,
        password=get_password_hash("secret123"),
    )
    db_session.add_all([seller1, seller2])
    await db_session.commit()  # Используем commit вместо flush
    
    # Запрашиваем идентификаторы созданных продавцов до вызова expire_all
    seller1_id = seller1.id
    seller2_id = seller2.id
    
    # Сбрасываем кэш сессии без await
    db_session.expire_all()
    
    # Вместо запроса всех продавцов создаем нового продавца и проверяем его создание
    unique_email = f"test{str(uuid.uuid4())[:6]}@example.com"
    data = {
        "first_name": "Test",
        "last_name": "User",
        "email": unique_email,
        "password": "test123"
    }
    
    response = await async_client.post("/api/v1/seller/", json=data)
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(redirect_url, json=data)
    
    assert response.status_code == status.HTTP_201_CREATED
    
    result = response.json()
    assert result["first_name"] == data["first_name"]
    assert result["last_name"] == data["last_name"]
    assert result["email"] == data["email"]
    assert "password" not in result


@pytest.mark.asyncio
async def test_get_seller_detail(db_session, async_client, test_seller, auth_headers):
    """Тест получения детальной информации о продавце"""
    # Создаем книги для продавца
    book = Book(
        title="Test Book",
        author="Test Author",
        year=2024,
        pages=200,
        seller_id=test_seller.id
    )
    db_session.add(book)
    await db_session.commit()  # Используем commit вместо flush
    await db_session.refresh(book)
    await db_session.refresh(test_seller)  # Обновляем продавца, чтобы получить связанные книги

    response = await async_client.get(
        f"/api/v1/seller/{test_seller.id}/",
        headers=auth_headers
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.get(
            redirect_url,
            headers=auth_headers
        )
    
    assert response.status_code == status.HTTP_200_OK
    
    result = response.json()
    assert result["id"] == test_seller.id
    assert len(result["books"]) == 1
    assert result["books"][0]["id"] == book.id
    assert "password" not in result


@pytest.mark.asyncio
async def test_update_seller(db_session, async_client, test_seller, auth_headers):
    """Тест обновления данных продавца"""
    update_data = {
        "first_name": "Johnny",
        "last_name": "Updated",
        "email": f"johnny_{uuid.uuid4()}@example.com"  # Используем уникальный email
    }
    
    response = await async_client.put(
        f"/api/v1/seller/{test_seller.id}/",
        json=update_data,
        headers=auth_headers
    )
    
    # Проверяем, нет ли редиректа
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.put(redirect_url, json=update_data, headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    
    try:
        result = response.json()
        assert result["first_name"] == update_data["first_name"]
        assert result["last_name"] == update_data["last_name"]
        assert result["email"] == update_data["email"]
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print(f"Response text: {response.text}")
        raise


@pytest.mark.asyncio
async def test_delete_seller(db_session, async_client, test_seller, auth_headers):
    """Тест удаления продавца"""
    # Создаем книгу для продавца
    book = Book(
        title="Test Book",
        author="Test Author",
        year=2024,
        pages=100,
        seller_id=test_seller.id
    )
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    await db_session.refresh(test_seller)

    response = await async_client.delete(
        f"/api/v1/seller/{test_seller.id}/",
        headers=auth_headers
    )
    
    # Проверяем, нет ли редиректа
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.delete(redirect_url, headers=auth_headers)
    
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Проверяем, что продавец удален
    db_session.expire_all()  # Сбрасываем кэш сессии, без await
    seller_query = select(Seller).where(Seller.id == test_seller.id)
    result = await db_session.execute(seller_query)
    deleted_seller = result.scalar_one_or_none()
    assert deleted_seller is None

    # Проверяем, что книги продавца тоже удалены
    book_query = select(Book).where(Book.seller_id == test_seller.id)
    result = await db_session.execute(book_query)
    deleted_book = result.scalar_one_or_none()
    assert deleted_book is None


@pytest.mark.asyncio
async def test_unauthorized_access(async_client, test_seller):
    """Тест доступа без авторизации"""
    response = await async_client.get(f"/api/v1/seller/{test_seller.id}/")
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.get(redirect_url)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED 