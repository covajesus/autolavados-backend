from datetime import datetime

from app.core.datetime_utils import business_now
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.license_scope import (
    apply_license_scope,
    assert_row_license,
    effective_license_id_for_write,
    license_is_usable,
    license_scope_for_user,
)
from app.core.roles import (
    ADMIN_ROL_ID,
    MANAGER_ROL_ID,
    SUPER_ADMIN_ROL_ID,
    WASHER_ROL_ID,
    role_from_id,
    role_id_from_role,
)
from app.core.security import hash_password, verify_password
from app.core.user_status import (
    STATUS_ABIERTO_ID,
    active_from_status_id,
    status_id_from_active,
)
from app.models.rol import Rol
from app.models.branch_office import BranchOffice
from app.models.license import License
from app.models.status import Status
from app.models.user import User
from app.schemas.user import UserCreate, UserPublic, UserRole, UserUpdate
from app.services.branch_office_manager_service import (
    BranchOfficeManagerService,
    BranchOfficeManagerValidationError,
)
from app.services.branch_office_washer_service import (
    BranchOfficeWasherService,
    BranchOfficeWasherValidationError,
)


class UserNotFoundError(Exception):
    pass


class UserValidationError(Exception):
    pass


class AuthFailedError(Exception):
    pass


class LicenseExpiredError(Exception):
    def __init__(self, message: str = "La licencia ha vencido o no está disponible") -> None:
        self.message = message
        super().__init__(message)


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._branch_washer = BranchOfficeWasherService(db)
        self._branch_manager = BranchOfficeManagerService(db)

    @staticmethod
    def _now() -> datetime:
        return business_now()

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _resolve_email(raw: str | None) -> str:
        text = (raw or "").strip()
        return UserService.normalize_email(text) if text else ""

    def _rol_labels_by_id(self) -> dict[int, str]:
        stmt = select(Rol)
        return {row.id: row.rol for row in self.db.scalars(stmt).all()}

    def to_public(self, row: User, *, rol_label: str | None = None) -> UserPublic:
        branch_office_id: int | None = None
        week_percentage: str | None = None
        sunday_percentage: str | None = None
        daily_goal: str | None = None
        daily_goal_percentage: str | None = None
        if row.id:
            if row.rol_id == WASHER_ROL_ID:
                assignment = self._branch_washer.get_active_assignment_for_washer(row.id)
                if assignment is not None and assignment.branch_office_id is not None:
                    branch_office_id = assignment.branch_office_id
                    week_percentage = assignment.week_percentage
                    sunday_percentage = assignment.sunday_percentage
                    daily_goal = assignment.daily_goal
                    daily_goal_percentage = assignment.daily_goal_percentage
            elif row.rol_id == MANAGER_ROL_ID:
                office_id = self._branch_manager.get_branch_office_id_for_manager(row.id)
                if office_id is not None:
                    branch_office_id = office_id
        if rol_label is None:
            rol_row = self.db.get(Rol, row.rol_id)
            rol_label = rol_row.rol if rol_row is not None else role_from_id(row.rol_id)
        return UserPublic(
            id=str(row.id),
            fullName=row.full_name,
            email=row.email,
            role=role_from_id(row.rol_id),
            roleId=row.rol_id,
            roleLabel=rol_label,
            licenseId=row.license_id,
            branchOfficeId=branch_office_id,
            weekPercentage=week_percentage,
            sundayPercentage=sunday_percentage,
            dailyGoal=daily_goal,
            dailyGoalPercentage=daily_goal_percentage,
            statusId=str(row.status_id) if row.status_id is not None else None,
            active=active_from_status_id(row.status_id),
            mustChangePassword=bool(row.must_change_password)
            and row.rol_id != SUPER_ADMIN_ROL_ID,
        )

    @staticmethod
    def _parse_branch_office_id(branch_office_id_raw: int | None) -> int | None:
        if branch_office_id_raw is None:
            return None
        if branch_office_id_raw < 1:
            raise UserValidationError("La sucursal no es válida")
        return branch_office_id_raw

    def _assert_branch_license(self, branch_office_id: int | None, user: UserPublic) -> None:
        if branch_office_id is None:
            return
        branch = self.db.get(BranchOffice, branch_office_id)
        if branch is None or not branch.is_active:
            raise UserValidationError("La sucursal no existe")
        assert_row_license(
            branch,
            license_scope_for_user(user),
            not_found_exc=UserValidationError,
        )

    def _resolve_status_id(
        self,
        *,
        active: bool | None = None,
        status_id_raw: str | None = None,
    ) -> int:
        if status_id_raw is not None and str(status_id_raw).strip():
            try:
                status_id = int(status_id_raw)
            except ValueError as exc:
                raise UserValidationError("El estado no es válido") from exc
            if self.db.get(Status, status_id) is None:
                raise UserValidationError("El estado no existe")
            return status_id
        if active is not None:
            return status_id_from_active(active)
        return STATUS_ABIERTO_ID

    @staticmethod
    def _can_authenticate(row: User) -> bool:
        return row.deleted_date is None and active_from_status_id(row.status_id)

    def assert_user_license_active(self, row: User) -> None:
        """Admin plataforma (sin license_id) entra siempre. Resto requiere licencia vigente."""
        if row.license_id is None or row.license_id < 1:
            if role_from_id(row.rol_id) == "admin":
                return
            raise LicenseExpiredError("Su cuenta no tiene licencia asignada")

        license_row = self.db.get(License, row.license_id)
        if license_row is None:
            raise LicenseExpiredError("La licencia no existe")
        if not license_is_usable(license_row):
            raise LicenseExpiredError("La licencia ha vencido. Contacte al administrador")

    def _active_filter(self, stmt):
        return stmt.where(User.deleted_date.is_(None))

    def _find_by_email(self, email: str, except_id: int | None = None) -> User | None:
        normalized = self.normalize_email(email)
        stmt = self._active_filter(select(User)).where(func.lower(User.email) == normalized)
        if except_id is not None:
            stmt = stmt.where(User.id != except_id)
        return self.db.scalars(stmt).first()

    def count_active(self) -> int:
        stmt = self._active_filter(select(func.count()).select_from(User))
        return int(self.db.scalar(stmt) or 0)

    def ensure_default_admin(self) -> None:
        if self.count_active() > 0:
            return

        settings = get_settings()
        now = self._now()
        row = User(
            rol_id=ADMIN_ROL_ID,
            status_id=STATUS_ABIERTO_ID,
            full_name="Administrador",
            email=self.normalize_email(settings.default_admin_email),
            password=hash_password(settings.default_admin_password),
            must_change_password=True,
            added_date=now,
            updated_date=now,
            deleted_date=None,
        )
        self.db.add(row)
        self.db.commit()

    def authenticate(self, email: str, password: str) -> User:
        normalized = self.normalize_email(email)
        row = self.db.scalars(
            self._active_filter(select(User)).where(func.lower(User.email) == normalized),
        ).first()
        if row is None or not verify_password(password, row.password):
            raise AuthFailedError()
        if not self._can_authenticate(row):
            raise AuthFailedError()
        self.assert_user_license_active(row)
        return row

    def list_all(self, current_user: UserPublic) -> list[UserPublic]:
        rol_labels = self._rol_labels_by_id()
        stmt = self._active_filter(select(User)).order_by(User.full_name)
        stmt = apply_license_scope(stmt, User, license_scope_for_user(current_user))
        return [
            self.to_public(row, rol_label=rol_labels.get(row.rol_id))
            for row in self.db.scalars(stmt).all()
        ]

    def list_by_rol_id(self, rol_id: int, current_user: UserPublic) -> list[UserPublic]:
        rol_labels = self._rol_labels_by_id()
        stmt = (
            self._active_filter(select(User))
            .where(User.rol_id == rol_id)
            .order_by(User.full_name)
        )
        stmt = apply_license_scope(stmt, User, license_scope_for_user(current_user))
        return [
            self.to_public(row, rol_label=rol_labels.get(row.rol_id))
            for row in self.db.scalars(stmt).all()
            if self._can_authenticate(row)
        ]

    def list_washers_by_branch_office(
        self,
        branch_office_id: int,
        current_user: UserPublic,
    ) -> list[UserPublic]:
        if branch_office_id < 1:
            return []
        self._assert_branch_license(branch_office_id, current_user)
        rol_labels = self._rol_labels_by_id()
        washer_ids = self._branch_washer.list_washer_ids_for_branch(branch_office_id)
        if not washer_ids:
            return []
        stmt = (
            self._active_filter(select(User))
            .where(User.id.in_(washer_ids), User.rol_id == WASHER_ROL_ID)
            .order_by(User.full_name)
        )
        stmt = apply_license_scope(stmt, User, license_scope_for_user(current_user))
        return [
            self.to_public(row, rol_label=rol_labels.get(row.rol_id))
            for row in self.db.scalars(stmt).all()
            if self._can_authenticate(row)
        ]

    def get_by_id(self, user_id: int, current_user: UserPublic | None = None) -> UserPublic:
        row = self.db.get(User, user_id)
        if row is None or not row.is_active:
            raise UserNotFoundError()
        if current_user is not None:
            assert_row_license(row, license_scope_for_user(current_user), not_found_exc=UserNotFoundError)
        return self.to_public(row)

    def get_row_by_id(self, user_id: int) -> User:
        row = self.db.get(User, user_id)
        if row is None or not row.is_active:
            raise UserNotFoundError()
        return row

    def create(self, data: UserCreate, current_user: UserPublic) -> UserPublic:
        full_name = data.fullName.strip()
        if not full_name:
            raise UserValidationError("El nombre completo es obligatorio")

        email = self._resolve_email(data.email)

        rol_id = role_id_from_role(data.role)
        if rol_id is None:
            raise UserValidationError("El rol no es válido")

        raw_password = (data.password or "").strip()
        if rol_id == WASHER_ROL_ID:
            stored_password = hash_password(raw_password) if raw_password else hash_password(secrets.token_urlsafe(32))
        else:
            if len(raw_password) < 6:
                raise UserValidationError("La contraseña debe tener al menos 6 caracteres")
            stored_password = hash_password(raw_password)

        status_id = self._resolve_status_id(
            active=data.active,
            status_id_raw=data.statusId,
        )
        license_id = effective_license_id_for_write(
            self.db,
            current_user,
            data.licenseId,
            error_factory=UserValidationError,
        )

        now = self._now()
        row = User(
            rol_id=rol_id,
            license_id=license_id,
            status_id=status_id,
            full_name=full_name,
            email=email,
            password=stored_password,
            must_change_password=True,
            added_date=now,
            updated_date=now,
            deleted_date=None,
        )
        try:
            self.db.add(row)
            self.db.flush()
            if not row.id:
                raise UserValidationError("No se pudo crear el usuario")

            if rol_id == WASHER_ROL_ID:
                branch_office_id = self._parse_branch_office_id(data.branchOfficeId)
                if branch_office_id is None:
                    raise UserValidationError("Seleccione una sucursal para el lavador")
                self._assert_branch_license(branch_office_id, current_user)
                self._branch_washer.assign_washer_to_branch(
                    row.id,
                    branch_office_id,
                    week_percentage=data.weekPercentage,
                    sunday_percentage=data.sundayPercentage,
                    daily_goal=data.dailyGoal,
                    daily_goal_percentage=data.dailyGoalPercentage,
                    commit=False,
                )
            elif rol_id == MANAGER_ROL_ID:
                branch_office_id = self._parse_branch_office_id(data.branchOfficeId)
                if branch_office_id is None:
                    raise UserValidationError("Seleccione una sucursal para el gerente")
                self._assert_branch_license(branch_office_id, current_user)
                self._branch_manager.assign_manager_to_branch(
                    row.id,
                    branch_office_id,
                    commit=False,
                )

            self.db.commit()
            self.db.refresh(row)
            return self.to_public(row)
        except (BranchOfficeWasherValidationError, BranchOfficeManagerValidationError) as exc:
            self.db.rollback()
            raise UserValidationError(str(exc)) from exc
        except Exception:
            self.db.rollback()
            raise

    def update(self, user_id: int, data: UserUpdate, current_user: UserPublic) -> UserPublic:
        row = self.db.get(User, user_id)
        if row is None:
            raise UserNotFoundError()
        scope = license_scope_for_user(current_user)
        assert_row_license(row, scope, not_found_exc=UserNotFoundError)

        if data.fullName is not None:
            name = data.fullName.strip()
            if not name:
                raise UserValidationError("El nombre completo no puede quedar vacío")
            row.full_name = name

        if data.email is not None:
            row.email = self._resolve_email(data.email)

        if data.licenseId is not None or scope is not None:
            row.license_id = effective_license_id_for_write(
                self.db,
                current_user,
                data.licenseId,
                error_factory=UserValidationError,
            )

        if data.password is not None and data.password:
            if len(data.password) < 6:
                raise UserValidationError("La contraseña debe tener al menos 6 caracteres")
            row.password = hash_password(data.password)
            row.must_change_password = True

        new_rol_id = row.rol_id
        if data.role is not None:
            rol_id = role_id_from_role(data.role)
            if rol_id is None:
                raise UserValidationError("El rol no es válido")
            row.rol_id = rol_id
            new_rol_id = rol_id

        if data.statusId is not None or data.active is not None:
            row.status_id = self._resolve_status_id(
                active=data.active,
                status_id_raw=data.statusId,
            )

        try:
            if new_rol_id == WASHER_ROL_ID and data.branchOfficeId is not None:
                branch_office_id = self._parse_branch_office_id(data.branchOfficeId)
                if branch_office_id is not None:
                    self._assert_branch_license(branch_office_id, current_user)
                    self._branch_manager.soft_delete_for_manager(user_id, commit=False)
                    self._branch_washer.assign_washer_to_branch(
                        user_id,
                        branch_office_id,
                        week_percentage=data.weekPercentage,
                        sunday_percentage=data.sundayPercentage,
                        daily_goal=data.dailyGoal,
                        daily_goal_percentage=data.dailyGoalPercentage,
                        commit=False,
                    )
            elif (
                new_rol_id == WASHER_ROL_ID
                and data.branchOfficeId is None
                and (
                    data.weekPercentage is not None
                    or data.sundayPercentage is not None
                    or data.dailyGoal is not None
                    or data.dailyGoalPercentage is not None
                )
            ):
                self._branch_washer.update_washer_percentages(
                    user_id,
                    week_percentage=data.weekPercentage,
                    sunday_percentage=data.sundayPercentage,
                    daily_goal=data.dailyGoal,
                    daily_goal_percentage=data.dailyGoalPercentage,
                    commit=False,
                )
            elif new_rol_id == MANAGER_ROL_ID and data.branchOfficeId is not None:
                branch_office_id = self._parse_branch_office_id(data.branchOfficeId)
                if branch_office_id is not None:
                    self._assert_branch_license(branch_office_id, current_user)
                    self._branch_washer.soft_delete_for_washer(user_id, commit=False)
                    self._branch_manager.assign_manager_to_branch(
                        user_id,
                        branch_office_id,
                        commit=False,
                    )
            elif data.role is not None:
                if new_rol_id != WASHER_ROL_ID:
                    self._branch_washer.soft_delete_for_washer(user_id, commit=False)
                if new_rol_id != MANAGER_ROL_ID:
                    self._branch_manager.soft_delete_for_manager(user_id, commit=False)

            row.updated_date = self._now()
            self.db.commit()
            self.db.refresh(row)
            return self.to_public(row)
        except (BranchOfficeWasherValidationError, BranchOfficeManagerValidationError) as exc:
            self.db.rollback()
            raise UserValidationError(str(exc)) from exc
        except Exception:
            self.db.rollback()
            raise

    def change_own_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> UserPublic:
        row = self.get_row_by_id(user_id)
        if not verify_password(current_password, row.password):
            raise UserValidationError("La contraseña actual no es correcta")
        if len(new_password) < 6:
            raise UserValidationError("La nueva contraseña debe tener al menos 6 caracteres")
        if verify_password(new_password, row.password):
            raise UserValidationError("La nueva contraseña debe ser distinta a la actual")
        row.password = hash_password(new_password)
        row.must_change_password = False
        row.updated_date = self._now()
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def delete(self, user_id: int, current_user: UserPublic) -> None:
        row = self.db.get(User, user_id)
        if row is None or not row.is_active:
            raise UserNotFoundError()
        assert_row_license(row, license_scope_for_user(current_user), not_found_exc=UserNotFoundError)
        now = self._now()
        self._branch_washer.soft_delete_for_washer(user_id, commit=False)
        self._branch_manager.soft_delete_for_manager(user_id, commit=False)
        row.deleted_date = now
        row.updated_date = now
        self.db.commit()
