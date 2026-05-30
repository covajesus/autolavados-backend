from datetime import date, datetime

from pydantic import BaseModel, Field


class LicenseCreate(BaseModel):
    license_client_name: str = Field(..., min_length=1, max_length=255)
    since_date: date | None = None
    end_date: date | None = None


class LicenseUpdate(BaseModel):
    license_client_name: str | None = Field(default=None, min_length=1, max_length=255)
    since_date: date | None = None
    end_date: date | None = None


class LicensePublic(BaseModel):
    id: str
    license_client_name: str
    since_date: date | None = None
    end_date: date | None = None
    added_date: datetime | None = None
    updated_date: datetime | None = None
    deleted_date: datetime | None = None


class LicenseListResponse(BaseModel):
    items: list[LicensePublic]


class LicenseItemResponse(BaseModel):
    item: LicensePublic


class LicenseDeleteResponse(BaseModel):
    ok: bool = True


class ErrorResponse(BaseModel):
    error: str
