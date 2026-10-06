"""Explicit, non-privileged fields editable by the account owner."""
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

AvatarColor = Literal['slate', 'indigo', 'emerald', 'rose', 'amber']


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    display_name: str | None = Field(default=None, min_length=1, max_length=120,
                                   validation_alias=AliasChoices('display_name', 'full_name', 'name'))
    bio: str | None = Field(default=None, max_length=1000)
    workspace: str | None = Field(default=None, max_length=120)
    avatar_color: AvatarColor = 'slate'

    @field_validator('display_name')
    @classmethod
    def name_is_present(cls, value):
        if value is None:
            raise ValueError('Display name cannot be empty')
        return value
