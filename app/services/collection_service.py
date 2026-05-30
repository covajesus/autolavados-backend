import calendar
from copy import deepcopy
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.branch_scope import branch_scope_for_user
from app.core.datetime_utils import business_now, business_today
from app.core.license_helpers import license_id_from_branch
from app.core.license_scope import (
    assert_row_license,
    effective_license_id_for_write,
    license_scope_for_user,
)
from app.core.pricing import ticket_totals_from_subtotal
from app.models.branch_collection import BranchCollection
from app.models.branch_office import BranchOffice
from app.schemas.collection import (
    CollectionCalendarDay,
    CollectionCalendarResponse,
    CollectionDayResponse,
    CollectionUpsert,
)
from app.schemas.user import UserPublic


class CollectionValidationError(Exception):
    pass


class CollectionForbiddenError(Exception):
    pass


def empty_earnings_bucket() -> dict[str, int]:
    return {"ticket_count": 0, "subtotal": 0, "iva": 0, "total": 0}


def apply_manual_gross_to_bucket(bucket: dict[str, int], gross_amount: int) -> None:
    if gross_amount <= 0:
        return
    pricing = ticket_totals_from_subtotal(gross_amount, apply_iva=False)
    if bucket["ticket_count"] == 0:
        bucket["ticket_count"] = 1
    bucket["subtotal"] += pricing["subtotal"]
    bucket["iva"] += pricing["iva"]
    bucket["total"] += pricing["total"]


class CollectionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _now():
        return business_now()

    @staticmethod
    def _require_admin(user: UserPublic) -> None:
        if branch_scope_for_user(user) is not None:
            raise CollectionForbiddenError()

    def _assert_branch_access(self, user: UserPublic, branch_office_id: int) -> None:
        scope = branch_scope_for_user(user)
        if scope == 0:
            raise CollectionValidationError("You have no branch assigned")
        if scope is not None and scope != branch_office_id:
            raise CollectionForbiddenError()
        branch = self._validate_branch(branch_office_id)
        assert_row_license(
            branch,
            license_scope_for_user(user),
            not_found_exc=CollectionForbiddenError,
        )

    def _validate_branch(self, branch_office_id: int) -> BranchOffice:
        if branch_office_id < 1:
            raise CollectionValidationError("Invalid branch")
        branch = self.db.get(BranchOffice, branch_office_id)
        if branch is None or not branch.is_active:
            raise CollectionValidationError("Branch not found")
        return branch

    def _active_stmt(self):
        return select(BranchCollection).where(BranchCollection.deleted_date.is_(None))

    def get_manual_gross(self, branch_office_id: int, collection_date: date) -> int:
        row = self.db.scalars(
            self._active_stmt().where(
                BranchCollection.branch_office_id == branch_office_id,
                BranchCollection.collection_date == collection_date,
            ),
        ).first()
        if row is None:
            return 0
        return max(0, int(row.gross_amount or 0))

    def list_manual_for_branch(
        self,
        branch_office_id: int,
        user: UserPublic | None = None,
    ) -> list[BranchCollection]:
        rows = list(
            self.db.scalars(
                self._active_stmt().where(
                    BranchCollection.branch_office_id == branch_office_id,
                ),
            ).all(),
        )
        if user is not None:
            scope = license_scope_for_user(user)
            if scope == 0:
                return []
            if scope is not None:
                rows = [row for row in rows if row.license_id == scope]
        return rows

    def list_manual_all(self, user: UserPublic | None = None) -> list[BranchCollection]:
        rows = list(self.db.scalars(self._active_stmt()).all())
        if user is not None:
            scope = license_scope_for_user(user)
            if scope == 0:
                return []
            if scope is not None:
                rows = [row for row in rows if row.license_id == scope]
        return rows

    def merge_into_date_buckets(
        self,
        buckets: dict[str, dict[str, int]],
        branch_office_id: int,
        user: UserPublic | None = None,
    ) -> None:
        for row in self.list_manual_for_branch(branch_office_id, user):
            if row.collection_date is None or row.gross_amount <= 0:
                continue
            day_key = row.collection_date.isoformat()
            if day_key not in buckets:
                buckets[day_key] = empty_earnings_bucket()
            apply_manual_gross_to_bucket(buckets[day_key], int(row.gross_amount))

    def merge_into_branch_buckets(
        self,
        buckets: dict[int, dict[str, int]],
        *,
        branch_office_id: int | None = None,
        user: UserPublic | None = None,
    ) -> None:
        for row in self.list_manual_all(user):
            if row.gross_amount <= 0:
                continue
            key = int(row.branch_office_id)
            if branch_office_id is not None and key != branch_office_id:
                continue
            if key not in buckets:
                buckets[key] = empty_earnings_bucket()
            apply_manual_gross_to_bucket(buckets[key], int(row.gross_amount))

    def upsert(
        self,
        user: UserPublic,
        branch_office_id: int,
        collection_date: date,
        data: CollectionUpsert,
    ) -> None:
        self._require_admin(user)
        self._assert_branch_access(user, branch_office_id)

        gross = int(data.gross_amount)
        license_id = effective_license_id_for_write(
            self.db,
            user,
            data.licenseId,
            error_factory=CollectionValidationError,
        ) or license_id_from_branch(self.db, branch_office_id)
        now = self._now()
        row = self.db.scalars(
            self._active_stmt().where(
                BranchCollection.branch_office_id == branch_office_id,
                BranchCollection.collection_date == collection_date,
            ),
        ).first()

        if gross <= 0:
            if row is not None:
                row.deleted_date = now
                row.updated_date = now
                self.db.commit()
        elif row is None:
            self.db.add(
                BranchCollection(
                    branch_office_id=branch_office_id,
                    collection_date=collection_date,
                    gross_amount=gross,
                    license_id=license_id,
                    added_date=now,
                    updated_date=now,
                    deleted_date=None,
                ),
            )
            self.db.commit()
        else:
            row.gross_amount = gross
            if license_id is not None:
                row.license_id = license_id
            row.updated_date = now
            self.db.commit()

    def build_day_response(
        self,
        user: UserPublic,
        branch_office_id: int,
        collection_date: date,
        *,
        branch_name: str | None = None,
        tickets_bucket: dict[str, int] | None = None,
    ) -> CollectionDayResponse:
        self._require_admin(user)
        self._assert_branch_access(user, branch_office_id)
        if branch_name is None:
            branch = self._validate_branch(branch_office_id)
            branch_name = branch.branch_office

        license_id = license_id_from_branch(self.db, branch_office_id)
        tickets = deepcopy(tickets_bucket or empty_earnings_bucket())
        manual_gross = self.get_manual_gross(branch_office_id, collection_date)
        combined = deepcopy(tickets)
        apply_manual_gross_to_bucket(combined, manual_gross)

        return CollectionDayResponse(
            branch_office_id=str(branch_office_id),
            branch_name=branch_name,
            collection_date=collection_date,
            licenseId=license_id,
            manual_gross_amount=manual_gross,
            tickets_ticket_count=tickets["ticket_count"],
            tickets_subtotal=tickets["subtotal"],
            tickets_iva=tickets["iva"],
            tickets_total=tickets["total"],
            ticket_count=combined["ticket_count"],
            subtotal=combined["subtotal"],
            iva=combined["iva"],
            total=combined["total"],
        )

    @staticmethod
    def tickets_bucket_for_date(
        date_buckets: dict[str, dict[str, int]],
        collection_date: date,
    ) -> dict[str, int]:
        return deepcopy(date_buckets.get(collection_date.isoformat(), empty_earnings_bucket()))

    @staticmethod
    def day_is_recorded(tickets: dict[str, int], manual_gross: int) -> bool:
        combined = deepcopy(tickets)
        apply_manual_gross_to_bucket(combined, manual_gross)
        return combined["ticket_count"] > 0 or combined["total"] > 0

    def build_calendar_month(
        self,
        user: UserPublic,
        branch_office_id: int,
        *,
        year: int,
        month: int,
        tickets_date_buckets: dict[str, dict[str, int]],
    ) -> CollectionCalendarResponse:
        self._require_admin(user)
        if month < 1 or month > 12:
            raise CollectionValidationError("Mes no válido")
        if year < 2000 or year > 2100:
            raise CollectionValidationError("Año no válido")

        self._assert_branch_access(user, branch_office_id)
        branch = self._validate_branch(branch_office_id)

        last_day = calendar.monthrange(year, month)[1]
        today = business_today()

        manual_by_day: dict[str, int] = {}
        for row in self.list_manual_for_branch(branch_office_id, user):
            if row.collection_date is None:
                continue
            if row.collection_date.year != year or row.collection_date.month != month:
                continue
            manual_by_day[row.collection_date.isoformat()] = max(0, int(row.gross_amount or 0))

        days: list[CollectionCalendarDay] = []
        for day_num in range(1, last_day + 1):
            day = date(year, month, day_num)
            day_key = day.isoformat()
            tickets = self.tickets_bucket_for_date(tickets_date_buckets, day)
            manual = manual_by_day.get(day_key, 0)
            combined = deepcopy(tickets)
            apply_manual_gross_to_bucket(combined, manual)

            if day > today:
                status = "future"
            elif self.day_is_recorded(tickets, manual):
                status = "ok"
            else:
                status = "missing"

            days.append(
                CollectionCalendarDay(
                    date=day,
                    status=status,
                    has_tickets=tickets["ticket_count"] > 0,
                    has_manual=manual > 0,
                    tickets_total=tickets["total"],
                    manual_gross_amount=manual,
                    total=combined["total"],
                ),
            )

        return CollectionCalendarResponse(
            branch_office_id=str(branch_office_id),
            branch_name=branch.branch_office,
            year=year,
            month=month,
            days=days,
        )
