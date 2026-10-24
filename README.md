# Wind Forecast Analysis

## Run with Docker

From the project root, build and start both services:

```powershell
docker compose up --build
```

Open the dashboard at [http://localhost:8080](http://localhost:8080). Nginx serves
the production React build and proxies its same-origin `/api/` requests to the
FastAPI backend. The backend is also exposed directly at `http://localhost:8000`
for API checks.

Verify the health endpoint:

```powershell
Invoke-WebRequest http://localhost:8080/api/health
Invoke-WebRequest http://localhost:8000/api/health
```

View logs or stop the stack:

```powershell
docker compose logs -f
docker compose down
```

`ELEXON_BASE_URL` is configured in `docker-compose.yml` as
`https://data.elexon.co.uk`. `ELEXON_API_KEY` is optional; if needed, set it in
your shell before starting the stack rather than committing it:

```powershell
$env:ELEXON_API_KEY = "your_key"
docker compose up --build
```

## Local validation

```powershell
cd backend
python -m pytest -p no:cacheprovider tests
cd ..\frontend
npm run build
```
