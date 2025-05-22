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



class BaseProfileRequestSchema(BaseModel):
    first_name: str
    last_name: str
    gender: Optional[GenderEnum] = None
    date_of_birth: date
    info: str
    avatar: UploadFile | None = None

    model_config = {
        "from_attributes": True
    }

    @field_validator("first_name")
    @classmethod
    def first_name_validator(cls, value):
        validate_name(value)
        return value

    @field_validator("last_name")
    @classmethod
    def last_name_validator(cls, value):
        validate_name(value)
        return value

    @field_validator("gender")
    @classmethod
    def gender_validator(cls, value):
        validate_gender(value)
        return value

    @field_validator("avatar")
    @classmethod
    def avatar_validator(cls, value):
        if value is not None:
            validate_image(value)
        return value

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_validator(cls, value):
        validate_birth_date(value)
        return value

    @field_validator("info")
    @classmethod
    def info_validator(cls, value):
        return value.strip()


class BaseProfileResponseSchema(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    info: str
    avatar: UploadFile | None = None