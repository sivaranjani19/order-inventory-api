# Order Inventory API

A small FastAPI + SQLModel + SQLite service where placing an order decrements
stock in a separate inventory table, with a pytest suite that verifies both
the API's response *and* the resulting database state directly with raw SQL.

This project exists specifically to demonstrate DB-level test verification —
something that isn't possible against a third-party API like GoRest, since
there's no access to the database behind it. Here, the app and its database
are both owned by this project, so tests can check that a side effect (a
stock decrement spanning two tables) actually landed correctly, not just that
the API returned the expected status code.

**Live test report:** https://sivaranjani19.github.io/order-inventory-api/
(auto-published on every push to `main`)

## Tech Stack

- **FastAPI** — the API layer
- **SQLModel** — combines Pydantic-style models and SQLAlchemy table mappings in one class
- **SQLite** — the database, a single local file
- **pytest** + **FastAPI's `TestClient`** — test runner and HTTP client for the app under test (not Playwright — that project deliberately uses Playwright to test a *third-party* API; this one owns the app being tested, so `TestClient` is the idiomatic fit)
- **Raw `sqlite3`** — used only in tests, to verify database state through a path independent of the app's own ORM
- **pytest-html** — generates the HTML test report
- **GitHub Actions** — CI, running on every push to `main`

## Architecture

### Models (`app/models.py`)

- **`Inventory`** — `id`, `name`, `quantity`.
- **`Order`** — `id`, `quantity_ordered`, `inventory_id` (foreign key to `Inventory.id`), plus a bidirectional `Relationship` between the two.
- **`OrderCreate`** — a second, non-table model used only as the request body for `POST /orders`. This exists because of a real bug found during development: SQLModel classes with `table=True` skip most Pydantic validation, since they double as SQLAlchemy table mappings. `Field(gt=0)` on the table-backed `Order` model silently allowed negative and zero quantities through — a negative order would *add* stock instead of rejecting the request. `OrderCreate` is a plain (non-table) SQLModel, so it gets full Pydantic validation, and the route converts a validated `OrderCreate` into a real `Order` before saving it.

### Database (`app/database.py`)

- A SQLite engine (`sqlite:///database.db`) and `create_db_and_tables()`, which creates any tables registered in `SQLModel.metadata` that don't already exist.
- `get_session()` — a generator-based FastAPI dependency that yields a `Session` per request and closes it afterward.

### API (`app/main.py`)

- `POST /inventory/` — creates an inventory item.
- `POST /orders` — looks up the inventory row, returns `404` if it doesn't exist, `409` if there isn't enough stock, otherwise decrements `quantity` and creates the `Order` in the same transaction (one `commit()` for both changes, so a failure can't leave one table updated and the other not).
- Startup table creation runs via a `lifespan` context manager (the current FastAPI pattern, not the deprecated `@app.on_event("startup")`).

### Why 409, not 422, for insufficient stock

`404` is for a missing resource. `422` is what FastAPI already uses for malformed request bodies. Insufficient stock is neither: the request is well-formed and the item exists, but the current state of that resource conflicts with what's being asked — which is exactly what `409 Conflict` means. Keeping this distinct from FastAPI's own `422` means a test can tell "bad input" and "not enough stock" apart by status code alone.

## Test Coverage (`tests/test_orders.py`)

- **`test_create_order_updates_db_and_stock`** — the core test. Creates an item via the API, places an order via the API, then opens the test database directly with raw `sqlite3` and asserts both the stock decrease and the new order row — independent of the SQLModel/SQLAlchemy layer the app itself used to write them.
- **`test_create_order_insufficient_stock`** — asserts `409`, the exact error message, and that neither the stock nor the order table changed.
- **`test_create_order_unknown_item`** — asserts `404` for a nonexistent `inventory_id`, with no order row created.
- **`test_order_exactly_the_remaining_stock`** — a boundary test: ordering exactly what's in stock (5 of 5) should succeed and leave `0`, guarding against an off-by-one if the stock comparison is ever changed from `<` to `<=`.
- **`test_two_orders_in_sequence`** — two orders against the same item prove stock decrements accumulate correctly across requests, and that a later order can still be correctly rejected once stock runs out.
- **`test_create_order_zero_or_negative_quantity_returns_422`** (parametrized `[0, -3]`) — the test that caught the `OrderCreate` bug described above. Written first against the buggy code, confirmed it failed, then the fix was made and confirmed the test turned green.

### Fixtures (`tests/conftest.py`)

- **`db_path`** — a path to a throwaway SQLite file inside pytest's `tmp_path`, unique per test.
- **`client`** — builds an engine and tables against that file, overrides the app's `get_session` dependency (via `app.dependency_overrides`) so every route call during the test writes to the test database instead of the real one, and yields a `TestClient`.
- **`db_cursor`** — a raw `sqlite3` connection to the same `db_path`, for the independent-verification assertions.

Both `client` and `db_cursor` depend on the same `db_path`, so within a single test they're always looking at the same file — that's what lets an API call in one and a raw SQL query in the other agree on the same data.

The `client` fixture builds a plain `TestClient(app)` rather than using it as a context manager, since a `with` block would trigger the app's `lifespan` — which calls `create_db_and_tables()` against the *real* dev engine, not the test one. Without the `with` block, tests never touch `database.db` at all; the fixture's own `create_all()` against the test engine is all a test needs.

## Running Locally

```bash
git clone https://github.com/sivaranjani19/order-inventory-api.git
cd order-inventory-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the app:
```bash
uvicorn app.main:app --reload
```

Run the tests:
```bash
pytest -v
```

Generate an HTML report:
```bash
pytest --html=report.html --self-contained-html
```

## CI/CD

`.github/workflows/tests.yml` runs the full suite on every push to `main` and publishes the HTML report to GitHub Pages. Unlike the GoRest project, there's no nightly schedule here — this app has no external dependency that can drift or go down, so there's nothing for a nightly run to catch that a push-triggered run wouldn't.

## Possible Next Steps

- `GET /inventory/{id}` and `GET /orders/{id}` endpoints
- A restock endpoint, to test stock increasing as well as decreasing
- Concurrency: two simultaneous orders against the same low-stock item
