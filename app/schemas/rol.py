from datetime import datetime

from pydantic import BaseModel, Field


class RolPublic(BaseModel):
    id: str
    rol: str
    licenseId: int | None = Field(default=None, ge=1)
    added_date: datetime | None = None
    updated_date: datetime | None = None


class RolListResponse(BaseModel):
    items: list[RolPublic]


class RolItemResponse(BaseModel):
    item: RolPublic


class ErrorResponse(BaseModel):
    error: str
