from typing import Literal

UserRole = Literal["admin", "manager", "washer"]

ROLE_FROM_ID: dict[int, UserRole] = {
    1: "admin",  # Super Administrador
    2: "admin",
    3: "manager",
    4: "washer",
}

ID_FROM_ROLE: dict[UserRole, int] = {
    "admin": 2,
    "manager": 3,
    "washer": 4,
}

SUPER_ADMIN_ROL_ID: int = 1
ADMIN_ROL_ID: int = ID_FROM_ROLE["admin"]
WASHER_ROL_ID: int = ID_FROM_ROLE["washer"]
MANAGER_ROL_ID: int = ID_FROM_ROLE["manager"]

ADMIN_ROL_IDS: frozenset[int] = frozenset({SUPER_ADMIN_ROL_ID, ADMIN_ROL_ID})


def is_admin_rol_id(rol_id: int | None) -> bool:
    return rol_id in ADMIN_ROL_IDS


def role_from_id(rol_id: int | None) -> UserRole:
    if rol_id is None:
        return "washer"
    return ROLE_FROM_ID.get(rol_id, "washer")


def role_id_from_role(role: str) -> int | None:
    if role not in ID_FROM_ROLE:
        return None
    return ID_FROM_ROLE[role]  # type: ignore[index]
