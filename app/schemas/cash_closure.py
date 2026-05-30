from datetime import date, datetime

from pydantic import BaseModel, Field


class CashClosureTodayResponse(BaseModel):
    date: date
    licenseId: int | None = Field(default=None, ge=1)
    status_id: int | None = Field(
        default=None,
        description="0 = caja abierta, 1 = caja cerrada; null si no hay registro hoy",
    )
    already_closed: bool = False
    needs_confirmation: bool = True


class CashClosureConfirmResponse(BaseModel):
    ok: bool = True
    date: date
    licenseId: int | None = Field(default=None, ge=1)
    status_id: int = Field(ge=0, le=1)
