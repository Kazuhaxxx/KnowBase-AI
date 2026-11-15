from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    slug: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    icon: Optional[str] = Field(default="folder", max_length=50)
    access_classification: Optional[str] = Field(default="employee", pattern="^(public|employee|it_only|restricted)$")


class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    icon: Optional[str] = Field(default=None, max_length=50)
    access_classification: Optional[str] = Field(default=None, pattern="^(public|employee|it_only|restricted)$")


class CollectionRead(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    icon: str
    access_classification: str
    document_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

