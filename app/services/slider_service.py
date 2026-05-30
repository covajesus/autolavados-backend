from datetime import datetime

from app.core.datetime_utils import business_now
from app.core.license_scope import (
    apply_license_scope,
    assert_row_license,
    effective_license_id_for_write,
    license_scope_for_user,
)

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.slider import Slider
from app.schemas.slider import SliderCreate, SliderPublic, SliderUpdate
from app.schemas.user import UserPublic


class SliderNotFoundError(Exception):
    pass


class SliderValidationError(Exception):
    pass


class SliderService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _now() -> datetime:
        return business_now()

    @staticmethod
    def to_public(row: Slider) -> SliderPublic:
        return SliderPublic(
            id=str(row.id),
            slider=row.slider,
            position=row.position,
            licenseId=row.license_id,
            added_date=row.added_date,
            updated_date=row.updated_date,
            deleted_date=row.deleted_date,
        )

    def _active_filter(self, stmt):
        return stmt.where(Slider.deleted_date.is_(None))

    def _find_duplicate_position(
        self,
        position: str,
        license_id: int | None,
        except_id: int | None = None,
    ) -> Slider | None:
        normalized = position.strip().lower()
        stmt = self._active_filter(select(Slider)).where(
            func.lower(Slider.position) == normalized,
            Slider.license_id == license_id,
        )
        if except_id is not None:
            stmt = stmt.where(Slider.id != except_id)
        return self.db.scalars(stmt).first()

    def list_all(self, user: UserPublic) -> list[SliderPublic]:
        stmt = self._active_filter(select(Slider)).order_by(Slider.position, Slider.id)
        stmt = apply_license_scope(stmt, Slider, license_scope_for_user(user))
        rows = self.db.scalars(stmt).all()
        return [self.to_public(row) for row in rows]

    def get_by_id(self, slider_id: int, user: UserPublic) -> SliderPublic:
        stmt = self._active_filter(select(Slider)).where(Slider.id == slider_id)
        stmt = apply_license_scope(stmt, Slider, license_scope_for_user(user))
        row = self.db.scalars(stmt).first()
        if row is None:
            raise SliderNotFoundError()
        return self.to_public(row)

    def create(self, data: SliderCreate, user: UserPublic) -> SliderPublic:
        image = data.slider.strip()
        position = data.position.strip()
        if not image:
            raise SliderValidationError("El slider es obligatorio")
        if not position:
            raise SliderValidationError("La posición es obligatoria")
        license_id = effective_license_id_for_write(
            self.db,
            user,
            data.licenseId,
            error_factory=SliderValidationError,
        )
        if self._find_duplicate_position(position, license_id):
            raise SliderValidationError("Ya existe un slider con esa posición")

        now = self._now()
        row = Slider(
            slider=image,
            position=position,
            license_id=license_id,
            added_date=now,
            updated_date=now,
            deleted_date=None,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def update(self, slider_id: int, data: SliderUpdate, user: UserPublic) -> SliderPublic:
        row = self.db.get(Slider, slider_id)
        if row is None or not row.is_active:
            raise SliderNotFoundError()
        scope = license_scope_for_user(user)
        assert_row_license(row, scope, not_found_exc=SliderNotFoundError)

        if data.slider is not None:
            image = data.slider.strip()
            if not image:
                raise SliderValidationError("El slider no puede quedar vacío")
            row.slider = image

        if data.position is not None:
            position = data.position.strip()
            if not position:
                raise SliderValidationError("La posición no puede quedar vacía")
            row.position = position

        if data.licenseId is not None or scope is not None:
            row.license_id = effective_license_id_for_write(
                self.db,
                user,
                data.licenseId,
                error_factory=SliderValidationError,
            )

        if self._find_duplicate_position(row.position, row.license_id, except_id=slider_id):
            raise SliderValidationError("Ya existe un slider con esa posición")

        row.updated_date = self._now()
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def delete(self, slider_id: int, user: UserPublic) -> None:
        row = self.db.get(Slider, slider_id)
        if row is None or not row.is_active:
            raise SliderNotFoundError()
        assert_row_license(row, license_scope_for_user(user), not_found_exc=SliderNotFoundError)

        now = self._now()
        row.deleted_date = now
        row.updated_date = now
        self.db.commit()
