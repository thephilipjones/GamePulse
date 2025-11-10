"""
⚠️ TEMPLATE DEMO MODELS - REMOVE BEFORE PRODUCTION ⚠️

Item model is part of the FastAPI template for demonstration purposes.
This is NOT part of GamePulse domain models.

TODO: Remove Item model before production.
GamePulse domain models (Game, Team, etc.) will be added in Epic 2.
"""
import uuid

from sqlmodel import Field, SQLModel


# ⚠️ TEMPLATE DEMO - Remove before production
# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=255)


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str
