"""Pydantic models — the contract shared between the API and its clients.

These describe the *shape* of data on the wire. Keeping them in one module (rather
than scattered through the routes) is a deliberate architecture choice: clients can
import these same types, and the contract tests assert against them.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")
DIFFICULTIES = ("beginner", "easy", "intermediate")


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
    difficulty: str = "beginner"
    ingredients: list[RecipeIngredientInput] = []


class Recipe(BaseModel):
    id: int
    name: str
    description: str = ""
    instructions: str = ""
    servings: int = 1
    prep_time_minutes: int = 0
    difficulty: str = "beginner"
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


# --- Substitutions -------------------------------------------------------

class SubstitutionInput(BaseModel):
    ingredient_id: int
    substitute_id: int
    ratio: float = 1.0   # amount of substitute per unit of the original
    note: str = ""


class Substitution(BaseModel):
    ingredient_id: int
    ingredient_name: str
    substitute_id: int
    substitute_name: str
    ratio: float = 1.0
    note: str = ""


class SubstitutionOption(BaseModel):
    """A swap the pantry makes possible for a missing ingredient."""
    missing: str       # ingredient the recipe calls for
    use_instead: str   # substitute the pantry has
    ratio: float = 1.0
    note: str = ""


# --- Derived: cook check & suggestions -----------------------------------

class CookCheck(BaseModel):
    recipe_id: int
    can_make: bool                              # pantry covers everything directly
    missing: list[str] = []                     # still missing, even after substitutions
    can_make_with_substitutions: bool = False   # all gaps fillable via pantry substitutes
    substitutions: list[SubstitutionOption] = []


class RecipeSuggestion(BaseModel):
    recipe_id: int
    name: str
    difficulty: str = "beginner"
    can_make: bool
    can_make_with_substitutions: bool = False
    missing: list[str] = []
    substitutions: list[SubstitutionOption] = []
    have_count: int   # ingredients the pantry covers directly
    need_count: int   # total ingredients in the recipe
