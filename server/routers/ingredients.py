"""Routes for the canonical ingredient list."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import repository, schemas
from ..deps import get_conn

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("", response_model=list[schemas.Ingredient])
def list_ingredients(conn: sqlite3.Connection = Depends(get_conn)):
    return repository.list_ingredients(conn)


@router.post("", response_model=schemas.Ingredient, status_code=201)
def create_ingredient(data: schemas.IngredientCreate, conn: sqlite3.Connection = Depends(get_conn)):
    try:
        return repository.create_ingredient(conn, data)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="ingredient name already exists")
