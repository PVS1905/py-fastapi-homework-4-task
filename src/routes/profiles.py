from fastapi import Header

from database.models.accounts import UserProfileModel
from schemas.profiles import BaseProfileResponseSchema, BaseProfileRequestSchema
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
        current_user_id = int(token_data["sub"])
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

    if user.profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Профіль вже існує для цього користувача"
        )

    # Створення профілю
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
# async def register_user(
#         user_id: int,
#         user_data: BaseProfileRequestSchema,
#         Authorization: str = Header(...),
#         db: AsyncSession = Depends(get_db),
#         jwt_auth_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
#
# ) -> BaseProfileResponseSchema:
#
#
#     if not Authorization.startswith("Bearer "):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid Authorization header format. Expected 'Bearer <token>'"
#         )
#
#     token_str = Authorization.removeprefix("Bearer ").strip()
#
#     try:
#         # Перевіряємо JWT токен
#         token_data = jwt_auth_manager.decode_access_token(token_str)
#         # user_id_from_token = token_data["sub"]  # або інше поле, де зберігається id користувача
#         # if user_id != user_id_from_token:
#         #     raise HTTPException(
#         #         status_code=status.HTTP_403_FORBIDDEN,
#         #         detail="You can only create or edit your own profile."
#         #     )
#     except BaseSecurityError as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=str(e)
#         )
#
#     user_stmt = select(UserModel).where(UserModel.id == user_id)
#     user_result = await db.execute(user_stmt)
#     user = user_result.scalars().first()
#
#
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Authorization header is missing"
#         )
#
#     # now_utc = datetime.now(timezone.utc)
#     # if cast(datetime, user._hashed_password.expires_at).replace(tzinfo=timezone.utc) < now_utc:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_401_UNAUTHORIZED,
#     #         detail="Token has expired."
#     #     )
#     now_utc = datetime.now(timezone.utc)
#
#     # Наприклад, беремо перший токен (або шукаємо потрібний по токену)
#     refresh_token = user.refresh_tokens[0]  # або інший спосіб отримання токена
#
#     if refresh_token.expires_at < now_utc:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token has expired."
#         )
#
#
#     if user.group != "user" or  user_data.email != user.email:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You don't have permission to edit this profile."
#         )
#     if not user or not user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User not found or not active."
#         )
#
#     if user.profile:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="User already has a profile."
#         )
#
#     new_profile = UserProfileModel(
#         user_id=user_id,
#         first_name=user_data.first_name,
#         last_name=user_data.last_name,
#         gender=user_data.gender,
#         date_of_birth=user_data.date_of_birth,
#         info=user_data.info,
#     )
#
#
#     try:
#         db.add(new_profile)
#         await db.commit()
#         await db.refresh(new_profile)
#     except SQLAlchemyError:
#         await db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Сталася помилка при створенні профілю."
#         )
#
#     return BaseProfileResponseSchema.model_validate(new_profile)
