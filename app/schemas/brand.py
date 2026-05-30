from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BrandCreate(BaseModel):
    brand: str = Field(..., min_length=1, max_length=255)
    licenseId: int | None = Field(default=None, ge=1)


class BrandUpdate(BaseModel):
    brand: str | None = Field(default=None, min_length=1, max_length=255)
    licenseId: int | None = Field(default=None, ge=1)


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand: str
    added_date: datetime | None = None
    updated_date: datetime | None = None
    deleted_date: datetime | None = None


class BrandPublic(BaseModel):
    id: str
    brand: str
    licenseId: int | None = Field(default=None, ge=1)
    added_date: str | None = None
    updated_date: str | None = None
    deleted_date: str | None = None


class BrandListResponse(BaseModel):
    items: list[BrandPublic]


class BrandItemResponse(BaseModel):
    item: BrandPublic


class BrandDeleteResponse(BaseModel):
    ok: bool = True


class ErrorResponse(BaseModel):
    error: str
