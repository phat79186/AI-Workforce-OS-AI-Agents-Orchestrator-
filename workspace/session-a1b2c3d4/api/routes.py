"""API routes for blog posts CRUD operations."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .database import db
from .models import BlogPostCreate, BlogPostResponse, BlogPostUpdate

router = APIRouter(tags=["posts"])


@router.get("/posts", response_model=list[BlogPostResponse])
async def list_posts(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return db.list_posts(offset=offset, limit=limit)


@router.get("/posts/{post_id}", response_model=BlogPostResponse)
async def get_post(post_id: str):
    post = db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts", response_model=BlogPostResponse, status_code=201)
async def create_post(data: BlogPostCreate):
    return db.create_post(data)


@router.put("/posts/{post_id}", response_model=BlogPostResponse)
async def update_post(post_id: str, data: BlogPostUpdate):
    post = db.update_post(post_id, data)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(post_id: str):
    if not db.delete_post(post_id):
        raise HTTPException(status_code=404, detail="Post not found")
