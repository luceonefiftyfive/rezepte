import logging
from typing import Annotated

from app.core.database import get_db
from app.models.group import GroupCreate, GroupOut, GroupUpdate
from app.models.user import Role
from app.routers.users import get_current_user, require_super_admin
from app.services.group_service import GroupService
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

log = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["groups"])


def _assigned_group_ids(current_user: dict) -> set[str]:
    return {group["group_id"] for group in current_user.get("groups", [])}


def _manageable_group_ids(current_user: dict) -> set[str]:
    return {
        group["group_id"]
        for group in current_user.get("groups", [])
        if group["role"] in {Role.admin.value, Role.author.value}
    }


@router.get("", response_model=list[GroupOut])
async def list_groups(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    manageable_only: bool = False,
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


@router.get("/{group_id}", response_model=GroupOut)
async def get_group(
    group_id: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> GroupOut:
    if not current_user.get(
        "is_super_admin", False
    ) and group_id not in _assigned_group_ids(current_user):
        # Re-use not found to avoid leaking group IDs to unauthorized users.
        raise HTTPException(status_code=404, detail="Group not found")
    return await GroupService(db).get_group_or_404(group_id)


@router.post("", response_model=GroupOut, status_code=201)
async def create_group(
    data: GroupCreate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    _: Annotated[dict, Depends(require_super_admin)],
) -> GroupOut:
    return await GroupService(db).create_group(data)


@router.put("/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: str,
    data: GroupUpdate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    _: Annotated[dict, Depends(require_super_admin)],
) -> GroupOut:
    return await GroupService(db).update_group(group_id, data)


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    _: Annotated[dict, Depends(require_super_admin)],
) -> dict[str, int | str | bool]:
    return await GroupService(db).delete_group(group_id)
