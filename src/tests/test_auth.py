import pytest
import pytest_asyncio
import uuid
from fastapi import status

from src.models.sellers import Seller
from src.configurations.security import get_password_hash


@pytest_asyncio.fixture
async def test_seller_with_password(db_session) -> Seller:
    """Create a seller for testing."""
    unique_email = f"test{str(uuid.uuid4())[:6]}@example.com"
    seller = Seller(
        first_name="Test",
        last_name="Seller",
        email=unique_email,
        password=get_password_hash("secret123")
    )
    db_session.add(seller)
    await db_session.commit()
    return seller


@pytest.mark.asyncio
async def test_login_success(async_client, test_seller_with_password):
    """Тест успешной аутентификации"""
    login_data = {
        "username": test_seller_with_password.email,
        "password": "secret123",
    }
    
    response = await async_client.post("/api/v1/token/", data=login_data)
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(redirect_url, data=login_data)
    
    print(f"Login success response status: {response.status_code}")
    print(f"Login success response content: {response.content}")
    
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(async_client, test_seller_with_password):
    """Тест аутентификации с неверным паролем"""
    response = await async_client.post(
        "/api/v1/token/",
        data={
            "username": test_seller_with_password.email,
            "password": "wrong_password"
        }
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(
            redirect_url,
            data={
                "username": test_seller_with_password.email,
                "password": "wrong_password"
            }
        )
    
    print(f"Login wrong password response status: {response.status_code}")
    print(f"Login wrong password response content: {response.content}")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_wrong_email(async_client):
    """Тест аутентификации с несуществующим email"""
    response = await async_client.post(
        "/api/v1/token/",
        data={
            "username": "wrong@example.com",
            "password": "secret123"
        }
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(
            redirect_url,
            data={
                "username": "wrong@example.com",
                "password": "secret123"
            }
        )
    
    print(f"Login wrong email response status: {response.status_code}")
    print(f"Login wrong email response content: {response.content}")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_protected_endpoint_with_token(async_client, test_seller_with_password):
    """Тест доступа к защищенному эндпоинту с валидным токеном"""
    # Получаем токен
    response = await async_client.post(
        "/api/v1/token/",
        data={
            "username": test_seller_with_password.email,
            "password": "secret123"
        }
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.post(
            redirect_url,
            data={
                "username": test_seller_with_password.email,
                "password": "secret123"
            }
        )
    
    print(f"Login response status: {response.status_code}")
    print(f"Login response content: {response.content}")
    
    assert response.status_code == status.HTTP_200_OK, f"Failed to login: {response.content}"
    
    # Проверяем содержимое ответа
    response_data = response.json()
    assert "access_token" in response_data, f"No access_token in response: {response_data}"
    token = response_data["access_token"]
    
    # Проверяем доступ к защищенному эндпоинту
    response = await async_client.get(
        f"/api/v1/seller/{test_seller_with_password.id}/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.get(
            redirect_url,
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(async_client, test_seller_with_password):
    """Тест доступа к защищенному эндпоинту с невалидным токеном"""
    response = await async_client.get(
        f"/api/v1/seller/{test_seller_with_password.id}/",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    # Проверяем редирект
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        redirect_url = response.headers.get("location")
        response = await async_client.get(
            redirect_url,
            headers={"Authorization": "Bearer invalid_token"}
        )
    
    print(f"Protected endpoint with invalid token response status: {response.status_code}")
    print(f"Protected endpoint with invalid token response content: {response.content}")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED 