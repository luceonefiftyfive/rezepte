import logging

from app.models.group import GroupCreate, GroupOut, GroupUpdate
from app.models.user import Role
from app.routers.users import CurrentUser, Db
from app.services.group_service import GroupService
from litestar import Router, delete, get, post, put
from litestar.exceptions import HTTPException
from litestar.params import FromPath, FromQuery

log = logging.getLogger(__name__)


def _assigned_group_ids(current_user: dict) -> set[str]:
    return {group["group_id"] for group in current_user.get("groups", [])}


def _manageable_group_ids(current_user: dict) -> set[str]:
    return {
        group["group_id"]
        for group in current_user.get("groups", [])
        if group["role"] in {Role.admin.value, Role.author.value}
    }


@get("")
async def list_groups(
    db: Db,
    current_user: CurrentUser,
    manageable_only: FromQuery[bool] = False,
) -> list[GroupOut]:
    service = GroupService(db)
    if current_user.get("is_super_admin", False):
        return await service.list_groups()

    group_ids = (
        _manageable_group_ids(current_user)
        if manageable_only
        else _assigned_group_ids(current_user)
    )
    if not group_ids:
        return []
    ret = await service.list_groups(group_ids=group_ids)
    log.info(f"Listed groups: {ret}")
    return ret


@get("/{group_id:str}")
async def get_group(
    group_id: FromPath[str],
    db: Db,
    current_user: CurrentUser,
) -> GroupOut:
    if not current_user.get(
        "is_super_admin", False
    ) and group_id not in _assigned_group_ids(current_user):
        # Re-use not found to avoid leaking group IDs to unauthorized users.
        raise HTTPException(status_code=404, detail="Group not found")
    return await GroupService(db).get_group_or_404(group_id)


@post("", status_code=201)
async def create_group(
    data: GroupCreate,
    db: Db,
    super_admin_user: CurrentUser,
) -> GroupOut:
    return await GroupService(db).create_group(data)


@put("/{group_id:str}")
async def update_group(
    group_id: FromPath[str],
    data: GroupUpdate,
    db: Db,
    super_admin_user: CurrentUser,
) -> GroupOut:
    return await GroupService(db).update_group(group_id, data)


@delete("/{group_id:str}", status_code=200)
async def delete_group(
    group_id: FromPath[str],
    db: Db,
    super_admin_user: CurrentUser,
) -> dict[str, int | str | bool]:
    return await GroupService(db).delete_group(group_id)


router = Router(
    path="/groups",
    route_handlers=[
        list_groups,
        get_group,
        create_group,
        update_group,
        delete_group,
    ],
)
