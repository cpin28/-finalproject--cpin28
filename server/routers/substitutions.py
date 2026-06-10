"""Routes for ingredient substitutions."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import repository, schemas
from ..deps import get_conn

router = APIRouter(prefix="/substitutions", tags=["substitutions"])


@router.get("", response_model=list[schemas.Substitution])
def list_substitutions(conn: sqlite3.Connection = Depends(get_conn)):
    return repository.list_substitutions(conn)


@router.post("", response_model=schemas.Substitution, status_code=201)
def create_substitution(data: schemas.SubstitutionInput, conn: sqlite3.Connection = Depends(get_conn)):
    if data.ingredient_id == data.substitute_id:
        raise HTTPException(status_code=422, detail="an ingredient cannot substitute for itself")
    for ingredient_id in (data.ingredient_id, data.substitute_id):
        if repository.get_ingredient(conn, ingredient_id) is None:
            raise HTTPException(status_code=404, detail=f"ingredient {ingredient_id} not found")
    return repository.create_substitution(conn, data)


@router.delete("/{ingredient_id}/{substitute_id}", status_code=204)
def delete_substitution(ingredient_id: int, substitute_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    if not repository.delete_substitution(conn, ingredient_id, substitute_id):
        raise HTTPException(status_code=404, detail="substitution not found")
