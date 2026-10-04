# Put PantryPal online

The local address works on your computer. GitHub stores code; GitHub Pages cannot run this Flask backend. No public deployment has been created for this project yet.

## GitHub

Create an empty repository named `pantrypal`. Upload the contents of the clean `github-upload/pantrypal` folder, including its subfolders and `.gitignore`. Put `app.py` and `requirements.txt` at the repository root. Commit the files. Do not upload a virtual environment, `instance/`, databases, `.env`, or session secrets. A ZIP is convenient for sharing, but extract it before uploading source files through GitHub's web interface.

## Render example

1. In Render choose New → Web Service and connect the repository.
2. Choose Python 3 as the runtime.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 90`
5. Choose a paid service with a persistent disk mounted at `/var/data`. This app uses SQLite, so keep one instance. Review pricing before creating the service.
6. Add environment variables:
   - `PANTRYPAL_ENV`: `production`
   - `DATA_DIR`: `/var/data`
   - `SECRET_KEY`: a private, random value of at least 32 characters. Generate locally with `python -c "import secrets; print(secrets.token_hex(32))"`. Keep it stable across restarts.
   - `MEALDB_API_KEY`: the key appropriate for your release under the provider's current terms.
7. Set the health check path to `/health` and deploy.
8. Open the HTTPS address. Test search, registration, save, plan, shopping and cooking. Restart the service and check that saved data remains.
9. Add the HTTPS address to your GitHub repository's About → Website and README.

Production mode requires a secret and secure cookies, so it must be served over HTTPS. This application does not trust arbitrary forwarded client-IP headers; behind a proxy its small rate limits may be shared across visitors. For a larger deployment, configure trusted proxy handling and per-user limits, add email verification/password recovery, database migrations and backups, and move to a managed database before scaling to multiple instances.

Keep database backups using SQLite's backup API rather than copying an actively written file. Saved recipes are snapshots and may differ from later provider edits. New searches and images require outbound Internet access.

References: [Render Flask guide](https://render.com/docs/deploy-flask), [persistent disks](https://render.com/docs/disks), [TheMealDB API terms](https://www.themealdb.com/api.php). Hosting instructions checked October 2026; verify current plans when deploying.
