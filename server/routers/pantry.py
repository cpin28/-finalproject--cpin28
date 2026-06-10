"""Routes for pantry (on-hand) stock."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import repository, schemas
from ..deps import get_conn

router = APIRouter(prefix="/pantry", tags=["pantry"])


@router.get("", response_model=list[schemas.PantryItem])
def list_pantry(conn: sqlite3.Connection = Depends(get_conn)):
    return repository.list_pantry(conn)


@router.put("", response_model=schemas.PantryItem)
def set_pantry(data: schemas.PantryItemInput, conn: sqlite3.Connection = Depends(get_conn)):
    if repository.get_ingredient(conn, data.ingredient_id) is None:
        raise HTTPException(status_code=404, detail="ingredient not found")
    return repository.set_pantry_item(conn, data)


@router.delete("/{ingredient_id}", status_code=204)
def remove_pantry(ingredient_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    if not repository.remove_pantry_item(conn, ingredient_id):
        raise HTTPException(status_code=404, detail="pantry item not found")
