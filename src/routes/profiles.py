from fastapi import Header

from database.models.accounts import UserProfileModel
from schemas.profiles import BaseProfileResponseSchema, BaseProfileRequestSchema, AvatarUploadResponse
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
router = APIRouter()


# Метод HTTP :POST
# Шлях :/users/{user_id}/profile/
# Відповідь :ProfileResponseSchema
# Авторизація : Потрібно дійсний Bearerтокен у Authorizationзаголовку.
# # Write your code here
# POST /users/{user_id}/profile/

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
        jwt_auth_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> BaseProfileResponseSchema:
    """Створення профілю користувача"""

    # Обробка токена
    if not Authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний формат заголовка Authorization. Очікується 'Bearer <token>'"
        )

    token_str = Authorization.removeprefix("Bearer ").strip()

    try:
        token_data = jwt_auth_manager.decode_access_token(token_str)
        current_user_id = int(token_data["user_id"])
    except (BaseSecurityError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний або протермінований токен"
        )

    # Перевірка прав доступу
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостатньо прав для створення профілю"
        )

    # Отримання та перевірка користувача
    user = await db.get(UserModel, current_user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Користувача не знайдено або обліковий запис не активний"
        )

    # if user.profile:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Профіль вже існує для цього користувача"
    #     )

    new_profile = UserProfileModel(
        user_id=user_id,
        **user_data.dict(exclude_unset=True)
    )

    try:
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


from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from config import get_s3_storage_client
from database import get_db, UserModel
from storages import S3StorageInterface
from exceptions import S3FileUploadError, S3ConnectionError

@router.post("/users/{user_id}/avatar/", response_model=AvatarUploadResponse)
async def upload_avatar(
    user_id: int,
    file: UploadFile = File(...),
    Authorization: str = Header(..., description="Bearer токен у форматі 'Bearer <token>'"),
    db: AsyncSession = Depends(get_db),
    jwt_auth_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    s3_storage: S3StorageInterface = Depends(get_s3_storage_client)
):
    if not Authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний формат заголовка Authorization. Очікується 'Bearer <token>'"
        )

    token_str = Authorization.removeprefix("Bearer ").strip()

    try:
        token_data = jwt_auth_manager.decode_access_token(token_str)
        current_user_id = int(token_data["user_id"])
    except (BaseSecurityError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний або протермінований токен"
        )

    # Перевірка прав доступу
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостатньо прав для завантаження аватара"
        )

    # Отримання та перевірка користувача
    user = await db.get(UserModel, current_user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Користувача не знайдено або обліковий запис не активний"
        )

    # Перевірка типу файлу
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл не є зображенням"
        )

    # Читання вмісту файлу
    contents = await file.read()

    # Генерація імені файлу
    filename = f"user_{user_id}_avatar.jpg"

    try:
        # Завантаження файлу в S3
        await s3_storage.upload_file(filename, contents)

        # Отримання URL файлу
        avatar_url = await s3_storage.get_file_url(filename)

        # Оновлення профілю користувача
        if user.profile:
            user.profile.avatar = avatar_url
            await db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Профіль користувача не знайдено. Спочатку створіть профіль."
            )

        return AvatarUploadResponse(detail="Аватар успішно завантажено", avatar_url=avatar_url)

    except (S3ConnectionError, S3FileUploadError) as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Помилка при завантаженні файлу: {str(e)}"
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Помилка при оновленні профілю"
        )
