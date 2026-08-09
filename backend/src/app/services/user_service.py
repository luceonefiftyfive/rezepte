import logging
from base64 import urlsafe_b64decode, urlsafe_b64encode
from functools import lru_cache
from typing import Any

from app.core.security import hash_password, now_utc, verify_password
from app.core.settings import settings
from app.models.user import GroupRole, Role, UserCreate
from app.repositories.user_repository import UserRepository
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

log = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.repository = UserRepository(db)

    async def bootstrap_superuser(self) -> None:
        await self.repository.ensure_indexes()
        existing = await self.repository.find_active_super_admin()
        if existing:
            log.info("Superuser already exists, skipping bootstrap")
            return

        user = UserCreate(
            username=settings.superuser_username,
            password=settings.superuser_password,
            first_name="System",
            last_name="Administrator",
            email=settings.superuser_email,
            groups=[],
            is_super_admin=True,
        )
        doc = self.create_user_document(user)
        doc["email_verified"] = True
        await self.repository.insert(doc)
        log.info(
            "Bootstrapped superuser with username '%s'", settings.superuser_username
        )

    def create_user_document(self, data: UserCreate) -> dict:
        timestamp = now_utc()
        return {
            "username": data.username,
            "password_hash": hash_password(data.password),
            "first_name": data.first_name,
            "last_name": data.last_name,
            "email": str(data.email),
            "email_verified": False,
            "groups": [group.model_dump() for group in data.groups],
            "is_super_admin": data.is_super_admin,
            "is_active": True,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

    async def get_user_or_404(self, user_id: str) -> dict:
        user = await self.repository.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def authenticate_user(self, username: str, password: str) -> dict | None:
        log.info("Authenticating user '%s'", username)
        user = await self.repository.find_by_username(username, active_only=True)
        if not user:
            log.info(
                "Authentication failed for user '%s': user not found or inactive",
                username,
            )
            return None
        if not verify_password(password, user["password_hash"]):
            log.info("Authentication failed for user '%s': invalid password", username)
            return None
        log.info("User '%s' authenticated successfully", username)
        return user

    @staticmethod
    def _b64url_encode(raw: bytes) -> str:
        return urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64url_decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return urlsafe_b64decode(f"{value}{padding}")

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_webauthn() -> dict[str, Any]:
        try:
            from webauthn import (  # type: ignore
                generate_authentication_options,
                generate_registration_options,
                options_to_json,
                verify_authentication_response,
                verify_registration_response,
            )
            from webauthn.helpers.structs import (  # type: ignore
                AttestationConveyancePreference,
                AuthenticatorSelectionCriteria,
                PublicKeyCredentialDescriptor,
                ResidentKeyRequirement,
                UserVerificationRequirement,
            )
        except ImportError as exc:  # pragma: no cover
            raise HTTPException(
                status_code=500,
                detail=(
                    "Passkey support is not available on the server. "
                    "Install the 'webauthn' package in the backend environment."
                ),
            ) from exc

        return {
            "generate_authentication_options": generate_authentication_options,
            "generate_registration_options": generate_registration_options,
            "options_to_json": options_to_json,
            "verify_authentication_response": verify_authentication_response,
            "verify_registration_response": verify_registration_response,
            "AttestationConveyancePreference": AttestationConveyancePreference,
            "AuthenticatorSelectionCriteria": AuthenticatorSelectionCriteria,
            "PublicKeyCredentialDescriptor": PublicKeyCredentialDescriptor,
            "ResidentKeyRequirement": ResidentKeyRequirement,
            "UserVerificationRequirement": UserVerificationRequirement,
        }

    @staticmethod
    def _parse_options(options_to_json, generated_options: Any) -> dict[str, Any]:
        raw = options_to_json(generated_options)
        if isinstance(raw, str):
            import json

            return json.loads(raw)
        if isinstance(raw, dict):
            return raw
        raise HTTPException(
            status_code=500, detail="Could not serialize passkey options"
        )

    async def begin_passkey_registration(self, current_user: dict) -> dict[str, Any]:
        webauthn = self._load_webauthn()
        existing_credentials = []
        for credential in current_user.get("passkeys", []):
            existing_credentials.append(
                webauthn["PublicKeyCredentialDescriptor"](
                    id=self._b64url_decode(credential["credential_id"])
                )
            )

        user_display_name = (
            f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()
            or current_user["username"]
        )
        user_verification = (
            webauthn["UserVerificationRequirement"].REQUIRED
            if settings.webauthn_require_user_verification
            else webauthn["UserVerificationRequirement"].PREFERRED
        )
        options = webauthn["generate_registration_options"](
            rp_id=settings.webauthn_rp_id,
            rp_name=settings.webauthn_rp_name,
            user_id=str(current_user["_id"]).encode("utf-8"),
            user_name=current_user["username"],
            user_display_name=user_display_name,
            exclude_credentials=existing_credentials,
            attestation=webauthn["AttestationConveyancePreference"].NONE,
            authenticator_selection=webauthn["AuthenticatorSelectionCriteria"](
                resident_key=webauthn["ResidentKeyRequirement"].PREFERRED,
                user_verification=user_verification,
            ),
        )

        options_payload = self._parse_options(webauthn["options_to_json"], options)
        challenge = options_payload.get("challenge")
        if not isinstance(challenge, str) or not challenge:
            raise HTTPException(
                status_code=500, detail="Invalid passkey registration challenge"
            )

        await self.repository.update_by_object_id(
            current_user["_id"],
            {
                "passkey_registration_challenge": challenge,
                "passkey_registration_started_at": now_utc(),
                "updated_at": now_utc(),
            },
        )
        return options_payload

    async def complete_passkey_registration(
        self,
        current_user: dict,
        credential: dict[str, Any],
        credential_name: str | None = None,
    ) -> dict:
        webauthn = self._load_webauthn()
        expected_challenge = current_user.get("passkey_registration_challenge")
        if not expected_challenge:
            raise HTTPException(
                status_code=400,
                detail="No passkey registration in progress. Request options first.",
            )

        try:
            verification = webauthn["verify_registration_response"](
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=settings.webauthn_rp_id,
                expected_origin=settings.webauthn_origin,
                require_user_verification=settings.webauthn_require_user_verification,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Passkey registration failed: {exc}"
            ) from exc

        credential_id = self._b64url_encode(verification.credential_id)
        passkeys = [*current_user.get("passkeys", [])]
        if any(item.get("credential_id") == credential_id for item in passkeys):
            raise HTTPException(status_code=409, detail="Passkey already registered")

        timestamp = now_utc()
        passkeys.append(
            {
                "credential_id": credential_id,
                "public_key": self._b64url_encode(verification.credential_public_key),
                "sign_count": int(verification.sign_count),
                "transports": credential.get("response", {}).get("transports", []),
                "device_type": str(verification.credential_device_type),
                "backed_up": bool(verification.credential_backed_up),
                "name": credential_name.strip() if credential_name else None,
                "created_at": timestamp,
                "last_used_at": None,
            }
        )

        updated = await self.repository.update_by_object_id(
            current_user["_id"],
            {
                "passkeys": passkeys,
                "passkey_registration_challenge": None,
                "passkey_registration_started_at": None,
                "updated_at": timestamp,
            },
        )
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")
        return updated

    async def begin_passkey_authentication(self, username: str) -> dict[str, Any]:
        webauthn = self._load_webauthn()
        user = await self.repository.find_by_username(username, active_only=True)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username")

        passkeys = user.get("passkeys", [])
        if not passkeys:
            raise HTTPException(
                status_code=400,
                detail="No passkey registered for this user",
            )

        allow_credentials = [
            webauthn["PublicKeyCredentialDescriptor"](
                id=self._b64url_decode(item["credential_id"]),
                transports=item.get("transports") or None,
            )
            for item in passkeys
        ]
        user_verification = (
            webauthn["UserVerificationRequirement"].REQUIRED
            if settings.webauthn_require_user_verification
            else webauthn["UserVerificationRequirement"].PREFERRED
        )
        options = webauthn["generate_authentication_options"](
            rp_id=settings.webauthn_rp_id,
            allow_credentials=allow_credentials,
            user_verification=user_verification,
        )
        options_payload = self._parse_options(webauthn["options_to_json"], options)
        challenge = options_payload.get("challenge")
        if not isinstance(challenge, str) or not challenge:
            raise HTTPException(
                status_code=500, detail="Invalid passkey authentication challenge"
            )

        await self.repository.update_by_object_id(
            user["_id"],
            {
                "passkey_authentication_challenge": challenge,
                "passkey_authentication_started_at": now_utc(),
                "updated_at": now_utc(),
            },
        )
        return options_payload

    async def authenticate_user_with_passkey(
        self, username: str, credential: dict[str, Any]
    ) -> dict:
        webauthn = self._load_webauthn()
        user = await self.repository.find_by_username(username, active_only=True)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username")

        expected_challenge = user.get("passkey_authentication_challenge")
        if not expected_challenge:
            raise HTTPException(
                status_code=400,
                detail="No passkey authentication in progress. Request options first.",
            )

        credential_id = credential.get("id")
        if not isinstance(credential_id, str) or not credential_id:
            raise HTTPException(
                status_code=400, detail="Passkey credential id is missing"
            )

        passkeys = user.get("passkeys", [])
        index = next(
            (
                i
                for i, item in enumerate(passkeys)
                if item.get("credential_id") == credential_id
            ),
            -1,
        )
        if index < 0:
            raise HTTPException(status_code=401, detail="Unknown passkey credential")

        matched_passkey = passkeys[index]
        try:
            verification = webauthn["verify_authentication_response"](
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=settings.webauthn_rp_id,
                expected_origin=settings.webauthn_origin,
                credential_public_key=self._b64url_decode(
                    matched_passkey["public_key"]
                ),
                credential_current_sign_count=int(matched_passkey.get("sign_count", 0)),
                require_user_verification=settings.webauthn_require_user_verification,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=401, detail=f"Passkey authentication failed: {exc}"
            ) from exc

        timestamp = now_utc()
        passkeys[index] = {
            **matched_passkey,
            "sign_count": int(verification.new_sign_count),
            "last_used_at": timestamp,
        }
        updated = await self.repository.update_by_object_id(
            user["_id"],
            {
                "passkeys": passkeys,
                "passkey_authentication_challenge": None,
                "passkey_authentication_started_at": None,
                "updated_at": timestamp,
            },
        )
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")
        return updated

    async def ensure_username_and_email_unique(self, username: str, email: str) -> None:
        if await self.repository.find_by_username(username, active_only=True):
            raise HTTPException(status_code=409, detail="Username already exists")
        if await self.repository.find_by_email(email, active_only=True):
            raise HTTPException(status_code=409, detail="Email already exists")

    def assert_may_manage_groups(
        self, current_user: dict, new_groups: list[GroupRole]
    ) -> None:
        if current_user.get("is_super_admin", False):
            return

        admin_group_ids = {
            group["group_id"]
            for group in current_user.get("groups", [])
            if group["role"] == Role.admin.value
        }
        requested_group_ids = {group.group_id for group in new_groups}

        if not requested_group_ids.issubset(admin_group_ids):
            raise HTTPException(
                status_code=403,
                detail="You may only manage groups where you are admin",
            )

    async def create_user(self, data: UserCreate, current_user: dict) -> dict:
        if data.is_super_admin and not current_user.get("is_super_admin", False):
            raise HTTPException(
                status_code=403, detail="Only super-admin may create super-admin users"
            )

        self.assert_may_manage_groups(current_user, data.groups)
        await self.ensure_username_and_email_unique(data.username, str(data.email))
        return await self.repository.insert(self.create_user_document(data))

    async def update_own_profile(
        self, current_user: dict, first_name=None, last_name=None, email=None
    ) -> dict:
        update: dict = {}
        if first_name is not None:
            update["first_name"] = first_name
        if last_name is not None:
            update["last_name"] = last_name
        if email is not None:
            new_email = str(email)
            if await self.repository.email_exists_for_other_user(
                new_email, current_user["_id"]
            ):
                raise HTTPException(status_code=409, detail="Email already exists")
            update["email"] = new_email
            update["email_verified"] = False

        if not update:
            return current_user

        update["updated_at"] = now_utc()
        return await self.repository.update_by_object_id(current_user["_id"], update)

    async def update_user_groups(
        self, user_id: str, groups: list[GroupRole], current_user: dict
    ) -> dict:
        self.assert_may_manage_groups(current_user, groups)
        target = await self.get_user_or_404(user_id)
        return await self.repository.update_by_object_id(
            target["_id"],
            {
                "groups": [group.model_dump() for group in groups],
                "updated_at": now_utc(),
            },
        )

    async def update_super_admin_status(
        self, user_id: str, is_super_admin: bool, current_user: dict
    ) -> dict:
        target = await self.get_user_or_404(user_id)
        if target["_id"] == current_user["_id"] and not is_super_admin:
            if await self.repository.count_active_super_admins() <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="At least one active super-admin must remain",
                )
        return await self.repository.update_by_object_id(
            target["_id"],
            {"is_super_admin": is_super_admin, "updated_at": now_utc()},
        )

    async def soft_delete_user(self, user_id: str, current_user: dict) -> None:
        target = await self.get_user_or_404(user_id)
        if target["_id"] == current_user["_id"]:
            if await self.repository.count_active_super_admins() <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="At least one active super-admin must remain",
                )

        target_id = str(target["_id"])
        await self.repository.update_by_object_id(
            target["_id"],
            {
                "is_active": False,
                "deleted_username": target.get("username"),
                "deleted_email": target.get("email"),
                "username": f"deleted-{target_id}-username",
                "email": f"deleted-{target_id}@deleted.local",
                "updated_at": now_utc(),
            },
        )
