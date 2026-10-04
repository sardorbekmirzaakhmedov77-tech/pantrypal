# PantryPal

A warm, practical cooking companion built with Python, Flask and SQLite. Discover real recipes, save favorites, plan your week, build a shopping list, and cook with a checklist and timer.

## What you can do

- Search live recipes by name or one main ingredient through TheMealDB.
- Discover related cooking techniques and recipes through Wikibooks Cookbook.
- Follow source instructions and open original recipe websites and video links when available.
- Keep a private recipe box with personal cooking notes.
- Plan breakfast, lunch and dinner for each day of the week.
- Generate a shopping list with recipe quantities; repeated generation does not duplicate existing meal ingredients.
- Check off shopping items, add your own and download CSV.
- Use cooking mode with remembered step progress and a start/pause/reset timer.
- Start as a guest without registration; create an account to keep your kitchen beyond seven days.

## Run on your computer

Use Python 3.11 or newer. Tested with Python 3.14.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Windows activate with `.venv\Scripts\activate` instead. Open http://127.0.0.1:5005. Keep the terminal running. The database and local session secret are created automatically inside `instance/`.

## Try this

1. Search for chicken or use one of the ingredient cards.
2. Open a recipe and save it.
3. Choose a day and add it to your meal plan.
4. Open Meal planner and select Build shopping list.
5. Check off an item, then open the recipe's Start cooking view.
6. Check a method section and try the timer.

A browser test used Mediterranean Pasta Salad from TheMealDB. Recipe search results depend on the providers and may change. An Internet connection is required for fresh searches and images. Previously opened recipes are stored as snapshots.

## Tests

```bash
python -m unittest discover -s tests -v
```

17 automated tests cover source failures, CSRF, account isolation, guest conversion, recipe caching, planning conflicts, quantities, duplicate prevention and CSV export. Tests use a temporary database and mocked recipe data; live providers were also checked separately.

## Learn the code

See [LEARNING_GUIDE.md](LEARNING_GUIDE.md) for a build-it-yourself path and [DEPLOYMENT.md](DEPLOYMENT.md) for hosting. This is a Python web app: HTML/CSS provide the interface, and a small JavaScript file handles the browser timer and checklist.

## Sources and limitations

- [TheMealDB API](https://www.themealdb.com/api.php) supplies recipes and remotely hosted photos. The default key `1` is for development/educational use. Review its current terms and obtain the appropriate key for your intended release; set `MEALDB_API_KEY` on the server.
- [Wikibooks Cookbook](https://en.wikibooks.org/wiki/Cookbook:Table_of_Contents) supplies linked guide search results. Follow each source page for contributors and licensing. Source content and photos retain their respective rights.
- Search queries go to these providers. No Wikipedia search is used. Results are limited to 18 recipes and six guides; providers can be unavailable independently.
- Recipe multiples are not servings. Only simple leading quantities are scaled; ambiguous quantities stay explicit. Method text remains the original recipe, including any quantities inside it.
- No guessed nutrition, preparation times or allergy guarantees. Read the complete source recipe and ingredient labels.
- Guest data is accessible for seven days; signing out loses access to an unregistered guest kitchen. Registered accounts have no email verification or password recovery yet.
- The timer needs an open browser tab; it is not a background phone alarm. Checklist state stays on this browser.
- Shopping entries remain after a meal is removed. Check them off if no longer needed.

Uploading this repository to GitHub publishes the source code. A public, clickable live app requires separate Python hosting.
