from typing import Literal

UserRole = Literal["admin", "manager", "washer"]

ROLE_FROM_ID: dict[int, UserRole] = {
    1: "washer",
    2: "admin",
    3: "manager",
}

ID_FROM_ROLE: dict[UserRole, int] = {
    "admin": 2,
    "manager": 3,
    "washer": 1,
}

ADMIN_ROL_ID: int = ID_FROM_ROLE["admin"]
WASHER_ROL_ID: int = ID_FROM_ROLE["washer"]
MANAGER_ROL_ID: int = ID_FROM_ROLE["manager"]


def role_from_id(rol_id: int | None) -> UserRole:
    if rol_id is None:
        return "washer"
    return ROLE_FROM_ID.get(rol_id, "washer")


def role_id_from_role(role: str) -> int | None:
    if role not in ID_FROM_ROLE:
        return None
    return ID_FROM_ROLE[role]  # type: ignore[index]
