"""Routes for the weekly meal plan."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import repository, schemas
from ..deps import get_conn

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("", response_model=list[schemas.PlannedMeal])
def list_plan(start: str | None = None, end: str | None = None, conn: sqlite3.Connection = Depends(get_conn)):
    return repository.list_planned_meals(conn, start, end)


@router.post("", response_model=schemas.PlannedMeal, status_code=201)
def add_plan(data: schemas.PlannedMealCreate, conn: sqlite3.Connection = Depends(get_conn)):
    if data.meal_type not in schemas.MEAL_TYPES:
        raise HTTPException(status_code=422, detail=f"meal_type must be one of {schemas.MEAL_TYPES}")
    meal = repository.create_planned_meal(conn, data)
    if meal is None:
        raise HTTPException(status_code=404, detail="recipe not found")
    return meal


@router.delete("/{meal_id}", status_code=204)
def remove_plan(meal_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    if not repository.delete_planned_meal(conn, meal_id):
        raise HTTPException(status_code=404, detail="planned meal not found")
