"""Load a catalogue of 100 easy recipes (and the ingredients they need) into a database.

Run: `python -m migrations.easy_recipes [db_path]`  (defaults to $MEALPLAN_DB or mealplan.db)

Unlike the small demo `seed.py`, this is a bulk content loader. It is idempotent at the
recipe level: ingredients are reused by name (created only when missing), and a recipe is
skipped if one with the same name already exists — so re-running it, or running it after
`seed.py`, never duplicates rows. Every recipe here is tagged `difficulty="easy"`.
"""

from __future__ import annotations

import os
import sys

from server import repository, schemas
from server.db import connect, init_db

# Default unit for each ingredient referenced below. Units are drawn from the planner's
# known families (g/kg, ml/l/tsp/tbsp/cup) plus the pass-through "unit" for countables.
UNITS: dict[str, str] = {
    # staples / baking
    "flour": "g", "sugar": "g", "salt": "g", "butter": "g", "oil": "ml", "olive oil": "ml",
    "baking powder": "tsp", "cinnamon": "tsp", "cocoa": "g", "vanilla": "tsp", "honey": "g",
    "breadcrumbs": "g", "vinegar": "ml", "chocolate chips": "g",
    # dairy / eggs
    "egg": "unit", "milk": "ml", "cheese": "g", "cheddar": "g", "mozzarella": "g",
    "parmesan": "g", "cream cheese": "g", "feta": "g", "yogurt": "g", "sour cream": "g",
    "heavy cream": "ml",
    # produce
    "onion": "unit", "garlic": "unit", "tomato": "unit", "potato": "unit", "carrot": "unit",
    "lettuce": "g", "cucumber": "unit", "bell pepper": "unit", "broccoli": "g", "mushroom": "g",
    "avocado": "unit", "lemon": "unit", "lime": "unit", "banana": "unit", "apple": "unit",
    "strawberry": "g", "blueberry": "g", "celery": "unit", "corn": "g", "peas": "g",
    "zucchini": "unit", "cabbage": "g", "basil": "g", "cilantro": "g", "parsley": "g",
    "scallion": "unit", "jalapeno": "unit", "lemon juice": "ml",
    # proteins / legumes
    "chicken breast": "g", "ground beef": "g", "bacon": "g", "ham": "g", "turkey": "g",
    "salmon": "g", "tuna": "g", "shrimp": "g", "tofu": "g", "sausage": "g",
    "chickpeas": "g", "black beans": "g", "kidney beans": "g", "lentils": "g",
    # grains / carbs
    "pasta": "g", "rice": "g", "bread": "unit", "tortilla": "unit", "oats": "g",
    "quinoa": "g", "noodles": "g", "couscous": "g", "bagel": "unit", "English muffin": "unit",
    "granola": "g",
    # condiments / pantry
    "soy sauce": "ml", "mustard": "ml", "mayonnaise": "g", "tomato sauce": "ml", "salsa": "g",
    "peanut butter": "g", "jam": "g", "coconut milk": "ml", "chili powder": "tsp",
    "cumin": "tsp", "paprika": "tsp",
    # snacks / drinks
    "peanuts": "g", "raisins": "g", "almonds": "g", "coffee": "ml", "water": "ml",
}

# (name, servings, prep_minutes, [(ingredient_name, quantity), ...]) — all "easy".
RECIPES: list[tuple[str, int, int, list[tuple[str, float]]]] = [
    # --- breakfast -------------------------------------------------------
    ("Scrambled Eggs on Toast", 1, 10, [("egg", 3), ("butter", 10), ("bread", 2)]),
    ("Avocado Toast", 1, 8, [("bread", 2), ("avocado", 1), ("lemon juice", 5), ("salt", 1)]),
    ("Peanut Butter Banana Toast", 1, 5, [("bread", 2), ("peanut butter", 30), ("banana", 1)]),
    ("Classic Pancakes", 4, 20, [("flour", 200), ("egg", 2), ("milk", 300), ("sugar", 20), ("baking powder", 2)]),
    ("Blueberry Pancakes", 4, 20, [("flour", 200), ("egg", 2), ("milk", 300), ("blueberry", 100), ("sugar", 20)]),
    ("French Toast", 2, 15, [("bread", 4), ("egg", 2), ("milk", 100), ("cinnamon", 1), ("butter", 10)]),
    ("Oatmeal with Banana", 1, 10, [("oats", 80), ("milk", 250), ("banana", 1), ("honey", 15)]),
    ("Overnight Oats", 1, 5, [("oats", 80), ("yogurt", 150), ("blueberry", 50), ("honey", 15)]),
    ("Greek Yogurt Parfait", 1, 5, [("yogurt", 200), ("granola", 50), ("strawberry", 80), ("honey", 15)]),
    ("Cheese Omelette", 1, 10, [("egg", 3), ("cheddar", 40), ("butter", 10)]),
    ("Veggie Omelette", 1, 12, [("egg", 3), ("bell pepper", 1), ("onion", 1), ("cheese", 30)]),
    ("Breakfast Burrito", 1, 15, [("tortilla", 1), ("egg", 2), ("cheese", 30), ("salsa", 30)]),
    ("Bacon and Eggs", 1, 12, [("egg", 2), ("bacon", 60)]),
    ("Banana Smoothie", 1, 5, [("banana", 1), ("milk", 200), ("honey", 15), ("yogurt", 100)]),
    ("Berry Smoothie", 1, 5, [("strawberry", 100), ("blueberry", 50), ("yogurt", 150), ("milk", 100)]),
    ("Fruit Salad", 2, 10, [("apple", 1), ("banana", 1), ("strawberry", 100), ("lemon juice", 5)]),
    ("Yogurt and Granola", 1, 3, [("yogurt", 200), ("granola", 60)]),
    ("Bagel with Cream Cheese", 1, 5, [("bagel", 1), ("cream cheese", 40)]),
    ("English Muffin Sandwich", 1, 12, [("English muffin", 1), ("egg", 1), ("cheese", 30), ("ham", 40)]),
    ("Toast with Jam", 1, 5, [("bread", 2), ("butter", 10), ("jam", 30)]),
    # --- sandwiches / wraps / salads ------------------------------------
    ("Grilled Cheese", 1, 10, [("bread", 2), ("cheddar", 50), ("butter", 15)]),
    ("Ham and Cheese Sandwich", 1, 8, [("bread", 2), ("ham", 50), ("cheese", 40), ("mustard", 5)]),
    ("Turkey Sandwich", 1, 8, [("bread", 2), ("turkey", 60), ("lettuce", 20), ("mayonnaise", 15)]),
    ("BLT", 1, 12, [("bread", 2), ("bacon", 50), ("lettuce", 20), ("tomato", 1), ("mayonnaise", 15)]),
    ("Tuna Salad Sandwich", 1, 10, [("bread", 2), ("tuna", 80), ("mayonnaise", 20), ("celery", 1)]),
    ("Egg Salad Sandwich", 1, 12, [("bread", 2), ("egg", 2), ("mayonnaise", 20)]),
    ("Caprese Salad", 2, 10, [("tomato", 2), ("mozzarella", 100), ("basil", 10), ("olive oil", 15)]),
    ("Greek Salad", 2, 12, [("cucumber", 1), ("tomato", 2), ("feta", 60), ("olive oil", 15), ("onion", 1)]),
    ("Garden Salad", 2, 10, [("lettuce", 100), ("tomato", 1), ("cucumber", 1), ("olive oil", 15)]),
    ("Caesar Salad", 2, 12, [("lettuce", 120), ("parmesan", 30), ("breadcrumbs", 20)]),
    ("Cobb Salad", 2, 15, [("lettuce", 100), ("chicken breast", 100), ("bacon", 40), ("egg", 1), ("avocado", 1)]),
    ("Tomato Cucumber Salad", 2, 8, [("tomato", 2), ("cucumber", 1), ("onion", 1), ("vinegar", 10)]),
    ("Coleslaw", 4, 10, [("cabbage", 150), ("carrot", 1), ("mayonnaise", 30), ("vinegar", 10)]),
    ("Chickpea Salad", 2, 10, [("chickpeas", 150), ("cucumber", 1), ("tomato", 1), ("olive oil", 15)]),
    ("Caprese Sandwich", 1, 8, [("bread", 2), ("mozzarella", 60), ("tomato", 1), ("basil", 8)]),
    ("Hummus Wrap", 1, 8, [("tortilla", 1), ("chickpeas", 100), ("cucumber", 1), ("lettuce", 20)]),
    ("Veggie Wrap", 1, 10, [("tortilla", 1), ("lettuce", 30), ("tomato", 1), ("cucumber", 1), ("cheese", 30)]),
    ("Chicken Wrap", 1, 12, [("tortilla", 1), ("chicken breast", 100), ("lettuce", 30), ("mayonnaise", 15)]),
    ("Quesadilla", 1, 10, [("tortilla", 2), ("cheddar", 60), ("salsa", 30)]),
    ("Grilled Chicken Salad", 2, 18, [("lettuce", 100), ("chicken breast", 120), ("tomato", 1), ("olive oil", 15)]),
    # --- soups -----------------------------------------------------------
    ("Tomato Soup", 4, 25, [("tomato", 4), ("onion", 1), ("garlic", 2), ("water", 300)]),
    ("Chicken Noodle Soup", 4, 30, [("chicken breast", 150), ("noodles", 100), ("carrot", 1), ("celery", 1)]),
    ("Vegetable Soup", 4, 30, [("carrot", 1), ("potato", 1), ("onion", 1), ("celery", 1), ("water", 400)]),
    ("Lentil Soup", 4, 35, [("lentils", 150), ("carrot", 1), ("onion", 1), ("water", 500)]),
    ("Minestrone", 4, 30, [("pasta", 80), ("kidney beans", 100), ("tomato", 2), ("carrot", 1)]),
    ("Potato Soup", 4, 30, [("potato", 3), ("onion", 1), ("milk", 200), ("butter", 15)]),
    ("Black Bean Soup", 4, 25, [("black beans", 200), ("onion", 1), ("garlic", 2), ("cumin", 1)]),
    ("Egg Drop Soup", 2, 12, [("egg", 2), ("water", 400), ("scallion", 1), ("soy sauce", 10)]),
    # --- pasta / rice / grains ------------------------------------------
    ("Spaghetti with Tomato Sauce", 2, 20, [("pasta", 200), ("tomato sauce", 200), ("garlic", 2)]),
    ("Spaghetti Aglio e Olio", 2, 18, [("pasta", 200), ("garlic", 3), ("olive oil", 30), ("parsley", 5)]),
    ("Mac and Cheese", 2, 20, [("pasta", 200), ("cheddar", 100), ("milk", 150), ("butter", 20)]),
    ("Pasta with Pesto", 2, 15, [("pasta", 200), ("basil", 30), ("parmesan", 40), ("olive oil", 30)]),
    ("Tomato Pasta", 2, 25, [("pasta", 200), ("tomato", 3), ("onion", 1), ("olive oil", 15)]),
    ("Penne Arrabbiata", 2, 20, [("pasta", 200), ("tomato sauce", 200), ("garlic", 2), ("chili powder", 1)]),
    ("Creamy Mushroom Pasta", 2, 22, [("pasta", 200), ("mushroom", 150), ("heavy cream", 100), ("garlic", 2)]),
    ("Buttered Noodles", 2, 15, [("noodles", 200), ("butter", 30), ("parmesan", 30)]),
    ("Fried Rice", 2, 18, [("rice", 200), ("egg", 2), ("peas", 60), ("soy sauce", 20), ("carrot", 1)]),
    ("Egg Fried Rice", 2, 15, [("rice", 200), ("egg", 3), ("scallion", 1), ("soy sauce", 20)]),
    ("Vegetable Fried Rice", 2, 18, [("rice", 200), ("peas", 60), ("carrot", 1), ("corn", 60), ("soy sauce", 20)]),
    ("Rice and Beans", 2, 20, [("rice", 200), ("black beans", 150), ("onion", 1), ("cumin", 1)]),
    ("Chicken and Rice", 2, 35, [("chicken breast", 250), ("rice", 150), ("onion", 1), ("olive oil", 15)]),
    ("Tomato Rice", 2, 22, [("rice", 200), ("tomato", 2), ("onion", 1), ("oil", 15)]),
    ("Coconut Rice", 2, 22, [("rice", 200), ("coconut milk", 200), ("salt", 2)]),
    ("Quinoa Bowl", 2, 20, [("quinoa", 150), ("chickpeas", 100), ("cucumber", 1), ("olive oil", 15)]),
    ("Couscous Salad", 2, 15, [("couscous", 150), ("cucumber", 1), ("tomato", 1), ("lemon juice", 10)]),
    # --- mains -----------------------------------------------------------
    ("Baked Chicken Breast", 2, 30, [("chicken breast", 300), ("olive oil", 15), ("paprika", 1), ("salt", 2)]),
    ("Grilled Chicken", 2, 25, [("chicken breast", 300), ("olive oil", 15), ("lemon", 1), ("garlic", 2)]),
    ("Chicken Stir Fry", 2, 20, [("chicken breast", 250), ("broccoli", 150), ("soy sauce", 20), ("garlic", 2)]),
    ("Beef Stir Fry", 2, 20, [("ground beef", 250), ("bell pepper", 1), ("onion", 1), ("soy sauce", 20)]),
    ("Beef Tacos", 3, 20, [("ground beef", 250), ("tortilla", 3), ("cheddar", 60), ("salsa", 40)]),
    ("Chicken Tacos", 3, 22, [("chicken breast", 250), ("tortilla", 3), ("lettuce", 30), ("salsa", 40)]),
    ("Sloppy Joes", 2, 20, [("ground beef", 250), ("tomato sauce", 150), ("onion", 1), ("bread", 2)]),
    ("Hamburger", 1, 18, [("ground beef", 200), ("bread", 1), ("cheese", 30), ("lettuce", 20), ("tomato", 1)]),
    ("Meatballs", 3, 30, [("ground beef", 300), ("breadcrumbs", 40), ("egg", 1), ("parmesan", 30)]),
    ("Baked Salmon", 2, 25, [("salmon", 250), ("lemon", 1), ("olive oil", 15), ("salt", 2)]),
    ("Salmon and Veggies", 2, 28, [("salmon", 250), ("broccoli", 150), ("olive oil", 15)]),
    ("Shrimp Scampi", 2, 20, [("shrimp", 200), ("garlic", 3), ("butter", 30), ("pasta", 200)]),
    ("Garlic Butter Shrimp", 2, 15, [("shrimp", 250), ("garlic", 3), ("butter", 30), ("parsley", 5)]),
    ("Tofu Stir Fry", 2, 20, [("tofu", 200), ("broccoli", 150), ("soy sauce", 20), ("garlic", 2)]),
    ("Scrambled Tofu", 2, 15, [("tofu", 200), ("onion", 1), ("bell pepper", 1), ("paprika", 1)]),
    ("Sausage and Peppers", 2, 25, [("sausage", 250), ("bell pepper", 2), ("onion", 1), ("olive oil", 15)]),
    ("Baked Potato", 2, 45, [("potato", 2), ("butter", 20), ("cheddar", 40), ("sour cream", 30)]),
    ("Mashed Potatoes", 4, 25, [("potato", 4), ("butter", 30), ("milk", 100), ("salt", 2)]),
    ("Roasted Vegetables", 4, 35, [("carrot", 2), ("potato", 2), ("zucchini", 1), ("olive oil", 20)]),
    ("Roasted Broccoli", 2, 22, [("broccoli", 250), ("olive oil", 15), ("garlic", 2), ("salt", 2)]),
    ("Stuffed Bell Peppers", 2, 40, [("bell pepper", 2), ("rice", 100), ("ground beef", 150), ("tomato sauce", 100)]),
    ("Veggie Quesadilla", 1, 12, [("tortilla", 2), ("cheese", 60), ("bell pepper", 1), ("onion", 1)]),
    ("Chili", 4, 35, [("ground beef", 250), ("kidney beans", 150), ("tomato", 2), ("chili powder", 2), ("onion", 1)]),
    ("Bean Burrito", 1, 12, [("tortilla", 1), ("black beans", 120), ("rice", 80), ("cheese", 40), ("salsa", 30)]),
    ("Tuna Melt", 1, 12, [("bread", 2), ("tuna", 80), ("cheddar", 40), ("mayonnaise", 15)]),
    # --- snacks / desserts / drinks -------------------------------------
    ("Guacamole", 4, 10, [("avocado", 2), ("lime", 1), ("onion", 1), ("cilantro", 5), ("salt", 2)]),
    ("Salsa", 4, 10, [("tomato", 3), ("onion", 1), ("cilantro", 5), ("lime", 1), ("jalapeno", 1)]),
    ("Hummus", 4, 10, [("chickpeas", 200), ("olive oil", 30), ("lemon juice", 15), ("garlic", 2)]),
    ("Trail Mix", 4, 5, [("peanuts", 80), ("raisins", 50), ("chocolate chips", 40), ("almonds", 40)]),
    ("Chocolate Chip Cookies", 12, 30, [("flour", 250), ("butter", 120), ("sugar", 150), ("egg", 1), ("chocolate chips", 150)]),
    ("Banana Bread", 8, 60, [("flour", 200), ("banana", 3), ("sugar", 120), ("egg", 2), ("butter", 80)]),
    ("Brownies", 9, 40, [("flour", 120), ("cocoa", 60), ("sugar", 200), ("butter", 120), ("egg", 2)]),
    ("Mug Cake", 1, 5, [("flour", 40), ("cocoa", 15), ("sugar", 30), ("milk", 45), ("oil", 15)]),
    ("Iced Coffee", 1, 5, [("coffee", 200), ("milk", 100), ("sugar", 15)]),
    ("Lemonade", 2, 5, [("lemon juice", 60), ("water", 300), ("sugar", 40)]),
]


def load(db_path: str) -> int:
    """Create missing ingredients and any not-yet-present easy recipes. Returns #added."""
    # Fail fast if a recipe references an ingredient with no declared unit.
    referenced = {name for _, _, _, items in RECIPES for name, _ in items}
    missing_units = sorted(referenced - UNITS.keys())
    if missing_units:
        raise ValueError(f"no unit declared for ingredients: {missing_units}")

    conn = connect(db_path)
    init_db(conn)

    ids = {ing.name: ing.id for ing in repository.list_ingredients(conn)}
    for name in sorted(referenced):
        if name not in ids:
            ids[name] = repository.create_ingredient(
                conn, schemas.IngredientCreate(name=name, default_unit=UNITS[name])
            ).id

    existing = {r.name for r in repository.list_recipes(conn)}
    added = 0
    for name, servings, prep, items in RECIPES:
        if name in existing:
            continue
        repository.create_recipe(conn, schemas.RecipeCreate(
            name=name, difficulty="easy", servings=servings, prep_time_minutes=prep,
            ingredients=[schemas.RecipeIngredientInput(ingredient_id=ids[n], quantity=q, unit=UNITS[n])
                         for n, q in items],
        ))
        added += 1

    conn.close()
    return added


def main() -> None:
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MEALPLAN_DB", "mealplan.db")
    added = load(db_path)
    print(f"Loaded {added} easy recipes into {db_path} (of {len(RECIPES)} in the catalogue).")


if __name__ == "__main__":
    main()
