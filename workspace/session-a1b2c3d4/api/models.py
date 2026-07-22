"""Pydantic models for the Blog Post API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BlogPostCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1, max_length=100)
    tags: list[str] = Field(default_factory=list)


class BlogPostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[list[str]] = None


class BlogPostResponse(BaseModel):
    id: str
    title: str
    content: str
    author: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
