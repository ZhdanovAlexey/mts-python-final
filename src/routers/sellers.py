from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.configurations.database import get_async_session
from src.configurations.security import get_current_seller, get_password_hash
from src.models.sellers import Seller
from src.schemas.sellers import (
    SellerCreate,
    SellerResponse,
    SellerDetailResponse,
    SellerUpdate,
)

router = APIRouter(prefix="/seller", tags=["sellers"])


@router.post("", response_model=SellerResponse, status_code=status.HTTP_201_CREATED)
async def create_seller(
    seller: SellerCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    try:
        # Hash the password
        hashed_password = get_password_hash(seller.password)
        seller_data = seller.model_dump()
        seller_data["password"] = hashed_password
        
        new_seller = Seller(**seller_data)
        session.add(new_seller)
        await session.commit()
        await session.refresh(new_seller)  # Обновляем объект после коммита
        return new_seller
    except IntegrityError:
        # Проверим, существует ли уже продавец с таким email
        await session.rollback()
        query = select(Seller).where(Seller.email == seller.email)
        result = await session.execute(query)
        existing_seller = result.scalar_one_or_none()
        
        if existing_seller:
            # Если продавец с таким email уже существует, возвращаем его
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Seller with email {seller.email} already exists"
            )
        else:
            # Если ошибка другая, возвращаем общую ошибку
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create seller due to database constraints"
            )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("", response_model=list[SellerResponse])
async def get_sellers(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    query = select(Seller)
    result = await session.execute(query)
    sellers = result.scalars().all()
    return sellers


@router.get("/{seller_id}", response_model=SellerDetailResponse)
async def get_seller(
    seller_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_seller: Annotated[Seller, Depends(get_current_seller)],
):
    query = select(Seller).where(Seller.id == seller_id)
    result = await session.execute(query)
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    return seller


@router.put("/{seller_id}", response_model=SellerResponse)
async def update_seller(
    seller_id: int,
    seller_update: SellerUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_seller: Annotated[Seller, Depends(get_current_seller)],
):
    if seller_id != current_seller.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this seller")
    
    query = select(Seller).where(Seller.id == seller_id)
    result = await session.execute(query)
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    # Update only provided fields
    update_data = seller_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(seller, field, value)
    
    await session.commit()
    return seller


@router.delete("/{seller_id}", status_code=204)
async def delete_seller(
    seller_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_seller: Annotated[Seller, Depends(get_current_seller)],
):
    if seller_id != current_seller.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this seller")
    
    query = select(Seller).where(Seller.id == seller_id)
    result = await session.execute(query)
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    await session.delete(seller)
    await session.commit() 