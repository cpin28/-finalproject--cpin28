"""Per-resource API routers.

Each module owns the routes for one resource and exposes a `router` (an
`APIRouter`). `api.create_app()` includes them all. Splitting routes this way keeps
each file small and focused, and makes the route surface easy to navigate.
"""

from . import ingredients, pantry, plan, recipes, shopping, substitutions

__all__ = ["ingredients", "pantry", "plan", "recipes", "shopping", "substitutions"]
