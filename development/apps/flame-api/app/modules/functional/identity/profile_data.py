"""Optional contact details; no authentication/authorization fields are editable."""
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator


def clean_phone(value):
    if value is None or isinstance(value, str) and not value.strip():
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\+?[0-9 () .-]{7,32}", value.strip()) or not 7 <= len(re.sub(r"\D", "", value)) <= 15:
        raise ValueError("Enter a phone number with 7–15 digits, optionally including a country code")
    return value.strip()


class PhoneInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone_number: str | None = Field(default=None, max_length=32)

    @field_validator("phone_number", mode="before")
    @classmethod
    def phone(cls, value):
        return clean_phone(value)


class ProfileEdit(PhoneInput):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_number: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=1000)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=20)

    @field_validator("contact_number", mode="before")
    @classmethod
    def contact_phone(cls, value):
        return clean_phone(value)

    @field_validator("address", "city", "state", "country", "pincode", mode="before")
    @classmethod
    def optional_text(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("display_name")
    @classmethod
    def name(cls, value):
        if value is None or not value.strip():
            raise ValueError("Display name is required")
        return value.strip()
