from fastapi import Header

from database.models.accounts import UserProfileModel
from schemas.profiles import (
    BaseProfileResponseSchema,
    BaseProfileRequestSchema,
)
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_jwt_auth_manager
from database import (
    get_db,
    UserModel,
)
from exceptions import BaseSecurityError
from security.interfaces import JWTAuthManagerInterface


from fastapi import File, UploadFile
from config import get_s3_storage_client
from storages import S3StorageInterface
from exceptions import S3FileUploadError, S3ConnectionError


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

    # Обробка токена
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

    # Отримання та перевірка користувача
    user = await db.get(UserModel, current_user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active."
        )

    if not user_data.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later."
        )

    # Читання вмісту файлу
    contents = await user_data.read()
    filename = f"user_{user_id}_avatar.jpg"

    try:
        new_profile = UserProfileModel(
            user_id=user_id,
            **user_data.dict(exclude_unset=True)
        )
        # Завантаження файлу в S3
        await s3_storage.upload_file(filename, contents)

        # Отримання URL файлу
        avatar_url = await s3_storage.get_file_url(filename)
        if user.profile:
            user.profile.avatar = avatar_url
            await db.commit()
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        return BaseProfileResponseSchema.model_validate(new_profile)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Помилка при створенні профілю"
        )
