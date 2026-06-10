# Architecture

A client–server application. A single FastAPI server process owns an SQLite database and
exposes a REST API. Three Python clients (CLI, TUI, GUI) talk to it through one shared
client library; a fourth client — a browser web UI — is static files served by the server
that call the same REST API directly with `fetch`. No client ever touches the database.

> The diagrams below are rendered inline (GitHub renders ```mermaid``` blocks). The
> matching source files live in [`docs/diagrams/`](diagrams/) — `components.mmd`,
> `layers.mmd`, `request_flow.mmd`, and `schema.mmd` — for editing or re-rendering.

## Component view

Who talks to whom. Four clients, one server process, one database. Green = pure logic
(no I/O). Source: [`diagrams/components.mmd`](diagrams/components.mmd).

```mermaid
graph TD
    subgraph Clients["Clients (separate programs)"]
        CLI[CLI<br/>mealplan]
        TUI[TUI<br/>textual]
        GUI[GUI<br/>tkinter]
        WEB[Web UI<br/>browser · static/]
    end

    LIB[mealplan_client<br/>httpx · the wire protocol]

    subgraph Server["mealplan-server — one process (FastAPI + uvicorn)"]
        direction TB
        ROUTERS["routers/<br/>ingredients · recipes · pantry · plan · shopping"]
        subgraph Logic["domain logic — pure, no I/O"]
            PLAN[planner.py<br/>shopping list · cook check · suggestions]
            SEARCH[search.py<br/>fuzzy ranking]
        end
        REPO["repository/<br/>ingredients · recipes · pantry · plan — all SQL"]
        DB[db.py<br/>connection + schema]
        SCHEMAS[schemas.py<br/>shared models]
    end

    STORE[(SQLite<br/>mealplan.db)]

    CLI --> LIB
    TUI --> LIB
    GUI --> LIB
    LIB -->|HTTP / JSON| ROUTERS
    WEB -->|HTTP / JSON via fetch| ROUTERS

    ROUTERS --> PLAN
    ROUTERS --> SEARCH
    ROUTERS --> REPO
    PLAN --> REPO
    REPO --> DB
    DB --> STORE

    SCHEMAS -. shared contract .- ROUTERS
    SCHEMAS -.-> PLAN
    SCHEMAS -.-> REPO

    classDef pure fill:#eef7ee,stroke:#2e7d32,color:#1b5e20;
    class PLAN,SEARCH pure;
```

## Layered dependency view

The same server, seen as layers. **Every arrow points downward — a lower layer never
imports a higher one.** That single rule is what keeps the domain logic testable without a
database and the storage swappable. Source: [`diagrams/layers.mmd`](diagrams/layers.mmd).

```mermaid
graph TD
    REST{{"Clients reach the server only over REST<br/>(CLI/TUI/GUI via mealplan_client, Web via fetch)"}}
    REST --> ROUTERS

    ROUTERS["routers/ — HTTP layer<br/>validate input, delegate, return schemas"]
    LOGIC["planner.py · search.py — domain logic<br/>pure functions, no database"]
    REPO["repository/ — data access<br/>every SQL statement lives here"]
    DBMOD["db.py — storage adapter<br/>the only module that imports sqlite3"]
    SQLITE[("SQLite database")]
    SCHEMAS["schemas.py — shared contract (Pydantic models)"]

    ROUTERS --> LOGIC
    ROUTERS --> REPO
    LOGIC --> REPO
    REPO --> DBMOD
    DBMOD --> SQLITE

    SCHEMAS -. imported by all layers .- ROUTERS
    SCHEMAS -.-> LOGIC
    SCHEMAS -.-> REPO

    classDef pure fill:#eef7ee,stroke:#2e7d32,color:#1b5e20;
    class LOGIC pure;
```

### Modules at a glance

| Module | Responsibility | Depends on |
|---|---|---|
| `db.py` | connection + schema (only module importing `sqlite3`) | sqlite3 |
| `repository/` | CRUD, all SQL — one module per entity | db, schemas |
| `planner.py` | shopping list, cook check, pantry suggestions — pure logic | schemas |
| `search.py` | fuzzy recipe-name scoring & ranking — pure logic | schemas |
| `schemas.py` | wire/data models (Pydantic) | — |
| `deps.py` | shared FastAPI dependency (per-request connection) | db |
| `routers/` | HTTP routes, one module per resource | repository, planner, search, schemas, deps |
| `api.py` | app assembly: include routers + serve web client | routers, db |
| `main.py` | uvicorn entry point | api |

Both the route layer and the data layer are **split per resource**: `routers/` has one
`APIRouter` module per resource, and `repository/` has one SQL module per entity (with
`__init__.py` re-exporting so callers still write `repository.create_recipe(...)`). Both
were refactored out of single monolithic modules — see [`refactoring.md`](refactoring.md)
and the git history. Adding a resource is a new router module plus a new repository module.

## Request flow

A representative request — the derived shopping list — showing routes delegating reads to
the repository and computation to the pure planner. Source:
[`diagrams/request_flow.mmd`](diagrams/request_flow.mmd).

```mermaid
sequenceDiagram
    actor User
    participant Client as Client (CLI/TUI/GUI/Web)
    participant Lib as mealplan_client / fetch
    participant Router as routers/shopping
    participant Repo as repository/
    participant Plan as planner.py
    participant DB as SQLite

    User->>Client: "show my shopping list"
    Client->>Lib: shopping_list(start, end)
    Lib->>Router: GET /shopping-list?start&end
    Router->>Repo: list_planned_meals(start, end)
    Repo->>DB: SELECT planned_meals
    Router->>Repo: recipes_by_id(ids)
    Repo->>DB: SELECT recipes + ingredients
    Router->>Repo: list_pantry()
    Repo->>DB: SELECT pantry_items
    Router->>Plan: shopping_list(meals, recipes, pantry)
    Note over Plan: pure function —<br/>aggregate needs, subtract pantry
    Plan-->>Router: items still needed
    Router-->>Lib: JSON list
    Lib-->>Client: items
    Client-->>User: rendered list
```

## Data model

Five tables; `recipe_ingredients` is the many-to-many join between recipes and
ingredients. Source: [`diagrams/schema.mmd`](diagrams/schema.mmd).

```mermaid
erDiagram
    INGREDIENTS ||--o{ RECIPE_INGREDIENTS : "used in"
    RECIPES     ||--o{ RECIPE_INGREDIENTS : "has"
    INGREDIENTS ||--o| PANTRY_ITEMS : "stocked as"
    RECIPES     ||--o{ PLANNED_MEALS : "scheduled as"

    INGREDIENTS {
        int id PK
        string name
        string default_unit
    }
    RECIPES {
        int id PK
        string name
        int servings
        int prep_time_minutes
    }
    RECIPE_INGREDIENTS {
        int recipe_id FK
        int ingredient_id FK
        real quantity
        string unit
    }
    PANTRY_ITEMS {
        int ingredient_id PK
        real quantity
        string unit
    }
    PLANNED_MEALS {
        int id PK
        string date
        string meal_type
        int recipe_id FK
        int servings
    }
```

## REST API surface

| Method & path | Purpose |
|---|---|
| `GET/POST /ingredients` | list / create ingredients |
| `GET/POST /recipes`, `GET/DELETE /recipes/{id}` | manage recipes (`?q=` filters by name) |
| `GET /recipes/search?q=` | fuzzy-ranked recipe search (`search.py`) |
| `GET /recipes/suggestions` | recipes ranked by pantry coverage (`planner.suggest_recipes`) |
| `GET /recipes/{id}/can-make` | cook check against the pantry |
| `GET /pantry`, `PUT /pantry`, `DELETE /pantry/{ingredient_id}` | pantry stock |
| `GET/POST /plan`, `DELETE /plan/{id}` | weekly meal plan (`?start=&end=`) |
| `GET /shopping-list` | derived list for a date range (`?start=&end=`) |

## Process & runtime notes

- **One server process.** `main.py` runs `uvicorn.run(create_app(db_path))` — a single
  process listening on one host/port (default `127.0.0.1:8000`).
- **Connection per request.** The `get_conn` dependency opens a short-lived SQLite
  connection for each request and closes it after — simple and thread-safe at this scale.
- **Configurable database.** `$MEALPLAN_DB` (default `mealplan.db`); the server creates the
  schema on startup, and `migrations/seed.py` loads demo data.

See [`design.md`](design.md) for the rationale behind these choices (and what was
deliberately left out), and [`testing.md`](testing.md) for how the layers are tested.
