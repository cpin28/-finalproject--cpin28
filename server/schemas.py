"""Pydantic models — the contract shared between the API and its clients.

These describe the *shape* of data on the wire. Keeping them in one module (rather
than scattered through the routes) is a deliberate architecture choice: clients can
import these same types, and the contract tests assert against them.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")


# --- Ingredients ---------------------------------------------------------

class IngredientCreate(BaseModel):
    name: str
    default_unit: str = "unit"


class Ingredient(IngredientCreate):
    id: int


# --- Recipes -------------------------------------------------------------

class RecipeIngredientInput(BaseModel):
    ingredient_id: int
    quantity: float
    unit: str


class RecipeIngredient(BaseModel):
    ingredient_id: int
    name: str
    quantity: float
    unit: str


class RecipeCreate(BaseModel):
    name: str
    description: str = ""
    instructions: str = ""
    servings: int = Field(default=1, ge=1)
    prep_time_minutes: int = Field(default=0, ge=0)
    ingredients: list[RecipeIngredientInput] = []


class Recipe(BaseModel):
    id: int
    name: str
    description: str = ""
    instructions: str = ""
    servings: int = 1
    prep_time_minutes: int = 0
    ingredients: list[RecipeIngredient] = []


# --- Pantry --------------------------------------------------------------

class PantryItemInput(BaseModel):
    ingredient_id: int
    quantity: float
    unit: str


class PantryItem(BaseModel):
    ingredient_id: int
    name: str
    quantity: float
    unit: str


# --- Meal plan -----------------------------------------------------------

class PlannedMealCreate(BaseModel):
    date: str  # ISO date, e.g. "2026-06-10"
    meal_type: str
    recipe_id: int
    servings: int | None = None


class PlannedMeal(BaseModel):
    id: int
    date: str
    meal_type: str
    recipe_id: int
    recipe_name: str
    servings: int


# --- Derived -------------------------------------------------------------

class ShoppingListItem(BaseModel):
    ingredient_id: int
    name: str
    quantity: float
    unit: str


class CookCheck(BaseModel):
    recipe_id: int
    can_make: bool
    missing: list[str] = []
