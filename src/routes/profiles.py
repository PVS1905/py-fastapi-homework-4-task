from fastapi import Header

from database.models.accounts import UserProfileModel
from schemas.profiles import (
    BaseProfileResponseSchema,
    BaseProfileRequestSchema,
)

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_jwt_auth_manager
from database import (
    get_db,
    UserModel,
)
from exceptions import BaseSecurityError
from security.interfaces import JWTAuthManagerInterface


from config import get_s3_storage_client
from storages import S3StorageInterface


router = APIRouter()


@router.post(
    "/users/{user_id}/profile/",
    response_model=BaseProfileResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def register_user_profile(
        user_id: int,
        user_data: BaseProfileRequestSchema,
        Authorization: str = Header(..., description="Bearer токен у форматі 'Bearer <token>'"),
        db: AsyncSession = Depends(get_db),
        jwt_auth_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        s3_storage: S3StorageInterface = Depends(get_s3_storage_client)
) -> BaseProfileResponseSchema:
    """Створення профілю користувача"""

    if not Authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )

    token_str = Authorization.removeprefix("Bearer ").strip()

    try:
        token_data = jwt_auth_manager.decode_access_token(token_str)
        current_user_id = int(token_data["user_id"])
    except (BaseSecurityError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired."
        )

    # Перевірка прав доступу
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this profile."
        )

    user = await db.get(UserModel, current_user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active."
        )

    if user_data.avatar and user_data.avatar.content_type:
        if not user_data.avatar.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not an image"
            )

        contents = await user_data.avatar.read()
        filename = f"avatars/{user_id}_avatar.jpg"
    else:
        contents = None
        filename = None

    try:
        profile_data = user_data.model_dump(exclude={"avatar"}, exclude_unset=True)

        if "first_name" in profile_data:
            profile_data["first_name"] = profile_data["first_name"].lower()
        if "last_name" in profile_data:
            profile_data["last_name"] = profile_data["last_name"].lower()

        new_profile = UserProfileModel(
            user_id=user_id,
            **profile_data
        )

        if contents and filename:
            await s3_storage.upload_file(filename, contents)
            new_profile.avatar = filename

        if user.profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has a profile."
            )

        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        return BaseProfileResponseSchema.model_validate(new_profile)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error when creating a profile"
        )
