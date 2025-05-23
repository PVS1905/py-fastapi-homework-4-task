from datetime import date
from typing import Optional

from fastapi import UploadFile, Form, File, HTTPException
from pydantic import BaseModel, field_validator, HttpUrl

from database.models.accounts import GenderEnum
from validation import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date
)
from fastapi import status


class BaseProfileRequestSchema(BaseModel):
    first_name: str
    last_name: str
    gender: Optional[GenderEnum] = None
    date_of_birth: date
    info: str
    avatar: UploadFile = None

    model_config = {
        "from_attributes": True
    }

    @field_validator("first_name")
    @classmethod
    def first_name_validator(cls, value):
        try:
            validate_name(value)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        return value

    @field_validator("last_name")
    @classmethod
    def last_name_validator(cls, value):
        try:
            validate_name(value)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        return value

    @field_validator("gender")
    @classmethod
    def validate_field_gender(cls, value):
        try:
            validate_gender(value)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        return value

    @field_validator("avatar")
    @classmethod
    def avatar_validator(cls, value):
        try:
            if value is not None:
                validate_image(value)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        return value

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_validator(cls, value):
        try:
            validate_birth_date(value)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        return value

    @field_validator("info")
    @classmethod
    def info_validator(cls, value):
        try:
            return value.strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )

    @classmethod
    def from_form(
        cls,
        first_name: str = Form(...),
        last_name: str = Form(...),
        gender: str = Form(...),
        date_of_birth: date = Form(...),
        info: str = Form(...),
        avatar: UploadFile = File(...),
    ) -> "BaseProfileRequestSchema":
        try:
            return cls(
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=date_of_birth,
                info=info,
                avatar=avatar,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )


class BaseProfileResponseSchema(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    info: str
    avatar: Optional[HttpUrl] = None

    class Config:
        from_attributes = True
