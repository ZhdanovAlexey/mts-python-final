from pydantic import BaseModel, EmailStr, Field


class SellerBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr


class SellerCreate(SellerBase):
    password: str = Field(..., min_length=6)


class SellerUpdate(SellerBase):
    first_name: str | None = Field(None, min_length=1, max_length=50)
    last_name: str | None = Field(None, min_length=1, max_length=50)
    email: EmailStr | None = None


class BookInSeller(BaseModel):
    id: int
    title: str
    author: str
    year: int
    pages: int

    class Config:
        from_attributes = True


class SellerResponse(SellerBase):
    id: int
    
    class Config:
        from_attributes = True


class SellerDetailResponse(SellerResponse):
    books: list[BookInSeller] = [] 