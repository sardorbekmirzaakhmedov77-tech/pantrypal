# Build PantryPal yourself

This project extends the Python, APIs, Flask, HTML/CSS, forms, databases and authentication concepts taught in Angela Yu's 100 Days of Code. Course sections can change, so follow the topic names rather than a fixed day number. You do not need to memorize this app: rebuild one working feature at a time.

| Topic | Where it appears | Practice task |
|---|---|---|
| Functions, lists, dictionaries, loops | sources.py | Convert one API recipe into an ingredient list |
| HTTP requests and JSON | sources.py | Search TheMealDB by recipe name |
| Exceptions and validation | app.py, sources.py | Show a friendly message when a source is offline |
| Flask routes and Jinja templates | app.py, templates/ | Render a recipe page from a dictionary |
| HTML and CSS | templates/, static/style.css | Build responsive recipe cards |
| Forms, GET and POST | app.py | Save a recipe after a form submission |
| SQL and relationships | db.py | Join saved recipe IDs with recipe details |
| Authentication and sessions | app.py | Log in with a hashed password |
| Dates and data processing | app.py | Build seven dates for a weekly planner |
| CSV files | app.py | Export your shopping list |
| JavaScript extension | static/app.js | Start and pause a browser timer |

## Suggested build order

1. Create a Flask home route that says hello. Add one template and a stylesheet.
2. Write a Python function that calls TheMealDB. Print the returned recipe title and ingredients.
3. Connect a GET search form to that function. Render cards and add an empty-results state.
4. Build a recipe detail route using its ID. Show ingredient measurements and original instructions.
5. Create the SQLite tables. Save one favorite; then join recipe data to display the recipe box.
6. Add guest sessions and account registration. Hash passwords and check ownership on every private query.
7. Add meal dates and slots. Prevent two recipes from silently replacing one another in the same slot.
8. Generate shopping entries. Keep units separate and make repeated generation safe.
9. Add Wikibooks guide search. Make each source fail independently.
10. Add the timer and checklist in JavaScript, then polish mobile layouts.
11. Write tests using Flask's test client and temporary SQLite databases.
12. Deploy using Gunicorn and persistent storage.

## Extensions beyond the course basics

CSRF tokens, response security headers, bounded requests, rate limits, cache locking, safe CSV cells, persistent hosting and account ownership tests are extra engineering practice. Understand why they exist before editing them. The timer's JavaScript is small, but it is a separate browser language; Python still handles search, storage, authentication and planning.

## Code map

- `sources.py`: fixed provider URLs, timeouts, caching and normalized recipes.
- `db.py`: schema and commit/rollback context manager.
- `app.py`: request handling, user sessions, validation and database actions.
- `templates/`: page structure, forms and escaped source content.
- `static/`: visual design and optional browser enhancements.
- `tests/test_app.py`: observable behaviors rather than real network calls.

Try adding a “remove favorite” feature yourself: use POST, include CSRF, require the current user, and delete only that user's saved relationship. Then test that another user's recipe remains saved.
